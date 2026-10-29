"""TechStore U4 - API REST con FastAPI.
Expone los endpoints para interactuar con los pedidos y la máquina de estados.
"""
from decimal import Decimal
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel, Field

from cargar_csv import load_fixture
from app.domain import (
    Order,
    OrderItem,
    Money,
    OrderStatus,
    InvalidOrderTransition,
    InvalidOrderData,
    OrderItemLimitExceeded,
)
from app.specifications import evaluate_discount

app = FastAPI(
    title="TechStore U4 API",
    description="API REST para la administración de pedidos de TechStore con Domain-Driven Design y FastAPI.",
    version="1.0.0"
)

# Almacenamiento en memoria cargado desde los CSV de fixture
orders_db: Dict[str, Order] = load_fixture()


# Modelos Pydantic para peticiones y respuestas
class ShipRequest(BaseModel):
    tracking_number: str = Field(..., description="Número de guía para el envío")


class CancelRequest(BaseModel):
    reason: str = Field(..., description="Motivo de la cancelación del pedido")


class AddItemRequest(BaseModel):
    sku: str = Field(..., description="Código SKU del producto")
    quantity: int = Field(..., gt=0, description="Cantidad a agregar (mayor a cero)")
    unit_price_mxn: float = Field(..., gt=0, description="Precio unitario en MXN")


def get_order_or_404(order_id: str) -> Order:
    order = orders_db.get(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail=f"Pedido {order_id} no encontrado")
    return order


@app.get("/", tags=["General"])
def root():
    return {
        "message": "Bienvenido a TechStore U4 API",
        "docs": "/docs",
        "total_pedidos": len(orders_db)
    }


@app.post("/reset", tags=["General"])
def reset_fixtures():
    """Recarga los pedidos originales desde los archivos CSV."""
    global orders_db
    orders_db = load_fixture()
    return {"message": "Fixtures recargados exitosamente desde CSV", "pedidos": len(orders_db)}


@app.get("/orders", tags=["Pedidos"])
def list_orders():
    """Lista todos los pedidos registrados en el sistema."""
    result = []
    for order in orders_db.values():
        rate, label = evaluate_discount(order)
        result.append({
            "id": order.id,
            "cliente_id": order.customer.id,
            "es_vip": order.customer.is_vip,
            "cliente_activo": order.customer.active,
            "status": order.status.value,
            "unidades": order.units,
            "total_mxn": float(order.total.amount),
            "tiene_promocion": order.has_promotion,
            "descuento": label
        })
    return result


@app.get("/orders/{order_id}", tags=["Pedidos"])
def get_order(order_id: str):
    """Obtiene el detalle completo de un pedido específico."""
    order = get_order_or_404(order_id)
    rate, label = evaluate_discount(order)
    return {
        "id": order.id,
        "cliente": {
            "id": order.customer.id,
            "es_vip": order.customer.is_vip,
            "activo": order.customer.active
        },
        "has_promotion": order.has_promotion,
        "status": order.status.value,
        "units": order.units,
        "total": {
            "amount": float(order.total.amount),
            "currency": order.total.currency
        },
        "descuento": {
            "porcentaje": label,
            "tasa": float(rate)
        },
        "tracking_number": order.tracking_number,
        "cancellation_reason": order.cancellation_reason,
        "items": [
            {
                "sku": item.sku,
                "quantity": item.quantity,
                "unit_price": float(item.unit_price.amount),
                "subtotal": float(item.subtotal.amount)
            } for item in order.items
        ],
        "events": [
            {
                "name": event.name,
                "occurred_at": event.occurred_at.isoformat()
            } for event in order.events
        ]
    }


@app.post("/orders/{order_id}/confirm", tags=["Máquina de Estados"],
    description="Confirma un pedido pendiente. "
    "Si el pedido ya fue confirmado o está en otro estado, "
    "se devuelve el código 409."
    )
def confirm_order(order_id: str):
    """Confirma un pedido en estado DRAFT."""
    order = get_order_or_404(order_id)
    try:
        order.confirm()
    except InvalidOrderTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except InvalidOrderData as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {
        "id": order.id,
        "status": order.status.value,
        "mensaje": "El pedido ha sido confirmado correctamente.",
        "events": [e.name for e in order.events]
    }


@app.post("/orders/{order_id}/ship", tags=["Máquina de Estados"])
def ship_order(order_id: str, payload: ShipRequest):
    """Envía un pedido confirmado proporcionando número de guía."""
    order = get_order_or_404(order_id)
    try:
        order.ship(payload.tracking_number)
    except InvalidOrderTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except InvalidOrderData as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {
        "id": order.id,
        "status": order.status.value,
        "tracking_number": order.tracking_number,
        "events": [e.name for e in order.events]
    }


@app.post("/orders/{order_id}/cancel", tags=["Máquina de Estados"])
def cancel_order(order_id: str, payload: CancelRequest):
    """Cancela un pedido confirmado indicando el motivo."""
    order = get_order_or_404(order_id)
    try:
        order.cancel(payload.reason)
    except InvalidOrderTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except InvalidOrderData as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {
        "id": order.id,
        "status": order.status.value,
        "cancellation_reason": order.cancellation_reason,
        "events": [e.name for e in order.events]
    }


@app.post("/orders/{order_id}/deliver", tags=["Máquina de Estados"])
def deliver_order(order_id: str):
    """Marca un pedido enviado como entregado."""
    order = get_order_or_404(order_id)
    try:
        order.deliver()
    except InvalidOrderTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except InvalidOrderData as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {
        "id": order.id,
        "status": order.status.value,
        "events": [e.name for e in order.events]
    }


@app.post("/orders/{order_id}/return", tags=["Máquina de Estados"])
def return_order(order_id: str):
    """Marca un pedido enviado como devuelto."""
    order = get_order_or_404(order_id)
    try:
        order.return_order()
    except InvalidOrderTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except InvalidOrderData as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {
        "id": order.id,
        "status": order.status.value,
        "events": [e.name for e in order.events]
    }


@app.post("/orders/{order_id}/items", tags=["Operaciones"])
def add_item_to_order(order_id: str, payload: AddItemRequest):
    """Agrega un artículo a un pedido en estado DRAFT."""
    order = get_order_or_404(order_id)
    try:
        item = OrderItem(
            sku=payload.sku,
            quantity=payload.quantity,
            unit_price=Money(Decimal(str(payload.unit_price_mxn)))
        )
        order.add_item(item)
    except InvalidOrderTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except (InvalidOrderData, OrderItemLimitExceeded) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {
        "id": order.id,
        "status": order.status.value,
        "units": order.units,
        "total_mxn": float(order.total.amount)
    }


@app.get("/orders/{order_id}/discount", tags=["Reglas"])
def get_order_discount(order_id: str):
    """Evalúa la regla de descuento aplicable al pedido."""
    order = get_order_or_404(order_id)
    rate, label = evaluate_discount(order)
    return {
        "order_id": order.id,
        "porcentaje_descuento": label,
        "tasa_decimal": float(rate),
        "es_vip": order.customer.is_vip,
        "unidades": order.units,
        "total": float(order.total.amount),
        "tiene_promocion": order.has_promotion
    }
