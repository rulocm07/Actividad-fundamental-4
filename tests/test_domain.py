"""TechStore U4 - Pruebas Unitarias del Dominio y Specifications.
Verifica reglas de negocio, invariantes, máquina de estados y cálculo de descuentos.
"""
from decimal import Decimal
import pytest

from app.domain import (
    Customer,
    Order,
    OrderItem,
    Money,
    OrderStatus,
    DomainEvent,
    InvalidOrderData,
    InvalidOrderTransition,
    OrderItemLimitExceeded,
)
from app.specifications import (
    MinimumAmountSpec,
    VIPCustomerSpec,
    MinimumUnitsSpec,
    ActivePromotionSpec,
    evaluate_discount,
)
from cargar_csv import load_fixture


# ==========================================
# 1. Pruebas de Money y Value Objects
# ==========================================

def test_money_valido():
    m = Money(Decimal("600.00"))
    assert m.amount == Decimal("600.00")
    assert m.currency == "MXN"


def test_money_negativo():
    with pytest.raises(InvalidOrderData, match="Monto inválido"):
        Money(Decimal("-1.00"))


def test_money_suma_misma_moneda():
    m1 = Money(Decimal("100.50"))
    m2 = Money(Decimal("200.25"))
    suma = m1.add(m2)
    assert suma.amount == Decimal("300.75")
    assert suma.currency == "MXN"


def test_money_suma_monedas_distintas():
    m1 = Money(Decimal("100.00"), "MXN")
    m2 = Money(Decimal("100.00"), "USD")
    with pytest.raises(InvalidOrderData, match="Monedas distintas"):
        m1.add(m2)


def test_order_item_valido():
    item = OrderItem("SKU001", 3, Money(Decimal("150.00")))
    assert item.sku == "SKU001"
    assert item.quantity == 3
    assert item.subtotal.amount == Decimal("450.00")


def test_order_item_cantidad_invalida():
    with pytest.raises(InvalidOrderData, match="Artículo inválido"):
        OrderItem("SKU001", 0, Money(Decimal("100.00")))
    with pytest.raises(InvalidOrderData, match="Artículo inválido"):
        OrderItem("SKU001", -2, Money(Decimal("100.00")))


def test_order_item_sku_vacio():
    with pytest.raises(InvalidOrderData, match="Artículo inválido"):
        OrderItem("   ", 1, Money(Decimal("100.00")))


# ==========================================
# 2. Pruebas de Invariantes del Pedido (Order)
# ==========================================

def test_pedido_o001_inicia_draft():
    orders = load_fixture()
    o = orders["O001"]
    assert o.status == OrderStatus.DRAFT
    assert o.units == 4
    assert o.total.amount == Decimal("2100.00")


def test_limite_maximo_20_unidades_exito():
    customer = Customer("C001", is_vip=True, active=True)
    order = Order(customer=customer, id="O_TEST")
    order.add_item(OrderItem("SKU001", 20, Money(Decimal("100.00"))))
    assert order.units == 20


def test_limite_maximo_20_unidades_excedido():
    customer = Customer("C001", is_vip=True, active=True)
    order = Order(customer=customer, id="O_TEST")
    order.add_item(OrderItem("SKU001", 19, Money(Decimal("100.00"))))
    with pytest.raises(OrderItemLimitExceeded, match="Máximo 20 unidades"):
        order.add_item(OrderItem("SKU002", 2, Money(Decimal("50.00"))))
    assert order.units == 19


def test_agregar_item_solo_en_draft():
    customer = Customer("C001", is_vip=True, active=True)
    order = Order(customer=customer, id="O_TEST")
    order.add_item(OrderItem("SKU001", 1, Money(Decimal("100.00"))))
    order.confirm()
    with pytest.raises(InvalidOrderTransition, match="Solo DRAFT admite artículos"):
        order.add_item(OrderItem("SKU002", 1, Money(Decimal("100.00"))))


# ==========================================
# 3. Pruebas de la Máquina de Estados y Eventos
# ==========================================

def test_confirmar_pedido_vacio_falla():
    customer = Customer("C001", is_vip=True, active=True)
    order = Order(customer=customer, id="O_EMPTY")
    with pytest.raises(InvalidOrderData, match="Requiere artículos y cliente activo"):
        order.confirm()
    assert order.status == OrderStatus.DRAFT
    assert len(order.events) == 0


def test_confirmar_cliente_inactivo_falla():
    customer = Customer("C003", is_vip=True, active=False)
    order = Order(customer=customer, id="O_INACTIVO")
    order.add_item(OrderItem("SKU001", 1, Money(Decimal("100.00"))))
    with pytest.raises(InvalidOrderData, match="Requiere artículos y cliente activo"):
        order.confirm()
    assert order.status == OrderStatus.DRAFT
    assert len(order.events) == 0


def test_confirmar_exitoso_emite_evento():
    customer = Customer("C001", is_vip=True, active=True)
    order = Order(customer=customer, id="O_OK")
    order.add_item(OrderItem("SKU001", 2, Money(Decimal("100.00"))))
    order.confirm()
    assert order.status == OrderStatus.CONFIRMED
    assert len(order.events) == 1
    assert order.events[0].name == "OrderConfirmed"


def test_confirmacion_doble_falla():
    orders = load_fixture()
    order = orders["O013"]
    order.confirm()
    assert order.status == OrderStatus.CONFIRMED
    assert len(order.events) == 1
    with pytest.raises(InvalidOrderTransition, match="Solo DRAFT"):
        order.confirm()
    assert len(order.events) == 1  # No agrega nuevo evento


def test_envio_sin_guia_falla():
    customer = Customer("C001", is_vip=True, active=True)
    order = Order(customer=customer, id="O_SHIP")
    order.add_item(OrderItem("SKU001", 1, Money(Decimal("100.00"))))
    order.confirm()
    with pytest.raises(InvalidOrderData, match="La guía de envío es obligatoria"):
        order.ship("")
    assert order.status == OrderStatus.CONFIRMED


def test_cancelacion_desde_shipped_falla():
    orders = load_fixture()
    order = orders["O014"]
    order.confirm()
    order.ship("GUIA123")
    assert order.status == OrderStatus.SHIPPED
    with pytest.raises(InvalidOrderTransition, match="Solo CONFIRMED puede ser cancelado"):
        order.cancel("Ya no lo quiero")
    assert order.status == OrderStatus.SHIPPED


def test_flujo_completo_entrega():
    orders = load_fixture()
    order = orders["O016"]
    order.confirm()
    order.ship("GUIA-O016")
    order.deliver()
    assert order.status == OrderStatus.DELIVERED
    event_names = [e.name for e in order.events]
    assert event_names == ["OrderConfirmed", "OrderShipped", "OrderDelivered"]


def test_flujo_completo_devolucion():
    orders = load_fixture()
    order = orders["O015"]
    order.confirm()
    order.ship("GUIA-O015")
    order.return_order()
    assert order.status == OrderStatus.RETURNED
    event_names = [e.name for e in order.events]
    assert event_names == ["OrderConfirmed", "OrderShipped", "OrderReturned"]


# ==========================================
# 4. Pruebas de Specifications y Descuentos
# ==========================================

def test_descuento_10_porciento_vip():
    orders = load_fixture()
    rate, label = evaluate_discount(orders["O001"])
    assert label == "10%"
    assert rate == Decimal("0.10")


def test_descuento_0_porciento_no_vip():
    orders = load_fixture()
    rate, label = evaluate_discount(orders["O002"])
    assert label == "0%"
    assert rate == Decimal("0.00")


def test_descuento_bloqueado_por_promocion():
    orders = load_fixture()
    rate, label = evaluate_discount(orders["O005"])
    assert label == "0%"
    assert rate == Decimal("0.00")


def test_descuento_5_porciento_monto_superior_5000():
    orders = load_fixture()
    rate, label = evaluate_discount(orders["O006"])
    assert label == "5%"
    assert rate == Decimal("0.05")


def test_descuento_umbral_estricto_500():
    orders = load_fixture()
    # O010 tiene exactamente 500.00 MXN -> no supera 500
    rate, label = evaluate_discount(orders["O010"])
    assert label == "0%"
    assert rate == Decimal("0.00")


def test_descuento_unidades_insuficientes():
    orders = load_fixture()
    # O011 es VIP, total > 500, pero solo tiene 3 unidades (requiere 4)
    rate, label = evaluate_discount(orders["O011"])
    assert label == "0%"
    assert rate == Decimal("0.00")


# ==========================================
# 5. Validación Exhaustiva de Escenarios E01 a E15
# ==========================================

def test_escenarios_e01_a_e15_completos():
    orders = load_fixture()

    # E01: O001 evaluar_descuento -> 10%
    assert evaluate_discount(orders["O001"])[1] == "10%"

    # E02: O002 evaluar_descuento -> 0%
    assert evaluate_discount(orders["O002"])[1] == "0%"

    # E03: O003 confirmar -> rechazo (Cliente inactivo)
    with pytest.raises(InvalidOrderData):
        orders["O003"].confirm()

    # E04: O005 evaluar_descuento -> 0% (Promocion activa bloquea)
    assert evaluate_discount(orders["O005"])[1] == "0%"

    # E05: O006 evaluar_descuento -> 5% (>5000 y sin promocion)
    assert evaluate_discount(orders["O006"])[1] == "5%"

    # E06: O007 confirmar -> rechazo (Pedido vacio)
    with pytest.raises(InvalidOrderData):
        orders["O007"].confirm()

    # E07: O008 confirmar -> exito (20 unidades)
    orders["O008"].confirm()
    assert orders["O008"].status == OrderStatus.CONFIRMED

    # E08: O009 agregar SKU003 x2 -> rechazo (19 + 2 = 21 excede 20)
    with pytest.raises(OrderItemLimitExceeded):
        orders["O009"].add_item(OrderItem("SKU003", 2, Money(Decimal("120.00"))))

    # E09: O010 evaluar_descuento -> 0% (Total exactamente 500)
    assert evaluate_discount(orders["O010"])[1] == "0%"

    # E10: O011 evaluar_descuento -> 0% (Solo 3 unidades)
    assert evaluate_discount(orders["O011"])[1] == "0%"

    # E11: O012 confirmar y enviar sin guia -> rechazo envio
    orders["O012"].confirm()
    assert orders["O012"].status == OrderStatus.CONFIRMED
    with pytest.raises(InvalidOrderData):
        orders["O012"].ship("")

    # E12: O013 confirmar dos veces -> rechazo segunda
    orders["O013"].confirm()
    with pytest.raises(InvalidOrderTransition):
        orders["O013"].confirm()

    # E13: O014 confirmar, enviar y cancelar -> rechazo cancelacion
    orders["O014"].confirm()
    orders["O014"].ship("GUIA-O014")
    with pytest.raises(InvalidOrderTransition):
        orders["O014"].cancel("No deseado")

    # E14: O015 confirmar, enviar y devolver -> exito RETURNED
    orders["O015"].confirm()
    orders["O015"].ship("GUIA-O015")
    orders["O015"].return_order()
    assert orders["O015"].status == OrderStatus.RETURNED

    # E15: O016 confirmar, enviar y entregar -> exito DELIVERED
    orders["O016"].confirm()
    orders["O016"].ship("GUIA-O016")
    orders["O016"].deliver()
    assert orders["O016"].status == OrderStatus.DELIVERED
