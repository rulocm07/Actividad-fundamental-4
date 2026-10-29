"""TechStore U4 - Pruebas de Integración de la API REST.
Verifica endpoints, códigos de estado HTTP (200, 404, 409, 422) y Swagger.
"""
import pytest
from fastapi.testclient import TestClient

from app.api import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_state():
    """Reinicia el estado en memoria antes de cada prueba para garantizar reproducibilidad."""
    client.post("/reset")


def test_api_root():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Bienvenido a TechStore U4 API"
    assert data["total_pedidos"] == 16


def test_api_list_orders():
    response = client.get("/orders")
    assert response.status_code == 200
    orders = response.json()
    assert len(orders) == 16
    assert orders[0]["id"] == "O001"
    assert orders[0]["unidades"] == 4


def test_api_get_order_valido():
    response = client.get("/orders/O001")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "O001"
    assert data["status"] == "DRAFT"
    assert data["units"] == 4
    assert data["total"]["amount"] == 2100.0
    assert data["descuento"]["porcentaje"] == "10%"


def test_api_get_order_404_no_existe():
    response = client.get("/orders/O_NO_EXISTE")
    assert response.status_code == 404
    assert "no encontrado" in response.json()["detail"].lower()


def test_api_confirm_exitoso():
    response = client.post("/orders/O001/confirm")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "O001"
    assert data["status"] == "CONFIRMED"
    assert "OrderConfirmed" in data["events"]


def test_api_confirm_404_inexistente():
    response = client.post("/orders/O999/confirm")
    assert response.status_code == 404


def test_api_confirm_409_doble_confirmacion():
    # Primera confirmación exitosa
    r1 = client.post("/orders/O013/confirm")
    assert r1.status_code == 200

    # Segunda confirmación produce conflicto 409
    r2 = client.post("/orders/O013/confirm")
    assert r2.status_code == 409
    assert "Solo DRAFT" in r2.json()["detail"]


def test_api_confirm_422_pedido_vacio():
    # O007 es un pedido sin artículos
    response = client.post("/orders/O007/confirm")
    assert response.status_code == 422
    assert "Requiere artículos y cliente activo" in response.json()["detail"]


def test_api_confirm_422_cliente_inactivo():
    # O003 pertenece al cliente C003 que está inactivo
    response = client.post("/orders/O003/confirm")
    assert response.status_code == 422
    assert "Requiere artículos y cliente activo" in response.json()["detail"]


def test_api_ship_order():
    client.post("/orders/O001/confirm")
    response = client.post("/orders/O001/ship", json={"tracking_number": "TRK-98765"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "SHIPPED"
    assert data["tracking_number"] == "TRK-98765"


def test_api_ship_sin_confirmar_409():
    response = client.post("/orders/O001/ship", json={"tracking_number": "TRK-11111"})
    assert response.status_code == 409
    assert "Solo CONFIRMED puede ser enviado" in response.json()["detail"]


def test_api_cancel_order():
    client.post("/orders/O001/confirm")
    response = client.post("/orders/O001/cancel", json={"reason": "Cambio de opinión del cliente"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "CANCELLED"
    assert data["cancellation_reason"] == "Cambio de opinión del cliente"


def test_api_deliver_order():
    client.post("/orders/O016/confirm")
    client.post("/orders/O016/ship", json={"tracking_number": "TRK-DELIVERY"})
    response = client.post("/orders/O016/deliver")
    assert response.status_code == 200
    assert response.json()["status"] == "DELIVERED"


def test_api_return_order():
    client.post("/orders/O015/confirm")
    client.post("/orders/O015/ship", json={"tracking_number": "TRK-RETURN"})
    response = client.post("/orders/O015/return")
    assert response.status_code == 200
    assert response.json()["status"] == "RETURNED"


def test_api_add_item_excede_limite_422():
    # O009 tiene 19 unidades
    response = client.post(
        "/orders/O009/items",
        json={"sku": "SKU003", "quantity": 2, "unit_price_mxn": 120.0}
    )
    assert response.status_code == 422
    assert "Máximo 20 unidades" in response.json()["detail"]


def test_api_evaluar_descuento_endpoint():
    r1 = client.get("/orders/O001/discount")
    assert r1.status_code == 200
    assert r1.json()["porcentaje_descuento"] == "10%"

    r6 = client.get("/orders/O006/discount")
    assert r6.status_code == 200
    assert r6.json()["porcentaje_descuento"] == "5%"
