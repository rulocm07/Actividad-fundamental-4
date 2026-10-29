"""TechStore U4 - Ejecución y Validación de los 15 Escenarios (E01 a E15).
Este script ejecuta cada escenario sobre instancias frescas de los pedidos cargados desde CSV
y genera la bitácora requerida para la entrega de la Actividad 4.
"""
from decimal import Decimal
from cargar_csv import load_fixture
from app.domain import OrderItem, Money, OrderStatus, InvalidOrderData, InvalidOrderTransition, OrderItemLimitExceeded
from app.specifications import evaluate_discount

def traducir_estado(estado):
    estados = {
        "DRAFT": "Creado, aún no confirmado (DRAFT)",
        "CONFIRMED": "Confirmado",
        "SHIPPED": "Enviado",
        "DELIVERED": "Entregado",
        "CANCELLED": "Cancelado",
        "RETURNED": "Devuelto"
    }
    return estados.get(estado, estado)


def run_all_scenarios():
    print("=" * 110)
    print("BITÁCORA DE EVALUACIÓN DE ESCENARIOS E01 - E15 | TECHSTORE U4")
    print("=" * 110)
    print(f"{'Caso':<5} | {'Pedido':<6} | {'Estado inicial':<28} | {'Operación':<30} | {'Resultado real':<38} | {'Eventos'}")
    print("-" * 110)

    bitacora = []

    # E01: O001 evaluar_descuento
    orders = load_fixture()
    o = orders["O001"]
    rate, label = evaluate_discount(o)
    res = f"Descuento: {label}"
    bitacora.append({
        "caso": "E01", "pedido": "O001", "estado_ini": traducir_estado(o.status.value),
        "operacion": "evaluar_descuento", "resultado": res,
        "eventos": "Sin eventos (lectura)",
        "explicacion": "Cliente VIP (C001), total 2100.00 > 500, 4 unidades >= 4, sin promoción. Aplica regla 10%."
    })

    # E02: O002 evaluar_descuento
    orders = load_fixture()
    o = orders["O002"]
    rate, label = evaluate_discount(o)
    res = f"Descuento: {label}"
    bitacora.append({
        "caso": "E02", "pedido": "O002", "estado_ini": traducir_estado(o.status.value),
        "operacion": "evaluar_descuento", "resultado": res,
        "eventos": "Sin eventos (lectura)",
        "explicacion": "Cliente no VIP (C002), total 1050.00 <= 5000. No califica para 10% ni 5%."
    })

    # E03: O003 confirmar
    orders = load_fixture()
    o = orders["O003"]
    try:
        o.confirm()
        res = f"CONFIRMED"
        ev = [e.name for e in o.events]
    except InvalidOrderData as e:
        res = "RECHAZO (InvalidOrderData)"
        ev = "Ninguno"
    bitacora.append({
        "caso": "E03", "pedido": "O003", "estado_ini": "DRAFT",
        "operacion": "confirmar", "resultado": res,
        "eventos": str(ev),
        "explicacion": "Cliente C003 está inactivo (activo=0). La regla exige cliente activo."
    })

    # E04: O005 evaluar_descuento
    orders = load_fixture()
    o = orders["O005"]
    rate, label = evaluate_discount(o)
    res = f"Descuento: {label}"
    bitacora.append({
        "caso": "E04", "pedido": "O005", "estado_ini": traducir_estado(o.status.value),
        "operacion": "evaluar_descuento", "resultado": res,
        "eventos": "Sin eventos (lectura)",
        "explicacion": "Tiene promoción activa (tiene_promocion=1). La especificación ~ActivePromotionSpec bloquea el descuento."
    })

    # E05: O006 evaluar_descuento
    orders = load_fixture()
    o = orders["O006"]
    rate, label = evaluate_discount(o)
    res = f"Descuento: {label}"
    bitacora.append({
        "caso": "E05", "pedido": "O006", "estado_ini": traducir_estado(o.status.value),
        "operacion": "evaluar_descuento", "resultado": res,
        "eventos": "Sin eventos (lectura)",
        "explicacion": "Total 18000.00 > 5000, sin promoción activa. Cumple regla alternativa del 5%."
    })

    # E06: O007 confirmar
    orders = load_fixture()
    o = orders["O007"]
    try:
        o.confirm()
        res = "CONFIRMED"
        ev = [e.name for e in o.events]
    except InvalidOrderData as e:
        res = "RECHAZO (InvalidOrderData)"
        ev = "Ninguno"
    bitacora.append({
        "caso": "E06", "pedido": "O007", "estado_ini": "DRAFT",
        "operacion": "confirmar", "resultado": res,
        "eventos": str(ev),
        "explicacion": "Pedido vacío (0 artículos). La regla exige que el pedido contenga al menos un artículo."
    })

    # E07: O008 confirmar
    orders = load_fixture()
    o = orders["O008"]
    try:
        o.confirm()
        res = f"ÉXITO ({traducir_estado(o.status.value)})"
        ev = [e.name for e in o.events]
    except Exception as e:
        res = f"RECHAZO ({type(e).__name__})"
        ev = "Ninguno"
    bitacora.append({
        "caso": "E07", "pedido": "O008", "estado_ini": "DRAFT",
        "operacion": "confirmar", "resultado": res,
        "eventos": str(ev),
        "explicacion": "Tiene exactamente 20 unidades de SKU003 y cliente activo. Es el límite máximo permitido y es válido."
    })

    # E08: O009 agregar SKU003 x2
    orders = load_fixture()
    o = orders["O009"]
    try:
        o.add_item(OrderItem("SKU003", 2, Money(Decimal("120.00"))))
        res = "ÉXITO"
        ev = "Ninguno"
    except OrderItemLimitExceeded as e:
        res = "RECHAZO (OrderItemLimitExceeded)"
        ev = "Ninguno"
    bitacora.append({
        "caso": "E08", "pedido": "O009", "estado_ini": traducir_estado(o.status.value),
        "operacion": "agregar SKU003 x2", "resultado": res,
        "eventos": str(ev),
        "explicacion": "El pedido ya tiene 19 unidades. Sumar 2 daría 21 unidades, superando el límite máximo estricto de 20."
    })

    # E09: O010 evaluar_descuento
    orders = load_fixture()
    o = orders["O010"]
    rate, label = evaluate_discount(o)
    res = f"Descuento: {label}"
    bitacora.append({
        "caso": "E09", "pedido": "O010", "estado_ini": traducir_estado(o.status.value),
        "operacion": "evaluar_descuento", "resultado": res,
        "eventos": "Sin eventos (lectura)",
        "explicacion": "Total es exactamente 500.00 MXN. La especificación exige total estrictamente > 500, por lo que no califica."
    })

    # E10: O011 evaluar_descuento
    orders = load_fixture()
    o = orders["O011"]
    rate, label = evaluate_discount(o)
    res = f"Descuento: {label}"
    bitacora.append({
        "caso": "E10", "pedido": "O011", "estado_ini": traducir_estado(o.status.value),
        "operacion": "evaluar_descuento", "resultado": res,
        "eventos": "Sin eventos (lectura)",
        "explicacion": "Cliente VIP y total 1500 > 500, pero solo tiene 3 unidades físicas. La regla exige >= 4 unidades."
    })

    # E11: O012 confirmar y enviar sin guia
    orders = load_fixture()
    o = orders["O012"]
    o.confirm()
    try:
        o.ship("")
        res = "ENVIADO"
        ev = [e.name for e in o.events]
    except InvalidOrderData as e:
        res = "RECHAZO (InvalidOrderData)"
        ev = [e.name for e in o.events]
    bitacora.append({
        "caso": "E11", "pedido": "O012", "estado_ini": "DRAFT",
        "operacion": "confirmar y enviar sin guía", "resultado": res,
        "eventos": str(ev),
        "explicacion": "La confirmación a CONFIRMED es exitosa emitiendo OrderConfirmed; el envío falla porque la guía no puede ser vacía."
    })

    # E12: O013 confirmar dos veces
    orders = load_fixture()
    o = orders["O013"]
    o.confirm()
    try:
        o.confirm()
        res = "CONFIRMED 2"
        ev = [e.name for e in o.events]
    except InvalidOrderTransition as e:
        res = "RECHAZO (InvalidOrderTransition)"
        ev = [e.name for e in o.events]
    bitacora.append({
        "caso": "E12", "pedido": "O013", "estado_ini": "DRAFT",
        "operacion": "confirmar dos veces", "resultado": res,
        "eventos": str(ev),
        "explicacion": "La primera confirmación es válida. La segunda se rechaza porque solo pedidos en DRAFT pueden confirmarse."
    })

    # E13: O014 confirmar, enviar y cancelar
    orders = load_fixture()
    o = orders["O014"]
    o.confirm()
    o.ship("GUIA-E13")
    try:
        o.cancel("Deseo cancelar")
        res = "CANCELADO"
        ev = [e.name for e in o.events]
    except InvalidOrderTransition as e:
        res = "RECHAZO (InvalidOrderTransition)"
        ev = [e.name for e in o.events]
    bitacora.append({
        "caso": "E13", "pedido": "O014", "estado_ini": "DRAFT",
        "operacion": "confirmar, enviar y cancelar", "resultado": res,
        "eventos": str(ev),
        "explicacion": "Pasa a CONFIRMED y luego a SHIPPED. La cancelación se rechaza porque solo el estado CONFIRMED admite cancelación."
    })

    # E14: O015 confirmar, enviar y devolver
    orders = load_fixture()
    o = orders["O015"]
    o.confirm()
    o.ship("GUIA-E14")
    o.return_order()
    res = f"ÉXITO ({traducir_estado(o.status.value)})"
    ev = [e.name for e in o.events]
    bitacora.append({
        "caso": "E14", "pedido": "O015", "estado_ini": "DRAFT",
        "operacion": "confirmar, enviar y devolver", "resultado": res,
        "eventos": str(ev),
        "explicacion": "Transiciones válidas DRAFT -> CONFIRMED -> SHIPPED -> RETURNED. Emite los 3 eventos correspondientes."
    })

    # E15: O016 confirmar, enviar y entregar
    orders = load_fixture()
    o = orders["O016"]
    o.confirm()
    o.ship("GUIA-E15")
    o.deliver()
    res = f"ÉXITO ({traducir_estado(o.status.value)})"
    ev = [e.name for e in o.events]
    bitacora.append({
        "caso": "E15", "pedido": "O016", "estado_ini": "DRAFT",
        "operacion": "confirmar, enviar y entregar", "resultado": res,
        "eventos": str(ev),
        "explicacion": "Transiciones válidas DRAFT -> CONFIRMED -> SHIPPED -> DELIVERED. Emite los 3 eventos correspondientes."
    })

    for row in bitacora:
        estado = traducir_estado(row["estado_ini"])

        print(
            f"{row['caso']:<5} | "
            f"{row['pedido']:<6} | "
            f"{estado:<28} | "
            f"{row['operacion']:<30} | "
            f"{row['resultado']:<38} | "
            f"{row['eventos']}"
        )
    return bitacora


if __name__ == "__main__":
    run_all_scenarios()
