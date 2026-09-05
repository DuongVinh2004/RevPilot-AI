"""
RevPilot AI — Canonical Domain Entity Models and Contracts (Phase 01)
Authoritative domain models, composite keys, invariant validations, and serialization.
Conforms to CANONICAL-DATA-MODEL.md §3, §4 and TASK-P01-001.
"""

from __future__ import annotations
import hashlib
import re
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Optional, TypeVar, Type

from revpilot.shared.identifiers import TenantId
from revpilot.shared.temporal import UtcDateTime
from revpilot.shared.monetary import Currency
from revpilot.shared.errors import ValidationError
from revpilot.shared.results import Result, Success, Failure

from revpilot.modules.canonical.enums import (
    CustomerSegment,
    AccountTier,
    CustomerStatus,
    OrderStatus,
    CancellationReason,
    DispatchStatus,
    ShipmentStatus,
    DelayReason,
    TicketTopic,
    TicketPriority,
    TicketSeverity,
    TicketStatus,
    FacilityType,
    MaintenanceEventType,
    MaintenanceType,
    MaintenanceSeverity,
    ContractType,
    ContractStatus,
    ClauseType,
    GatewayProvider,
    TransactionType,
    PaymentStatus,
    DataClassification,
    CurrencyCode,
)

_EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
_COUNTRY_CODE_REGEX = re.compile(r"^[A-Z]{2}$")
_HEX64_REGEX = re.compile(r"^[a-fA-F0-9]{64}$")


class CanonicalValidationError(ValidationError):
    """Domain validation error for canonical data contracts."""

    def __init__(
        self,
        message: str = "Invalid canonical entity data",
        code: str = "CANONICAL_VALIDATION_ERROR",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, details=details)
        self.code = code


class TenantRequiredError(CanonicalValidationError):
    """Raised when tenant_id is missing, null, or invalid."""

    def __init__(
        self,
        message: str = "Tenant context required",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message=message, code="TENANT_REQUIRED_ERROR", details=details)


def _validate_tenant_id(val: Any) -> TenantId:
    """Validate and normalize TenantId, failing closed on None or empty."""
    if val is None:
        raise TenantRequiredError("Tenant context required: tenant_id cannot be None")
    if isinstance(val, str):
        cleaned = val.strip()
        if not cleaned:
            raise TenantRequiredError("Tenant context required: tenant_id cannot be empty")
        try:
            return TenantId(cleaned)
        except Exception as exc:
            raise TenantRequiredError(f"Invalid tenant_id format: {exc}") from exc
    if isinstance(val, TenantId):
        return val
    raise TenantRequiredError(f"tenant_id must be TenantId or str, got {type(val).__name__}")


def _validate_entity_id(val: Any, entity_name: str) -> str:
    """Validate non-empty string identifier."""
    if not isinstance(val, str) or not val.strip():
        raise CanonicalValidationError(f"{entity_name} id must be a non-empty string")
    return val.strip()


def _validate_enum(val: Any, enum_cls: Type[Any], field_name: str) -> Any:
    """Validate and convert enum value."""
    if isinstance(val, enum_cls):
        return val
    if isinstance(val, str):
        try:
            return enum_cls(val)
        except ValueError:
            raise CanonicalValidationError(
                f"Invalid {field_name}: {val!r}. Must be one of {[e.value for e in enum_cls]}"
            )
    raise CanonicalValidationError(
        f"{field_name} must be {enum_cls.__name__} or str, got {type(val).__name__}"
    )


def _validate_currency(val: Any) -> Currency:
    """Validate and convert Currency value."""
    if isinstance(val, Currency):
        return val
    if isinstance(val, str):
        try:
            return Currency.from_str(val)
        except (ValueError, TypeError) as exc:
            raise CanonicalValidationError(f"Invalid currency code: {val!r}") from exc
    raise CanonicalValidationError(f"currency must be Currency or str, got {type(val).__name__}")


def _validate_utc(val: Any, field_name: str) -> UtcDateTime:
    """Validate and convert UtcDateTime value."""
    if isinstance(val, UtcDateTime):
        return val
    if isinstance(val, str):
        try:
            return UtcDateTime.from_iso(val)
        except Exception as exc:
            raise CanonicalValidationError(f"Invalid timestamp format for {field_name}: {exc}") from exc
    raise CanonicalValidationError(f"{field_name} must be UtcDateTime or ISO str, got {type(val).__name__}")


def _compute_dedup_key(tenant_id: str, entity_name: str, identifier: str, source_system: str = "", source_id: str = "") -> str:
    """Deterministic SHA-256 hash for idempotent replay."""
    seed = f"{tenant_id}:{source_system}:{source_id}" if (source_system and source_id) else f"{tenant_id}:{entity_name}:{identifier}"
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


# =============================================================================
# 1. Customer Entity
# =============================================================================

@dataclass(frozen=True, slots=True)
class Customer:
    """
    Canonical Customer entity (Customer 360 context).
    Primary Key: (tenant_id, id).
    """
    tenant_id: TenantId
    id: str
    name: str
    email: str
    segment: CustomerSegment
    account_tier: AccountTier
    billing_country: str
    contract_mrr_cents: int
    currency: Currency
    status: CustomerStatus
    event_time: UtcDateTime
    effective_from: UtcDateTime
    effective_to: Optional[UtcDateTime] = None
    ingested_at: UtcDateTime = field(default_factory=UtcDateTime.now)
    data_classification: str = "CONFIDENTIAL"
    retention_class: str = "CUSTOMER_RECORD_7YR"
    lineage_trace_id: str = ""
    dedup_key: str = ""
    schema_version: str = "1.0.0"
    source_system: str = ""
    source_id: str = ""

    def __post_init__(self) -> None:
        t_id = _validate_tenant_id(self.tenant_id)
        e_id = _validate_entity_id(self.id, "Customer")
        object.__setattr__(self, "tenant_id", t_id)
        object.__setattr__(self, "id", e_id)

        if not isinstance(self.name, str) or not self.name.strip():
            raise CanonicalValidationError("Customer name cannot be empty")
        object.__setattr__(self, "name", self.name.strip())

        if not isinstance(self.email, str) or not _EMAIL_REGEX.match(self.email.strip()):
            raise CanonicalValidationError(f"Invalid customer email: {self.email!r}")
        object.__setattr__(self, "email", self.email.strip())

        seg = _validate_enum(self.segment, CustomerSegment, "segment")
        tier = _validate_enum(self.account_tier, AccountTier, "account_tier")
        st = _validate_enum(self.status, CustomerStatus, "status")
        curr = _validate_currency(self.currency)
        object.__setattr__(self, "segment", seg)
        object.__setattr__(self, "account_tier", tier)
        object.__setattr__(self, "status", st)
        object.__setattr__(self, "currency", curr)

        country = str(self.billing_country).strip().upper()
        if not _COUNTRY_CODE_REGEX.match(country):
            raise CanonicalValidationError(f"Invalid billing_country: {self.billing_country!r}. Must be ISO 3166-1 alpha-2")
        object.__setattr__(self, "billing_country", country)

        if not isinstance(self.contract_mrr_cents, int) or self.contract_mrr_cents < 0:
            raise CanonicalValidationError(f"contract_mrr_cents must be a non-negative integer, got {self.contract_mrr_cents!r}")

        evt = _validate_utc(self.event_time, "event_time")
        eff_from = _validate_utc(self.effective_from, "effective_from")
        object.__setattr__(self, "event_time", evt)
        object.__setattr__(self, "effective_from", eff_from)

        if self.effective_to is not None:
            eff_to = _validate_utc(self.effective_to, "effective_to")
            if eff_to.value < eff_from.value:
                raise CanonicalValidationError(
                    f"effective_to ({eff_to}) cannot precede effective_from ({eff_from})"
                )
            object.__setattr__(self, "effective_to", eff_to)

        if not isinstance(self.ingested_at, UtcDateTime):
            object.__setattr__(self, "ingested_at", _validate_utc(self.ingested_at, "ingested_at"))

        if not self.dedup_key:
            object.__setattr__(
                self,
                "dedup_key",
                _compute_dedup_key(t_id.value, "Customer", e_id, self.source_system, self.source_id),
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id.value,
            "id": self.id,
            "name": self.name,
            "email": self.email,
            "segment": self.segment.value,
            "account_tier": self.account_tier.value,
            "billing_country": self.billing_country,
            "contract_mrr_cents": self.contract_mrr_cents,
            "currency": self.currency.value,
            "status": self.status.value,
            "event_time": self.event_time.isoformat(),
            "effective_from": self.effective_from.isoformat(),
            "effective_to": self.effective_to.isoformat() if self.effective_to else None,
            "ingested_at": self.ingested_at.isoformat(),
            "data_classification": self.data_classification,
            "retention_class": self.retention_class,
            "lineage_trace_id": self.lineage_trace_id,
            "dedup_key": self.dedup_key,
            "schema_version": self.schema_version,
            "source_system": self.source_system,
            "source_id": self.source_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Customer:
        d = dict(data)
        d["tenant_id"] = _validate_tenant_id(d.get("tenant_id"))
        d["segment"] = CustomerSegment(d["segment"]) if isinstance(d.get("segment"), str) else d.get("segment")
        d["account_tier"] = AccountTier(d["account_tier"]) if isinstance(d.get("account_tier"), str) else d.get("account_tier")
        d["status"] = CustomerStatus(d["status"]) if isinstance(d.get("status"), str) else d.get("status")
        d["currency"] = Currency.from_str(d["currency"]) if isinstance(d.get("currency"), str) else d.get("currency")
        d["event_time"] = _validate_utc(d["event_time"], "event_time") if "event_time" in d else UtcDateTime.now()
        d["effective_from"] = _validate_utc(d["effective_from"], "effective_from") if "effective_from" in d else UtcDateTime.now()
        if d.get("effective_to"):
            d["effective_to"] = _validate_utc(d["effective_to"], "effective_to")
        if d.get("ingested_at"):
            d["ingested_at"] = _validate_utc(d["ingested_at"], "ingested_at")
        return cls(**d)

    @classmethod
    def try_create(cls, **kwargs: Any) -> Result[Customer, CanonicalValidationError]:
        try:
            return Success(cls(**kwargs))
        except CanonicalValidationError as err:
            return Failure(err)


CustomerRecord = Customer


# =============================================================================
# 2. Order Entity
# =============================================================================

@dataclass(frozen=True, slots=True)
class Order:
    """
    Canonical Order entity (Fulfillment & Revenue Ledger context).
    Primary Key: (tenant_id, id).
    Enforces monetary equality: total_cents == subtotal_cents + tax_cents + shipping_cents.
    """
    tenant_id: TenantId
    id: str
    customer_id: str
    order_number: str
    order_status: OrderStatus
    currency: Currency
    subtotal_cents: int
    tax_cents: int
    shipping_cents: int
    total_cents: int
    sla_delivery_deadline: UtcDateTime
    event_time: UtcDateTime
    effective_from: UtcDateTime
    cancellation_reason: Optional[CancellationReason] = None
    cancellation_requested_at: Optional[UtcDateTime] = None
    cancelled_at: Optional[UtcDateTime] = None
    effective_to: Optional[UtcDateTime] = None
    ingested_at: UtcDateTime = field(default_factory=UtcDateTime.now)
    data_classification: str = "CONFIDENTIAL"
    retention_class: str = "REVENUE_FINANCIAL_7YR"
    lineage_trace_id: str = ""
    dedup_key: str = ""
    schema_version: str = "1.0.0"
    source_system: str = ""
    source_id: str = ""

    def __post_init__(self) -> None:
        t_id = _validate_tenant_id(self.tenant_id)
        e_id = _validate_entity_id(self.id, "Order")
        c_id = _validate_entity_id(self.customer_id, "Order.customer_id")
        object.__setattr__(self, "tenant_id", t_id)
        object.__setattr__(self, "id", e_id)
        object.__setattr__(self, "customer_id", c_id)

        if not isinstance(self.order_number, str) or not self.order_number.strip():
            raise CanonicalValidationError("order_number cannot be empty")
        object.__setattr__(self, "order_number", self.order_number.strip())

        st = _validate_enum(self.order_status, OrderStatus, "order_status")
        curr = _validate_currency(self.currency)
        object.__setattr__(self, "order_status", st)
        object.__setattr__(self, "currency", curr)

        # Monetary checks
        for name, val in [
            ("subtotal_cents", self.subtotal_cents),
            ("tax_cents", self.tax_cents),
            ("shipping_cents", self.shipping_cents),
            ("total_cents", self.total_cents),
        ]:
            if not isinstance(val, int) or val < 0:
                raise CanonicalValidationError(f"{name} must be a non-negative integer, got {val!r}")

        expected_total = self.subtotal_cents + self.tax_cents + self.shipping_cents
        if self.total_cents != expected_total:
            raise CanonicalValidationError(
                f"Monetary invariant violated: total_cents ({self.total_cents}) != "
                f"subtotal ({self.subtotal_cents}) + tax ({self.tax_cents}) + shipping ({self.shipping_cents}) = {expected_total}"
            )

        evt = _validate_utc(self.event_time, "event_time")
        eff_from = _validate_utc(self.effective_from, "effective_from")
        sla = _validate_utc(self.sla_delivery_deadline, "sla_delivery_deadline")
        object.__setattr__(self, "event_time", evt)
        object.__setattr__(self, "effective_from", eff_from)
        object.__setattr__(self, "sla_delivery_deadline", sla)

        if self.cancellation_reason is not None:
            reason = _validate_enum(self.cancellation_reason, CancellationReason, "cancellation_reason")
            object.__setattr__(self, "cancellation_reason", reason)

        if self.cancelled_at is not None:
            c_at = _validate_utc(self.cancelled_at, "cancelled_at")
            if c_at.value < evt.value:
                raise CanonicalValidationError(f"cancelled_at ({c_at}) cannot precede event_time ({evt})")
            object.__setattr__(self, "cancelled_at", c_at)

        if self.cancellation_requested_at is not None:
            req_at = _validate_utc(self.cancellation_requested_at, "cancellation_requested_at")
            object.__setattr__(self, "cancellation_requested_at", req_at)

        if self.effective_to is not None:
            eff_to = _validate_utc(self.effective_to, "effective_to")
            if eff_to.value < eff_from.value:
                raise CanonicalValidationError(
                    f"effective_to ({eff_to}) cannot precede effective_from ({eff_from})"
                )
            object.__setattr__(self, "effective_to", eff_to)

        if not isinstance(self.ingested_at, UtcDateTime):
            object.__setattr__(self, "ingested_at", _validate_utc(self.ingested_at, "ingested_at"))

        if not self.dedup_key:
            object.__setattr__(
                self,
                "dedup_key",
                _compute_dedup_key(t_id.value, "Order", e_id, self.source_system, self.source_id),
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id.value,
            "id": self.id,
            "customer_id": self.customer_id,
            "order_number": self.order_number,
            "order_status": self.order_status.value,
            "currency": self.currency.value,
            "subtotal_cents": self.subtotal_cents,
            "tax_cents": self.tax_cents,
            "shipping_cents": self.shipping_cents,
            "total_cents": self.total_cents,
            "sla_delivery_deadline": self.sla_delivery_deadline.isoformat(),
            "event_time": self.event_time.isoformat(),
            "effective_from": self.effective_from.isoformat(),
            "cancellation_reason": self.cancellation_reason.value if self.cancellation_reason else None,
            "cancellation_requested_at": self.cancellation_requested_at.isoformat() if self.cancellation_requested_at else None,
            "cancelled_at": self.cancelled_at.isoformat() if self.cancelled_at else None,
            "effective_to": self.effective_to.isoformat() if self.effective_to else None,
            "ingested_at": self.ingested_at.isoformat(),
            "data_classification": self.data_classification,
            "retention_class": self.retention_class,
            "lineage_trace_id": self.lineage_trace_id,
            "dedup_key": self.dedup_key,
            "schema_version": self.schema_version,
            "source_system": self.source_system,
            "source_id": self.source_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Order:
        d = dict(data)
        d["tenant_id"] = _validate_tenant_id(d.get("tenant_id"))
        d["order_status"] = OrderStatus(d["order_status"]) if isinstance(d.get("order_status"), str) else d.get("order_status")
        d["currency"] = Currency.from_str(d["currency"]) if isinstance(d.get("currency"), str) else d.get("currency")
        if d.get("cancellation_reason"):
            d["cancellation_reason"] = CancellationReason(d["cancellation_reason"]) if isinstance(d.get("cancellation_reason"), str) else d.get("cancellation_reason")
        d["sla_delivery_deadline"] = _validate_utc(d["sla_delivery_deadline"], "sla_delivery_deadline")
        d["event_time"] = _validate_utc(d["event_time"], "event_time")
        d["effective_from"] = _validate_utc(d["effective_from"], "effective_from")
        if d.get("cancellation_requested_at"):
            d["cancellation_requested_at"] = _validate_utc(d["cancellation_requested_at"], "cancellation_requested_at")
        if d.get("cancelled_at"):
            d["cancelled_at"] = _validate_utc(d["cancelled_at"], "cancelled_at")
        if d.get("effective_to"):
            d["effective_to"] = _validate_utc(d["effective_to"], "effective_to")
        if d.get("ingested_at"):
            d["ingested_at"] = _validate_utc(d["ingested_at"], "ingested_at")
        return cls(**d)

    @classmethod
    def try_create(cls, **kwargs: Any) -> Result[Order, CanonicalValidationError]:
        try:
            return Success(cls(**kwargs))
        except CanonicalValidationError as err:
            return Failure(err)


OrderRecord = Order


# =============================================================================
# 3. OrderLine Entity
# =============================================================================

@dataclass(frozen=True, slots=True)
class OrderLine:
    """
    Canonical OrderLine entity (Fulfillment context).
    Primary Key: (tenant_id, id).
    Foreign Key: (tenant_id, order_id) -> Order.
    Enforces: total_price_cents == quantity * unit_price_cents.
    """
    tenant_id: TenantId
    id: str
    order_id: str
    sku: str
    product_name: str
    product_category: str
    quantity: int
    unit_price_cents: int
    total_price_cents: int
    event_time: UtcDateTime
    effective_from: UtcDateTime
    effective_to: Optional[UtcDateTime] = None
    ingested_at: UtcDateTime = field(default_factory=UtcDateTime.now)
    data_classification: str = "INTERNAL"
    retention_class: str = "REVENUE_FINANCIAL_7YR"
    lineage_trace_id: str = ""
    dedup_key: str = ""
    schema_version: str = "1.0.0"
    source_system: str = ""
    source_id: str = ""

    def __post_init__(self) -> None:
        t_id = _validate_tenant_id(self.tenant_id)
        e_id = _validate_entity_id(self.id, "OrderLine")
        o_id = _validate_entity_id(self.order_id, "OrderLine.order_id")
        object.__setattr__(self, "tenant_id", t_id)
        object.__setattr__(self, "id", e_id)
        object.__setattr__(self, "order_id", o_id)

        if not isinstance(self.sku, str) or not self.sku.strip():
            raise CanonicalValidationError("sku cannot be empty")
        if not isinstance(self.product_name, str) or not self.product_name.strip():
            raise CanonicalValidationError("product_name cannot be empty")
        if not isinstance(self.product_category, str) or not self.product_category.strip():
            raise CanonicalValidationError("product_category cannot be empty")

        if not isinstance(self.quantity, int) or self.quantity <= 0:
            raise CanonicalValidationError(f"quantity must be a positive integer (> 0), got {self.quantity!r}")

        if not isinstance(self.unit_price_cents, int) or self.unit_price_cents < 0:
            raise CanonicalValidationError(f"unit_price_cents must be non-negative, got {self.unit_price_cents!r}")

        expected_total = self.quantity * self.unit_price_cents
        if self.total_price_cents != expected_total:
            raise CanonicalValidationError(
                f"total_price_cents ({self.total_price_cents}) != quantity ({self.quantity}) * unit_price_cents ({self.unit_price_cents}) = {expected_total}"
            )

        evt = _validate_utc(self.event_time, "event_time")
        eff_from = _validate_utc(self.effective_from, "effective_from")
        object.__setattr__(self, "event_time", evt)
        object.__setattr__(self, "effective_from", eff_from)

        if self.effective_to is not None:
            eff_to = _validate_utc(self.effective_to, "effective_to")
            if eff_to.value < eff_from.value:
                raise CanonicalValidationError(
                    f"effective_to ({eff_to}) cannot precede effective_from ({eff_from})"
                )
            object.__setattr__(self, "effective_to", eff_to)

        if not isinstance(self.ingested_at, UtcDateTime):
            object.__setattr__(self, "ingested_at", _validate_utc(self.ingested_at, "ingested_at"))

        if not self.dedup_key:
            object.__setattr__(
                self,
                "dedup_key",
                _compute_dedup_key(t_id.value, "OrderLine", e_id, self.source_system, self.source_id),
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id.value,
            "id": self.id,
            "order_id": self.order_id,
            "sku": self.sku,
            "product_name": self.product_name,
            "product_category": self.product_category,
            "quantity": self.quantity,
            "unit_price_cents": self.unit_price_cents,
            "total_price_cents": self.total_price_cents,
            "event_time": self.event_time.isoformat(),
            "effective_from": self.effective_from.isoformat(),
            "effective_to": self.effective_to.isoformat() if self.effective_to else None,
            "ingested_at": self.ingested_at.isoformat(),
            "data_classification": self.data_classification,
            "retention_class": self.retention_class,
            "lineage_trace_id": self.lineage_trace_id,
            "dedup_key": self.dedup_key,
            "schema_version": self.schema_version,
            "source_system": self.source_system,
            "source_id": self.source_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OrderLine:
        d = dict(data)
        d["tenant_id"] = _validate_tenant_id(d.get("tenant_id"))
        d["event_time"] = _validate_utc(d["event_time"], "event_time")
        d["effective_from"] = _validate_utc(d["effective_from"], "effective_from")
        if d.get("effective_to"):
            d["effective_to"] = _validate_utc(d["effective_to"], "effective_to")
        if d.get("ingested_at"):
            d["ingested_at"] = _validate_utc(d["ingested_at"], "ingested_at")
        return cls(**d)

    @classmethod
    def try_create(cls, **kwargs: Any) -> Result[OrderLine, CanonicalValidationError]:
        try:
            return Success(cls(**kwargs))
        except CanonicalValidationError as err:
            return Failure(err)


OrderLineRecord = OrderLine


# =============================================================================
# 4. Shipment Entity
# =============================================================================

@dataclass(frozen=True, slots=True)
class Shipment:
    """
    Canonical Shipment entity (Fulfillment context).
    Primary Key: (tenant_id, id).
    Foreign Key: (tenant_id, order_id) -> Order.
    """
    tenant_id: TenantId
    id: str
    order_id: str
    tracking_number: str
    carrier_id: str
    carrier_name: str
    warehouse_id: str
    origin_region: str
    destination_region: str
    dispatch_status: DispatchStatus
    estimated_delivery_at: UtcDateTime
    event_time: UtcDateTime
    effective_from: UtcDateTime
    dispatched_at: Optional[UtcDateTime] = None
    actual_delivered_at: Optional[UtcDateTime] = None
    delay_reason: Optional[DelayReason] = None
    is_delayed: bool = False
    effective_to: Optional[UtcDateTime] = None
    ingested_at: UtcDateTime = field(default_factory=UtcDateTime.now)
    data_classification: str = "INTERNAL"
    retention_class: str = "OPERATIONAL_LOGISTICS_5YR"
    lineage_trace_id: str = ""
    dedup_key: str = ""
    schema_version: str = "1.0.0"
    source_system: str = ""
    source_id: str = ""

    def __post_init__(self) -> None:
        t_id = _validate_tenant_id(self.tenant_id)
        e_id = _validate_entity_id(self.id, "Shipment")
        o_id = _validate_entity_id(self.order_id, "Shipment.order_id")
        object.__setattr__(self, "tenant_id", t_id)
        object.__setattr__(self, "id", e_id)
        object.__setattr__(self, "order_id", o_id)

        st = _validate_enum(self.dispatch_status, DispatchStatus, "dispatch_status")
        object.__setattr__(self, "dispatch_status", st)

        if self.delay_reason is not None:
            dr = _validate_enum(self.delay_reason, DelayReason, "delay_reason")
            object.__setattr__(self, "delay_reason", dr)

        evt = _validate_utc(self.event_time, "event_time")
        eff_from = _validate_utc(self.effective_from, "effective_from")
        est_del = _validate_utc(self.estimated_delivery_at, "estimated_delivery_at")
        object.__setattr__(self, "event_time", evt)
        object.__setattr__(self, "effective_from", eff_from)
        object.__setattr__(self, "estimated_delivery_at", est_del)

        if self.dispatched_at is not None:
            disp_at = _validate_utc(self.dispatched_at, "dispatched_at")
            object.__setattr__(self, "dispatched_at", disp_at)

        if self.actual_delivered_at is not None:
            act_del = _validate_utc(self.actual_delivered_at, "actual_delivered_at")
            if self.dispatched_at is not None and act_del.value < self.dispatched_at.value:
                raise CanonicalValidationError(
                    f"actual_delivered_at ({act_del}) cannot precede dispatched_at ({self.dispatched_at})"
                )
            object.__setattr__(self, "actual_delivered_at", act_del)

        if self.effective_to is not None:
            eff_to = _validate_utc(self.effective_to, "effective_to")
            if eff_to.value < eff_from.value:
                raise CanonicalValidationError(
                    f"effective_to ({eff_to}) cannot precede effective_from ({eff_from})"
                )
            object.__setattr__(self, "effective_to", eff_to)

        if not isinstance(self.ingested_at, UtcDateTime):
            object.__setattr__(self, "ingested_at", _validate_utc(self.ingested_at, "ingested_at"))

        if not self.dedup_key:
            object.__setattr__(
                self,
                "dedup_key",
                _compute_dedup_key(t_id.value, "Shipment", e_id, self.source_system, self.source_id),
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id.value,
            "id": self.id,
            "order_id": self.order_id,
            "tracking_number": self.tracking_number,
            "carrier_id": self.carrier_id,
            "carrier_name": self.carrier_name,
            "warehouse_id": self.warehouse_id,
            "origin_region": self.origin_region,
            "destination_region": self.destination_region,
            "dispatch_status": self.dispatch_status.value,
            "estimated_delivery_at": self.estimated_delivery_at.isoformat(),
            "event_time": self.event_time.isoformat(),
            "effective_from": self.effective_from.isoformat(),
            "dispatched_at": self.dispatched_at.isoformat() if self.dispatched_at else None,
            "actual_delivered_at": self.actual_delivered_at.isoformat() if self.actual_delivered_at else None,
            "delay_reason": self.delay_reason.value if self.delay_reason else None,
            "is_delayed": self.is_delayed,
            "effective_to": self.effective_to.isoformat() if self.effective_to else None,
            "ingested_at": self.ingested_at.isoformat(),
            "data_classification": self.data_classification,
            "retention_class": self.retention_class,
            "lineage_trace_id": self.lineage_trace_id,
            "dedup_key": self.dedup_key,
            "schema_version": self.schema_version,
            "source_system": self.source_system,
            "source_id": self.source_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Shipment:
        d = dict(data)
        d["tenant_id"] = _validate_tenant_id(d.get("tenant_id"))
        d["dispatch_status"] = DispatchStatus(d["dispatch_status"]) if isinstance(d.get("dispatch_status"), str) else d.get("dispatch_status")
        if d.get("delay_reason"):
            d["delay_reason"] = DelayReason(d["delay_reason"]) if isinstance(d.get("delay_reason"), str) else d.get("delay_reason")
        d["estimated_delivery_at"] = _validate_utc(d["estimated_delivery_at"], "estimated_delivery_at")
        d["event_time"] = _validate_utc(d["event_time"], "event_time")
        d["effective_from"] = _validate_utc(d["effective_from"], "effective_from")
        if d.get("dispatched_at"):
            d["dispatched_at"] = _validate_utc(d["dispatched_at"], "dispatched_at")
        if d.get("actual_delivered_at"):
            d["actual_delivered_at"] = _validate_utc(d["actual_delivered_at"], "actual_delivered_at")
        if d.get("effective_to"):
            d["effective_to"] = _validate_utc(d["effective_to"], "effective_to")
        if d.get("ingested_at"):
            d["ingested_at"] = _validate_utc(d["ingested_at"], "ingested_at")
        return cls(**d)

    @classmethod
    def try_create(cls, **kwargs: Any) -> Result[Shipment, CanonicalValidationError]:
        try:
            return Success(cls(**kwargs))
        except CanonicalValidationError as err:
            return Failure(err)


ShipmentRecord = Shipment


# =============================================================================
# 5. SupportTicket Entity
# =============================================================================

@dataclass(frozen=True, slots=True)
class SupportTicket:
    """
    Canonical SupportTicket entity (Service Intelligence context).
    Primary Key: (tenant_id, id).
    Relationships: Customer (mandatory), Order (optional).
    """
    tenant_id: TenantId
    id: str
    customer_id: str
    ticket_number: str
    topic: TicketTopic
    priority: TicketPriority
    status: TicketStatus
    subject: str
    transcript_text: str
    event_time: UtcDateTime
    effective_from: UtcDateTime
    order_id: Optional[str] = None
    first_response_at: Optional[UtcDateTime] = None
    resolved_at: Optional[UtcDateTime] = None
    effective_to: Optional[UtcDateTime] = None
    ingested_at: UtcDateTime = field(default_factory=UtcDateTime.now)
    data_classification: str = "RESTRICTED_PII"
    retention_class: str = "SUPPORT_TRANSCRIPT_3YR"
    lineage_trace_id: str = ""
    dedup_key: str = ""
    schema_version: str = "1.0.0"
    source_system: str = ""
    source_id: str = ""

    def __post_init__(self) -> None:
        t_id = _validate_tenant_id(self.tenant_id)
        e_id = _validate_entity_id(self.id, "SupportTicket")
        c_id = _validate_entity_id(self.customer_id, "SupportTicket.customer_id")
        object.__setattr__(self, "tenant_id", t_id)
        object.__setattr__(self, "id", e_id)
        object.__setattr__(self, "customer_id", c_id)

        top = _validate_enum(self.topic, TicketTopic, "topic")
        prio = _validate_enum(self.priority, TicketPriority, "priority")
        st = _validate_enum(self.status, TicketStatus, "status")
        object.__setattr__(self, "topic", top)
        object.__setattr__(self, "priority", prio)
        object.__setattr__(self, "status", st)

        evt = _validate_utc(self.event_time, "event_time")
        eff_from = _validate_utc(self.effective_from, "effective_from")
        object.__setattr__(self, "event_time", evt)
        object.__setattr__(self, "effective_from", eff_from)

        if self.first_response_at is not None:
            fr_at = _validate_utc(self.first_response_at, "first_response_at")
            object.__setattr__(self, "first_response_at", fr_at)

        if self.resolved_at is not None:
            res_at = _validate_utc(self.resolved_at, "resolved_at")
            if res_at.value < evt.value:
                raise CanonicalValidationError(
                    f"resolved_at ({res_at}) cannot precede event_time ({evt})"
                )
            object.__setattr__(self, "resolved_at", res_at)

        if self.effective_to is not None:
            eff_to = _validate_utc(self.effective_to, "effective_to")
            if eff_to.value < eff_from.value:
                raise CanonicalValidationError(
                    f"effective_to ({eff_to}) cannot precede effective_from ({eff_from})"
                )
            object.__setattr__(self, "effective_to", eff_to)

        if not isinstance(self.ingested_at, UtcDateTime):
            object.__setattr__(self, "ingested_at", _validate_utc(self.ingested_at, "ingested_at"))

        if not self.dedup_key:
            object.__setattr__(
                self,
                "dedup_key",
                _compute_dedup_key(t_id.value, "SupportTicket", e_id, self.source_system, self.source_id),
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id.value,
            "id": self.id,
            "customer_id": self.customer_id,
            "ticket_number": self.ticket_number,
            "topic": self.topic.value,
            "priority": self.priority.value,
            "status": self.status.value,
            "subject": self.subject,
            "transcript_text": self.transcript_text,
            "event_time": self.event_time.isoformat(),
            "effective_from": self.effective_from.isoformat(),
            "order_id": self.order_id,
            "first_response_at": self.first_response_at.isoformat() if self.first_response_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "effective_to": self.effective_to.isoformat() if self.effective_to else None,
            "ingested_at": self.ingested_at.isoformat(),
            "data_classification": self.data_classification,
            "retention_class": self.retention_class,
            "lineage_trace_id": self.lineage_trace_id,
            "dedup_key": self.dedup_key,
            "schema_version": self.schema_version,
            "source_system": self.source_system,
            "source_id": self.source_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SupportTicket:
        d = dict(data)
        d["tenant_id"] = _validate_tenant_id(d.get("tenant_id"))
        d["topic"] = TicketTopic(d["topic"]) if isinstance(d.get("topic"), str) else d.get("topic")
        d["priority"] = TicketPriority(d["priority"]) if isinstance(d.get("priority"), str) else d.get("priority")
        d["status"] = TicketStatus(d["status"]) if isinstance(d.get("status"), str) else d.get("status")
        d["event_time"] = _validate_utc(d["event_time"], "event_time")
        d["effective_from"] = _validate_utc(d["effective_from"], "effective_from")
        if d.get("first_response_at"):
            d["first_response_at"] = _validate_utc(d["first_response_at"], "first_response_at")
        if d.get("resolved_at"):
            d["resolved_at"] = _validate_utc(d["resolved_at"], "resolved_at")
        if d.get("effective_to"):
            d["effective_to"] = _validate_utc(d["effective_to"], "effective_to")
        if d.get("ingested_at"):
            d["ingested_at"] = _validate_utc(d["ingested_at"], "ingested_at")
        return cls(**d)

    @classmethod
    def try_create(cls, **kwargs: Any) -> Result[SupportTicket, CanonicalValidationError]:
        try:
            return Success(cls(**kwargs))
        except CanonicalValidationError as err:
            return Failure(err)


SupportTicketRecord = SupportTicket


# =============================================================================
# 6. MaintenanceEvent Entity
# =============================================================================

@dataclass(frozen=True, slots=True)
class MaintenanceEvent:
    """
    Canonical MaintenanceEvent entity (Fulfillment context).
    Primary Key: (tenant_id, id).
    Enforces impact_capacity_reduction_pct between 0.00 and 100.00.
    """
    tenant_id: TenantId
    id: str
    facility_id: str
    facility_type: FacilityType
    event_type: MaintenanceEventType
    severity: MaintenanceSeverity
    start_window: UtcDateTime
    impact_capacity_reduction_pct: Decimal
    description: str
    event_time: UtcDateTime
    effective_from: UtcDateTime
    end_window: Optional[UtcDateTime] = None
    effective_to: Optional[UtcDateTime] = None
    ingested_at: UtcDateTime = field(default_factory=UtcDateTime.now)
    data_classification: str = "INTERNAL"
    retention_class: str = "FACILITY_OPS_5YR"
    lineage_trace_id: str = ""
    dedup_key: str = ""
    schema_version: str = "1.0.0"
    source_system: str = ""
    source_id: str = ""

    def __post_init__(self) -> None:
        t_id = _validate_tenant_id(self.tenant_id)
        e_id = _validate_entity_id(self.id, "MaintenanceEvent")
        f_id = _validate_entity_id(self.facility_id, "MaintenanceEvent.facility_id")
        object.__setattr__(self, "tenant_id", t_id)
        object.__setattr__(self, "id", e_id)
        object.__setattr__(self, "facility_id", f_id)

        ft = _validate_enum(self.facility_type, FacilityType, "facility_type")
        et = _validate_enum(self.event_type, MaintenanceEventType, "event_type")
        sev = _validate_enum(self.severity, MaintenanceSeverity, "severity")
        object.__setattr__(self, "facility_type", ft)
        object.__setattr__(self, "event_type", et)
        object.__setattr__(self, "severity", sev)

        # Capacity reduction percentage validation
        pct = self.impact_capacity_reduction_pct
        if not isinstance(pct, Decimal):
            try:
                pct = Decimal(str(pct))
            except Exception as exc:
                raise CanonicalValidationError(f"Invalid impact_capacity_reduction_pct: {pct!r}") from exc
        if pct < Decimal("0.0") or pct > Decimal("100.0"):
            raise CanonicalValidationError(
                f"impact_capacity_reduction_pct must be between 0.00 and 100.00, got {pct}"
            )
        object.__setattr__(self, "impact_capacity_reduction_pct", pct)

        start = _validate_utc(self.start_window, "start_window")
        evt = _validate_utc(self.event_time, "event_time")
        eff_from = _validate_utc(self.effective_from, "effective_from")
        object.__setattr__(self, "start_window", start)
        object.__setattr__(self, "event_time", evt)
        object.__setattr__(self, "effective_from", eff_from)

        if self.end_window is not None:
            end = _validate_utc(self.end_window, "end_window")
            if end.value < start.value:
                raise CanonicalValidationError(
                    f"end_window ({end}) cannot precede start_window ({start})"
                )
            object.__setattr__(self, "end_window", end)

        if self.effective_to is not None:
            eff_to = _validate_utc(self.effective_to, "effective_to")
            if eff_to.value < eff_from.value:
                raise CanonicalValidationError(
                    f"effective_to ({eff_to}) cannot precede effective_from ({eff_from})"
                )
            object.__setattr__(self, "effective_to", eff_to)

        if not isinstance(self.ingested_at, UtcDateTime):
            object.__setattr__(self, "ingested_at", _validate_utc(self.ingested_at, "ingested_at"))

        if not self.dedup_key:
            object.__setattr__(
                self,
                "dedup_key",
                _compute_dedup_key(t_id.value, "MaintenanceEvent", e_id, self.source_system, self.source_id),
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id.value,
            "id": self.id,
            "facility_id": self.facility_id,
            "facility_type": self.facility_type.value,
            "event_type": self.event_type.value,
            "severity": self.severity.value,
            "start_window": self.start_window.isoformat(),
            "impact_capacity_reduction_pct": float(self.impact_capacity_reduction_pct),
            "description": self.description,
            "event_time": self.event_time.isoformat(),
            "effective_from": self.effective_from.isoformat(),
            "end_window": self.end_window.isoformat() if self.end_window else None,
            "effective_to": self.effective_to.isoformat() if self.effective_to else None,
            "ingested_at": self.ingested_at.isoformat(),
            "data_classification": self.data_classification,
            "retention_class": self.retention_class,
            "lineage_trace_id": self.lineage_trace_id,
            "dedup_key": self.dedup_key,
            "schema_version": self.schema_version,
            "source_system": self.source_system,
            "source_id": self.source_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MaintenanceEvent:
        d = dict(data)
        d["tenant_id"] = _validate_tenant_id(d.get("tenant_id"))
        d["facility_type"] = FacilityType(d["facility_type"]) if isinstance(d.get("facility_type"), str) else d.get("facility_type")
        d["event_type"] = MaintenanceEventType(d["event_type"]) if isinstance(d.get("event_type"), str) else d.get("event_type")
        d["severity"] = MaintenanceSeverity(d["severity"]) if isinstance(d.get("severity"), str) else d.get("severity")
        d["start_window"] = _validate_utc(d["start_window"], "start_window")
        d["event_time"] = _validate_utc(d["event_time"], "event_time")
        d["effective_from"] = _validate_utc(d["effective_from"], "effective_from")
        if d.get("end_window"):
            d["end_window"] = _validate_utc(d["end_window"], "end_window")
        if d.get("effective_to"):
            d["effective_to"] = _validate_utc(d["effective_to"], "effective_to")
        if d.get("ingested_at"):
            d["ingested_at"] = _validate_utc(d["ingested_at"], "ingested_at")
        return cls(**d)

    @classmethod
    def try_create(cls, **kwargs: Any) -> Result[MaintenanceEvent, CanonicalValidationError]:
        try:
            return Success(cls(**kwargs))
        except CanonicalValidationError as err:
            return Failure(err)


MaintenanceEventRecord = MaintenanceEvent


# =============================================================================
# 7. Contract Entity
# =============================================================================

@dataclass(frozen=True, slots=True)
class Contract:
    """
    Canonical Contract entity (Contract Intelligence context).
    Primary Key: (tenant_id, id).
    Foreign Key: (tenant_id, customer_id) -> Customer.
    """
    tenant_id: TenantId
    id: str
    customer_id: str
    title: str
    contract_type: ContractType
    document_uri: str
    document_digest: str
    event_time: UtcDateTime
    effective_from: UtcDateTime
    status: ContractStatus = ContractStatus.ACTIVE
    effective_to: Optional[UtcDateTime] = None
    ingested_at: UtcDateTime = field(default_factory=UtcDateTime.now)
    data_classification: str = "CONFIDENTIAL"
    retention_class: str = "LEGAL_CONTRACT_10YR"
    lineage_trace_id: str = ""
    dedup_key: str = ""
    schema_version: str = "1.0.0"
    source_system: str = ""
    source_id: str = ""

    def __post_init__(self) -> None:
        t_id = _validate_tenant_id(self.tenant_id)
        e_id = _validate_entity_id(self.id, "Contract")
        c_id = _validate_entity_id(self.customer_id, "Contract.customer_id")
        object.__setattr__(self, "tenant_id", t_id)
        object.__setattr__(self, "id", e_id)
        object.__setattr__(self, "customer_id", c_id)

        ct = _validate_enum(self.contract_type, ContractType, "contract_type")
        st = _validate_enum(self.status, ContractStatus, "status")
        object.__setattr__(self, "contract_type", ct)
        object.__setattr__(self, "status", st)

        if not isinstance(self.document_digest, str) or not _HEX64_REGEX.match(self.document_digest.strip()):
            raise CanonicalValidationError(
                f"Invalid document_digest: {self.document_digest!r}. Must be a 64-character hex string."
            )
        object.__setattr__(self, "document_digest", self.document_digest.strip().lower())

        evt = _validate_utc(self.event_time, "event_time")
        eff_from = _validate_utc(self.effective_from, "effective_from")
        object.__setattr__(self, "event_time", evt)
        object.__setattr__(self, "effective_from", eff_from)

        if self.effective_to is not None:
            eff_to = _validate_utc(self.effective_to, "effective_to")
            if eff_to.value < eff_from.value:
                raise CanonicalValidationError(
                    f"effective_to ({eff_to}) cannot precede effective_from ({eff_from})"
                )
            object.__setattr__(self, "effective_to", eff_to)

        if not isinstance(self.ingested_at, UtcDateTime):
            object.__setattr__(self, "ingested_at", _validate_utc(self.ingested_at, "ingested_at"))

        if not self.dedup_key:
            object.__setattr__(
                self,
                "dedup_key",
                _compute_dedup_key(t_id.value, "Contract", e_id, self.source_system, self.source_id),
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id.value,
            "id": self.id,
            "customer_id": self.customer_id,
            "title": self.title,
            "contract_type": self.contract_type.value,
            "status": self.status.value,
            "document_uri": self.document_uri,
            "document_digest": self.document_digest,
            "event_time": self.event_time.isoformat(),
            "effective_from": self.effective_from.isoformat(),
            "effective_to": self.effective_to.isoformat() if self.effective_to else None,
            "ingested_at": self.ingested_at.isoformat(),
            "data_classification": self.data_classification,
            "retention_class": self.retention_class,
            "lineage_trace_id": self.lineage_trace_id,
            "dedup_key": self.dedup_key,
            "schema_version": self.schema_version,
            "source_system": self.source_system,
            "source_id": self.source_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Contract:
        d = dict(data)
        d["tenant_id"] = _validate_tenant_id(d.get("tenant_id"))
        d["contract_type"] = ContractType(d["contract_type"]) if isinstance(d.get("contract_type"), str) else d.get("contract_type")
        if d.get("status"):
            d["status"] = ContractStatus(d["status"]) if isinstance(d.get("status"), str) else d.get("status")
        d["event_time"] = _validate_utc(d["event_time"], "event_time")
        d["effective_from"] = _validate_utc(d["effective_from"], "effective_from")
        if d.get("effective_to"):
            d["effective_to"] = _validate_utc(d["effective_to"], "effective_to")
        if d.get("ingested_at"):
            d["ingested_at"] = _validate_utc(d["ingested_at"], "ingested_at")
        return cls(**d)

    @classmethod
    def try_create(cls, **kwargs: Any) -> Result[Contract, CanonicalValidationError]:
        try:
            return Success(cls(**kwargs))
        except CanonicalValidationError as err:
            return Failure(err)


ContractRecord = Contract


# =============================================================================
# 8. ContractClause Entity
# =============================================================================

@dataclass(frozen=True, slots=True)
class ContractClause:
    """
    Canonical ContractClause entity (Contract Intelligence context).
    Primary Key: (tenant_id, id).
    Foreign Key: (tenant_id, contract_id) -> Contract.
    """
    tenant_id: TenantId
    id: str
    contract_id: str
    clause_number: str
    clause_type: ClauseType
    clause_text: str
    event_time: UtcDateTime
    effective_from: UtcDateTime
    sla_threshold_hours: Optional[int] = None
    penalty_per_hour_cents: Optional[int] = None
    effective_to: Optional[UtcDateTime] = None
    ingested_at: UtcDateTime = field(default_factory=UtcDateTime.now)
    data_classification: str = "CONFIDENTIAL"
    retention_class: str = "LEGAL_CONTRACT_10YR"
    lineage_trace_id: str = ""
    dedup_key: str = ""
    schema_version: str = "1.0.0"
    source_system: str = ""
    source_id: str = ""

    def __post_init__(self) -> None:
        t_id = _validate_tenant_id(self.tenant_id)
        e_id = _validate_entity_id(self.id, "ContractClause")
        c_id = _validate_entity_id(self.contract_id, "ContractClause.contract_id")
        object.__setattr__(self, "tenant_id", t_id)
        object.__setattr__(self, "id", e_id)
        object.__setattr__(self, "contract_id", c_id)

        ct = _validate_enum(self.clause_type, ClauseType, "clause_type")
        object.__setattr__(self, "clause_type", ct)

        if not isinstance(self.clause_text, str) or not self.clause_text.strip():
            raise CanonicalValidationError("clause_text cannot be empty")

        if self.sla_threshold_hours is not None:
            if not isinstance(self.sla_threshold_hours, int) or self.sla_threshold_hours < 0:
                raise CanonicalValidationError(
                    f"sla_threshold_hours must be a non-negative integer, got {self.sla_threshold_hours!r}"
                )

        if self.penalty_per_hour_cents is not None:
            if not isinstance(self.penalty_per_hour_cents, int) or self.penalty_per_hour_cents < 0:
                raise CanonicalValidationError(
                    f"penalty_per_hour_cents must be a non-negative integer, got {self.penalty_per_hour_cents!r}"
                )

        evt = _validate_utc(self.event_time, "event_time")
        eff_from = _validate_utc(self.effective_from, "effective_from")
        object.__setattr__(self, "event_time", evt)
        object.__setattr__(self, "effective_from", eff_from)

        if self.effective_to is not None:
            eff_to = _validate_utc(self.effective_to, "effective_to")
            if eff_to.value < eff_from.value:
                raise CanonicalValidationError(
                    f"effective_to ({eff_to}) cannot precede effective_from ({eff_from})"
                )
            object.__setattr__(self, "effective_to", eff_to)

        if not isinstance(self.ingested_at, UtcDateTime):
            object.__setattr__(self, "ingested_at", _validate_utc(self.ingested_at, "ingested_at"))

        if not self.dedup_key:
            object.__setattr__(
                self,
                "dedup_key",
                _compute_dedup_key(t_id.value, "ContractClause", e_id, self.source_system, self.source_id),
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id.value,
            "id": self.id,
            "contract_id": self.contract_id,
            "clause_number": self.clause_number,
            "clause_type": self.clause_type.value,
            "clause_text": self.clause_text,
            "sla_threshold_hours": self.sla_threshold_hours,
            "penalty_per_hour_cents": self.penalty_per_hour_cents,
            "event_time": self.event_time.isoformat(),
            "effective_from": self.effective_from.isoformat(),
            "effective_to": self.effective_to.isoformat() if self.effective_to else None,
            "ingested_at": self.ingested_at.isoformat(),
            "data_classification": self.data_classification,
            "retention_class": self.retention_class,
            "lineage_trace_id": self.lineage_trace_id,
            "dedup_key": self.dedup_key,
            "schema_version": self.schema_version,
            "source_system": self.source_system,
            "source_id": self.source_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ContractClause:
        d = dict(data)
        d["tenant_id"] = _validate_tenant_id(d.get("tenant_id"))
        d["clause_type"] = ClauseType(d["clause_type"]) if isinstance(d.get("clause_type"), str) else d.get("clause_type")
        d["event_time"] = _validate_utc(d["event_time"], "event_time")
        d["effective_from"] = _validate_utc(d["effective_from"], "effective_from")
        if d.get("effective_to"):
            d["effective_to"] = _validate_utc(d["effective_to"], "effective_to")
        if d.get("ingested_at"):
            d["ingested_at"] = _validate_utc(d["ingested_at"], "ingested_at")
        return cls(**d)

    @classmethod
    def try_create(cls, **kwargs: Any) -> Result[ContractClause, CanonicalValidationError]:
        try:
            return Success(cls(**kwargs))
        except CanonicalValidationError as err:
            return Failure(err)


ContractClauseRecord = ContractClause


# =============================================================================
# 9. PaymentReference Entity
# =============================================================================

@dataclass(frozen=True, slots=True)
class PaymentReference:
    """
    Canonical PaymentReference entity (Revenue Ledger context).
    Primary Key: (tenant_id, id).
    Foreign Key: (tenant_id, order_id) -> Order.
    Enforces amount_cents >= 0; zero card credentials stored (INV-SEC-001).
    """
    tenant_id: TenantId
    id: str
    order_id: str
    gateway_provider: GatewayProvider
    transaction_type: TransactionType
    payment_status: PaymentStatus
    amount_cents: int
    currency: Currency
    processed_at: UtcDateTime
    event_time: UtcDateTime
    effective_from: UtcDateTime
    gateway_error_code: Optional[str] = None
    effective_to: Optional[UtcDateTime] = None
    ingested_at: UtcDateTime = field(default_factory=UtcDateTime.now)
    data_classification: str = "CONFIDENTIAL"
    retention_class: str = "FINANCIAL_PAYMENT_7YR"
    lineage_trace_id: str = ""
    dedup_key: str = ""
    schema_version: str = "1.0.0"
    source_system: str = ""
    source_id: str = ""

    def __post_init__(self) -> None:
        t_id = _validate_tenant_id(self.tenant_id)
        e_id = _validate_entity_id(self.id, "PaymentReference")
        o_id = _validate_entity_id(self.order_id, "PaymentReference.order_id")
        object.__setattr__(self, "tenant_id", t_id)
        object.__setattr__(self, "id", e_id)
        object.__setattr__(self, "order_id", o_id)

        gp = _validate_enum(self.gateway_provider, GatewayProvider, "gateway_provider")
        tt = _validate_enum(self.transaction_type, TransactionType, "transaction_type")
        ps = _validate_enum(self.payment_status, PaymentStatus, "payment_status")
        curr = _validate_currency(self.currency)
        object.__setattr__(self, "gateway_provider", gp)
        object.__setattr__(self, "transaction_type", tt)
        object.__setattr__(self, "payment_status", ps)
        object.__setattr__(self, "currency", curr)

        if not isinstance(self.amount_cents, int) or self.amount_cents < 0:
            raise CanonicalValidationError(
                f"amount_cents must be a non-negative integer, got {self.amount_cents!r}"
            )

        proc = _validate_utc(self.processed_at, "processed_at")
        evt = _validate_utc(self.event_time, "event_time")
        eff_from = _validate_utc(self.effective_from, "effective_from")
        object.__setattr__(self, "processed_at", proc)
        object.__setattr__(self, "event_time", evt)
        object.__setattr__(self, "effective_from", eff_from)

        if self.effective_to is not None:
            eff_to = _validate_utc(self.effective_to, "effective_to")
            if eff_to.value < eff_from.value:
                raise CanonicalValidationError(
                    f"effective_to ({eff_to}) cannot precede effective_from ({eff_from})"
                )
            object.__setattr__(self, "effective_to", eff_to)

        if not isinstance(self.ingested_at, UtcDateTime):
            object.__setattr__(self, "ingested_at", _validate_utc(self.ingested_at, "ingested_at"))

        if not self.dedup_key:
            object.__setattr__(
                self,
                "dedup_key",
                _compute_dedup_key(t_id.value, "PaymentReference", e_id, self.source_system, self.source_id),
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "tenant_id": self.tenant_id.value,
            "id": self.id,
            "order_id": self.order_id,
            "gateway_provider": self.gateway_provider.value,
            "transaction_type": self.transaction_type.value,
            "payment_status": self.payment_status.value,
            "amount_cents": self.amount_cents,
            "currency": self.currency.value,
            "processed_at": self.processed_at.isoformat(),
            "event_time": self.event_time.isoformat(),
            "effective_from": self.effective_from.isoformat(),
            "gateway_error_code": self.gateway_error_code,
            "effective_to": self.effective_to.isoformat() if self.effective_to else None,
            "ingested_at": self.ingested_at.isoformat(),
            "data_classification": self.data_classification,
            "retention_class": self.retention_class,
            "lineage_trace_id": self.lineage_trace_id,
            "dedup_key": self.dedup_key,
            "schema_version": self.schema_version,
            "source_system": self.source_system,
            "source_id": self.source_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PaymentReference:
        d = dict(data)
        d["tenant_id"] = _validate_tenant_id(d.get("tenant_id"))
        d["gateway_provider"] = GatewayProvider(d["gateway_provider"]) if isinstance(d.get("gateway_provider"), str) else d.get("gateway_provider")
        d["transaction_type"] = TransactionType(d["transaction_type"]) if isinstance(d.get("transaction_type"), str) else d.get("transaction_type")
        d["payment_status"] = PaymentStatus(d["payment_status"]) if isinstance(d.get("payment_status"), str) else d.get("payment_status")
        d["currency"] = Currency.from_str(d["currency"]) if isinstance(d.get("currency"), str) else d.get("currency")
        d["processed_at"] = _validate_utc(d["processed_at"], "processed_at")
        d["event_time"] = _validate_utc(d["event_time"], "event_time")
        d["effective_from"] = _validate_utc(d["effective_from"], "effective_from")
        if d.get("effective_to"):
            d["effective_to"] = _validate_utc(d["effective_to"], "effective_to")
        if d.get("ingested_at"):
            d["ingested_at"] = _validate_utc(d["ingested_at"], "ingested_at")
        return cls(**d)

    @classmethod
    def try_create(cls, **kwargs: Any) -> Result[PaymentReference, CanonicalValidationError]:
        try:
            return Success(cls(**kwargs))
        except CanonicalValidationError as err:
            return Failure(err)


PaymentReferenceRecord = PaymentReference


__all__ = [
    "CanonicalValidationError",
    "TenantRequiredError",
    "Customer",
    "CustomerRecord",
    "Order",
    "OrderRecord",
    "OrderLine",
    "OrderLineRecord",
    "Shipment",
    "ShipmentRecord",
    "SupportTicket",
    "SupportTicketRecord",
    "MaintenanceEvent",
    "MaintenanceEventRecord",
    "Contract",
    "ContractRecord",
    "ContractClause",
    "ContractClauseRecord",
    "PaymentReference",
    "PaymentReferenceRecord",
]
