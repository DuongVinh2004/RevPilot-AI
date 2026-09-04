"""
RevPilot AI — Canonical Domain Enums (Phase 01)
Authoritative enumeration types for canonical business domain entities.
Conforms to CANONICAL-DATA-MODEL.md §3, §4 and TASK-P01-001.
"""

from __future__ import annotations
from enum import Enum
from revpilot.shared.monetary import Currency


class CustomerSegment(str, Enum):
    """Customer market segmentation."""
    ENTERPRISE = "ENTERPRISE"
    MID_MARKET = "MID_MARKET"
    SMB = "SMB"
    CONSUMER = "CONSUMER"


class AccountTier(str, Enum):
    """Customer SLA/support account tier."""
    TIER_1_PLATINUM = "TIER_1_PLATINUM"
    TIER_2_GOLD = "TIER_2_GOLD"
    TIER_3_STANDARD = "TIER_3_STANDARD"


class CustomerStatus(str, Enum):
    """Customer account lifecycle state."""
    ACTIVE = "ACTIVE"
    CHURN_RISK = "CHURN_RISK"
    CHURNED = "CHURNED"
    SUSPENDED = "SUSPENDED"


class OrderStatus(str, Enum):
    """E-commerce order fulfillment state."""
    PLACED = "PLACED"
    PROCESSING = "PROCESSING"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"
    RETURNED = "RETURNED"


class CancellationReason(str, Enum):
    """Root cause category for cancelled orders."""
    CUSTOMER_REQUEST_DELAY = "CUSTOMER_REQUEST_DELAY"
    OUT_OF_STOCK = "OUT_OF_STOCK"
    PAYMENT_FAILURE = "PAYMENT_FAILURE"
    FRAUD_SUSPECTED = "FRAUD_SUSPECTED"
    OTHER = "OTHER"


class DispatchStatus(str, Enum):
    """Logistics shipment dispatch and tracking status."""
    PENDING = "PENDING"
    DISPATCHED = "DISPATCHED"
    IN_TRANSIT = "IN_TRANSIT"
    DELIVERED = "DELIVERED"
    DELAYED = "DELAYED"
    LOST = "LOST"


# Alias for DispatchStatus
ShipmentStatus = DispatchStatus


class DelayReason(str, Enum):
    """Root cause reason for delivery delay."""
    FLEET_CAPACITY_SHORTAGE = "FLEET_CAPACITY_SHORTAGE"
    WEATHER_DISRUPTION = "WEATHER_DISRUPTION"
    MECHANICAL_FAILURE = "MECHANICAL_FAILURE"
    CUSTOMS_HOLD = "CUSTOMS_HOLD"
    NONE = "NONE"


class TicketTopic(str, Enum):
    """Service desk ticket categorization topic."""
    ORDER_STATUS_DELAY = "ORDER_STATUS_DELAY"
    CANCELLATION_INQUIRY = "CANCELLATION_INQUIRY"
    PAYMENT_ISSUE = "PAYMENT_ISSUE"
    DAMAGED_ITEM = "DAMAGED_ITEM"
    GENERAL_SUPPORT = "GENERAL_SUPPORT"


class TicketPriority(str, Enum):
    """Support ticket response priority."""
    P1_URGENT = "P1_URGENT"
    P2_HIGH = "P2_HIGH"
    P3_NORMAL = "P3_NORMAL"
    P4_LOW = "P4_LOW"


# Alias for TicketPriority
TicketSeverity = TicketPriority


class TicketStatus(str, Enum):
    """Support ticket workflow lifecycle status."""
    OPEN = "OPEN"
    PENDING_CUSTOMER = "PENDING_CUSTOMER"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class FacilityType(str, Enum):
    """Fulfillment infrastructure asset type."""
    WAREHOUSE = "WAREHOUSE"
    FLEET_DEPOT = "FLEET_DEPOT"
    SORTATION_HUB = "SORTATION_HUB"


class MaintenanceEventType(str, Enum):
    """Operational incident or disruption type."""
    CARRIER_CAPACITY_SHORTAGE = "CARRIER_CAPACITY_SHORTAGE"
    EQUIPMENT_BREAKDOWN = "EQUIPMENT_BREAKDOWN"
    SCHEDULED_MAINTENANCE = "SCHEDULED_MAINTENANCE"
    WEATHER_CLOSURE = "WEATHER_CLOSURE"


# Alias for MaintenanceEventType
MaintenanceType = MaintenanceEventType


class MaintenanceSeverity(str, Enum):
    """Operational disruption severity."""
    CRITICAL = "CRITICAL"
    MAJOR = "MAJOR"
    MINOR = "MINOR"
    INFORMATIONAL = "INFORMATIONAL"


class ContractType(str, Enum):
    """Legal agreement contract category."""
    ENTERPRISE_SLA = "ENTERPRISE_SLA"
    STANDARD_TERMS = "STANDARD_TERMS"
    SUPPLIER_AGREEMENT = "SUPPLIER_AGREEMENT"


class ContractStatus(str, Enum):
    """Legal agreement lifecycle status."""
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    TERMINATED = "TERMINATED"


class ClauseType(str, Enum):
    """Contract clause legal provision classification."""
    DELIVERY_SLA = "DELIVERY_SLA"
    CANCELLATION_POLICY = "CANCELLATION_POLICY"
    PENALTY_CREDIT = "PENALTY_CREDIT"
    FORCE_MAJEURE = "FORCE_MAJEURE"


class GatewayProvider(str, Enum):
    """Payment processing gateway provider."""
    STRIPE = "STRIPE"
    ADYEN = "ADYEN"
    SYNTHETIC_BANK = "SYNTHETIC_BANK"


class TransactionType(str, Enum):
    """Payment ledger transaction classification."""
    AUTHORIZATION = "AUTHORIZATION"
    CAPTURE = "CAPTURE"
    REFUND = "REFUND"
    CHARGEBACK = "CHARGEBACK"


class PaymentStatus(str, Enum):
    """Payment transaction settlement status."""
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    PENDING = "PENDING"
    DISPUTED = "DISPUTED"


class DataClassification(str, Enum):
    """Data privacy and security governance classification."""
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    RESTRICTED_PII = "RESTRICTED_PII"


# Re-export Currency as CurrencyCode for spec compatibility
CurrencyCode = Currency

__all__ = [
    "CustomerSegment",
    "AccountTier",
    "CustomerStatus",
    "OrderStatus",
    "CancellationReason",
    "DispatchStatus",
    "ShipmentStatus",
    "DelayReason",
    "TicketTopic",
    "TicketPriority",
    "TicketSeverity",
    "TicketStatus",
    "FacilityType",
    "MaintenanceEventType",
    "MaintenanceType",
    "MaintenanceSeverity",
    "ContractType",
    "ContractStatus",
    "ClauseType",
    "GatewayProvider",
    "TransactionType",
    "PaymentStatus",
    "DataClassification",
    "CurrencyCode",
    "Currency",
]
