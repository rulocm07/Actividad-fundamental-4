"""TechStore U4 - Dominio del Negocio (Entities, Value Objects, Domain Events).
Implementación del núcleo de negocio siguiendo Domain-Driven Design (DDD).
"""
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from datetime import datetime, timezone
from typing import List, Optional


class DomainException(Exception):
    """Excepción base del dominio de negocio."""
    pass


class InvalidOrderData(DomainException):
    """Lanzada cuando los datos de un pedido o componente violan las invariantes del dominio."""
    pass


class InvalidOrderTransition(DomainException):
    """Lanzada cuando se intenta una transición de estado no permitida."""
    pass


class OrderItemLimitExceeded(DomainException):
    """Lanzada cuando el número total de unidades en el pedido excede el límite de 20."""
    pass


@dataclass(frozen=True)
class Money:
    """Value Object inmutable para representar valores monetarios con precisión decimal."""
    amount: Decimal
    currency: str = "MXN"

    def __post_init__(self):
        if not isinstance(self.amount, Decimal):
            object.__setattr__(self, "amount", Decimal(str(self.amount)))
        if not self.amount.is_finite() or self.amount < 0:
            raise InvalidOrderData("Monto inválido")

    def add(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise InvalidOrderData("Monedas distintas")
        return Money(self.amount + other.amount, self.currency)

    def __str__(self) -> str:
        return f"{self.amount:.2f} {self.currency}"


@dataclass(frozen=True)
class Customer:
    """Entidad Cliente con identificación, membresía VIP y estatus de actividad."""
    id: str
    is_vip: bool = False
    active: bool = True


@dataclass(frozen=True)
class OrderItem:
    """Value Object que representa un renglón de pedido con cálculo inmutable de subtotal."""
    sku: str
    quantity: int
    unit_price: Money

    def __post_init__(self):
        if not self.sku or not self.sku.strip() or self.quantity <= 0:
            raise InvalidOrderData("Artículo inválido")

    @property
    def subtotal(self) -> Money:
        return Money(self.unit_price.amount * self.quantity, self.unit_price.currency)


class OrderStatus(str, Enum):
    """Estados del ciclo de vida de un pedido según la máquina de estados TechStore."""
    DRAFT = "DRAFT"
    CONFIRMED = "CONFIRMED"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"
    RETURNED = "RETURNED"


@dataclass(frozen=True)
class DomainEvent:
    """Evento de dominio inmutable registrado cuando ocurre un cambio relevante de estado."""
    name: str
    order_id: str
    occurred_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


@dataclass
class Order:
    """Aggregate Root que gobierna las reglas de negocio, ciclo de vida e invariantes de pedidos."""
    customer: Customer
    id: str
    has_promotion: bool = False
    status: OrderStatus = OrderStatus.DRAFT
    items: List[OrderItem] = field(default_factory=list)
    events: List[DomainEvent] = field(default_factory=list)
    tracking_number: Optional[str] = None
    cancellation_reason: Optional[str] = None

    @property
    def units(self) -> int:
        """Suma de las cantidades de todas las unidades de los artículos del pedido."""
        return sum(item.quantity for item in self.items)

    @property
    def total(self) -> Money:
        """Suma total de los subtotales de todos los artículos."""
        amount = sum((x.subtotal.amount for x in self.items), Decimal("0"))
        return Money(amount)

    def add_item(self, item: OrderItem) -> None:
        """Agrega un artículo al pedido verificando el estado y límite de 20 unidades."""
        if self.status != OrderStatus.DRAFT:
            raise InvalidOrderTransition("Solo DRAFT admite artículos")
        if self.units + item.quantity > 20:
            raise OrderItemLimitExceeded("Máximo 20 unidades")
        if item.unit_price.currency != "MXN":
            raise InvalidOrderData("Solo MXN")
        self.items.append(item)

    def confirm(self) -> None:
        """Transición de DRAFT a CONFIRMED. Requiere artículos y cliente activo."""
        if self.status != OrderStatus.DRAFT:
            raise InvalidOrderTransition("Solo DRAFT")
        if not self.items or not self.customer.active:
            raise InvalidOrderData("Requiere artículos y cliente activo")
        self.status = OrderStatus.CONFIRMED
        self.events.append(DomainEvent("OrderConfirmed", self.id))

    def ship(self, tracking_number: str) -> None:
        """Transición de CONFIRMED a SHIPPED. Requiere número de guía obligatorio."""
        if self.status != OrderStatus.CONFIRMED:
            raise InvalidOrderTransition("Solo CONFIRMED puede ser enviado")
        if not tracking_number or not str(tracking_number).strip():
            raise InvalidOrderData("La guía de envío es obligatoria")
        self.tracking_number = str(tracking_number).strip()
        self.status = OrderStatus.SHIPPED
        self.events.append(DomainEvent("OrderShipped", self.id))

    def cancel(self, reason: str) -> None:
        """Transición de CONFIRMED a CANCELLED. Requiere motivo no vacío."""
        if self.status != OrderStatus.CONFIRMED:
            raise InvalidOrderTransition("Solo CONFIRMED puede ser cancelado")
        if not reason or not str(reason).strip():
            raise InvalidOrderData("El motivo de cancelación es obligatorio")
        self.cancellation_reason = str(reason).strip()
        self.status = OrderStatus.CANCELLED
        self.events.append(DomainEvent("OrderCancelled", self.id))

    def deliver(self) -> None:
        """Transición de SHIPPED a DELIVERED."""
        if self.status != OrderStatus.SHIPPED:
            raise InvalidOrderTransition("Solo SHIPPED puede ser entregado")
        self.status = OrderStatus.DELIVERED
        self.events.append(DomainEvent("OrderDelivered", self.id))

    def return_order(self) -> None:
        """Transición de SHIPPED a RETURNED."""
        if self.status != OrderStatus.SHIPPED:
            raise InvalidOrderTransition("Solo SHIPPED puede ser devuelto")
        self.status = OrderStatus.RETURNED
        self.events.append(DomainEvent("OrderReturned", self.id))
