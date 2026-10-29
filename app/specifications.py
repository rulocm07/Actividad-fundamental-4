"""TechStore U4 - Specification Pattern y Reglas de Descuento.
Permite evaluar y combinar reglas de negocio desacopladas mediante operadores lógicos (&, |, ~).
"""
from decimal import Decimal
from typing import Tuple
from app.domain import Order


class Specification:
    """Clase base abstracta para el patrón Specification."""
    def is_satisfied_by(self, order: Order) -> bool:
        raise NotImplementedError("Debe implementarse en la subclase")

    def __and__(self, other: "Specification") -> "Specification":
        return AndSpec(self, other)

    def __or__(self, other: "Specification") -> "Specification":
        return OrSpec(self, other)

    def __invert__(self) -> "Specification":
        return NotSpec(self)


class AndSpec(Specification):
    """Composición lógica AND entre dos especificaciones."""
    def __init__(self, left: Specification, right: Specification):
        self.left = left
        self.right = right

    def is_satisfied_by(self, order: Order) -> bool:
        return self.left.is_satisfied_by(order) and self.right.is_satisfied_by(order)


class OrSpec(Specification):
    """Composición lógica OR entre dos especificaciones."""
    def __init__(self, left: Specification, right: Specification):
        self.left = left
        self.right = right

    def is_satisfied_by(self, order: Order) -> bool:
        return self.left.is_satisfied_by(order) or self.right.is_satisfied_by(order)


class NotSpec(Specification):
    """Operador de negación NOT sobre una especificación."""
    def __init__(self, spec: Specification):
        self.spec = spec

    def is_satisfied_by(self, order: Order) -> bool:
        return not self.spec.is_satisfied_by(order)


class MinimumAmountSpec(Specification):
    """Valida que el total del pedido sea estrictamente mayor que un importe umbral."""
    def __init__(self, amount: Decimal):
        self.amount = Decimal(str(amount))

    def is_satisfied_by(self, order: Order) -> bool:
        return order.total.amount > self.amount


class VIPCustomerSpec(Specification):
    """Valida que el cliente sea VIP."""
    def is_satisfied_by(self, order: Order) -> bool:
        return bool(order.customer.is_vip)


class MinimumUnitsSpec(Specification):
    """Valida que el pedido tenga al menos un número mínimo de unidades (>=)."""
    def __init__(self, min_units: int = 4):
        self.min_units = min_units

    def is_satisfied_by(self, order: Order) -> bool:
        return order.units >= self.min_units


class ActivePromotionSpec(Specification):
    """Valida si el pedido tiene una promoción activa."""
    def is_satisfied_by(self, order: Order) -> bool:
        return bool(order.has_promotion)


# Regla de descuento del 10%:
# Cliente VIP, total > 500 MXN, >= 4 unidades, y SIN promoción activa.
ten_percent_spec = (
    MinimumAmountSpec(Decimal("500"))
    & VIPCustomerSpec()
    & MinimumUnitsSpec(4)
    & ~ActivePromotionSpec()
)

# Regla de descuento del 5%:
# Total > 5000 MXN y SIN promoción activa.
five_percent_spec = (
    MinimumAmountSpec(Decimal("5000"))
    & ~ActivePromotionSpec()
)


def evaluate_discount(order: Order) -> Tuple[Decimal, str]:
    """Evalúa las reglas de descuento con prioridad:
    10% si se cumple la regla VIP + monto > 500 + unidades >= 4 + sin promoción.
    5% si se cumple monto > 5000 + sin promoción.
    0% en cualquier otro caso.

    Retorna una tupla (tasa_decimal, etiqueta_porcentaje), ej. (Decimal('0.10'), '10%').
    """
    if ten_percent_spec.is_satisfied_by(order):
        return Decimal("0.10"), "10%"
    if five_percent_spec.is_satisfied_by(order):
        return Decimal("0.05"), "5%"
    return Decimal("0.00"), "0%"
