"""
RevPilot AI — Unit and Contract Tests for Canonical Data Models (Phase 01)
Verifies CANONICAL-DATA-MODEL.md, INV-TEN-001, INV-TEN-002, and INV-DATA-001 compliance.
AC-P01-001-01 .. AC-P01-001-04.
"""

from __future__ import annotations
import sys
from decimal import Decimal
import pytest

from revpilot.shared.identifiers import TenantId
from revpilot.shared.temporal import UtcDateTime
from revpilot.shared.monetary import Currency
from revpilot.shared.errors import ValidationError

import revpilot.modules.canonical as canonical
from revpilot.modules.canonical import (
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
    CanonicalValidationError,
    TenantRequiredError,
    Customer,
    CustomerRecord,
    Order,
    OrderRecord,
    OrderLine,
    OrderLineRecord,
    Shipment,
    ShipmentRecord,
    SupportTicket,
    SupportTicketRecord,
    MaintenanceEvent,
    MaintenanceEventRecord,
    Contract,
    ContractRecord,
    ContractClause,
    ContractClauseRecord,
    PaymentReference,
    PaymentReferenceRecord,
)


@pytest.fixture
def sample_tenant() -> TenantId:
    return TenantId("tnt_alpha123")


@pytest.fixture
def sample_now() -> UtcDateTime:
    return UtcDateTime.from_iso("2026-09-04T12:00:00.000000Z")


@pytest.fixture
def sample_future() -> UtcDateTime:
    return UtcDateTime.from_iso("2026-09-05T12:00:00.000000Z")


# =============================================================================
# Architectural & Module Boundary Tests
# =============================================================================

def test_canonical_module_exports():
    """Verify all canonical contracts and enums are exported."""
    expected = {
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
    }
    actual = set(canonical.__all__)
    assert expected.issubset(actual), f"Missing exports: {expected - actual}"


def test_canonical_module_forbidden_dependencies():
    """Verify canonical module does not depend on forbidden external frameworks or ORMs."""
    forbidden = [
        "sqlalchemy",
        "psycopg",
        "tortoise",
        "peewee",
        "django",
        "temporalio",
        "langgraph",
        "fastapi",
    ]
    for mod in forbidden:
        assert mod not in sys.modules or not any(
            mod in getattr(val, "__module__", "")
            for val in vars(canonical).values()
        ), f"Canonical module illegally imports {mod}"


# =============================================================================
# AC-P01-001-01: Mandatory Tenant Scoping (INV-TEN-001)
# =============================================================================

@pytest.mark.parametrize("invalid_tenant", [None, "", "   "])
def test_all_entities_reject_null_or_empty_tenant(invalid_tenant, sample_now, sample_future):
    """AC-P01-001-01: Every canonical entity MUST reject null or empty tenant_id."""
    # 1. Customer
    with pytest.raises(TenantRequiredError):
        Customer(
            tenant_id=invalid_tenant,
            id="cus_001",
            name="Acme Corp",
            email="ops@acme.com",
            segment=CustomerSegment.ENTERPRISE,
            account_tier=AccountTier.TIER_1_PLATINUM,
            billing_country="US",
            contract_mrr_cents=500000,
            currency=Currency.USD,
            status=CustomerStatus.ACTIVE,
            event_time=sample_now,
            effective_from=sample_now,
        )

    # 2. Order
    with pytest.raises(TenantRequiredError):
        Order(
            tenant_id=invalid_tenant,
            id="ord_001",
            customer_id="cus_001",
            order_number="ORD-1001",
            order_status=OrderStatus.PLACED,
            currency=Currency.USD,
            subtotal_cents=10000,
            tax_cents=800,
            shipping_cents=500,
            total_cents=11300,
            sla_delivery_deadline=sample_future,
            event_time=sample_now,
            effective_from=sample_now,
        )

    # 3. OrderLine
    with pytest.raises(TenantRequiredError):
        OrderLine(
            tenant_id=invalid_tenant,
            id="orl_001",
            order_id="ord_001",
            sku="SKU-ITEM-1",
            product_name="Gadget Pro",
            product_category="ELECTRONICS",
            quantity=2,
            unit_price_cents=5000,
            total_price_cents=10000,
            event_time=sample_now,
            effective_from=sample_now,
        )

    # 4. Shipment
    with pytest.raises(TenantRequiredError):
        Shipment(
            tenant_id=invalid_tenant,
            id="shp_001",
            order_id="ord_001",
            tracking_number="TRK123456",
            carrier_id="CARRIER_01",
            carrier_name="Swift Freight",
            warehouse_id="WH-MIDWEST-01",
            origin_region="US-MIDWEST",
            destination_region="US-EAST",
            dispatch_status=DispatchStatus.PENDING,
            estimated_delivery_at=sample_future,
            event_time=sample_now,
            effective_from=sample_now,
        )

    # 5. SupportTicket
    with pytest.raises(TenantRequiredError):
        SupportTicket(
            tenant_id=invalid_tenant,
            id="tkt_001",
            customer_id="cus_001",
            ticket_number="TKT-99",
            topic=TicketTopic.GENERAL_SUPPORT,
            priority=TicketPriority.P3_NORMAL,
            status=TicketStatus.OPEN,
            subject="Billing question",
            transcript_text="Customer asked about invoice",
            event_time=sample_now,
            effective_from=sample_now,
        )

    # 6. MaintenanceEvent
    with pytest.raises(TenantRequiredError):
        MaintenanceEvent(
            tenant_id=invalid_tenant,
            id="mte_001",
            facility_id="WH-MIDWEST-01",
            facility_type=FacilityType.WAREHOUSE,
            event_type=MaintenanceEventType.EQUIPMENT_BREAKDOWN,
            severity=MaintenanceSeverity.MAJOR,
            start_window=sample_now,
            impact_capacity_reduction_pct=Decimal("25.50"),
            description="Belt conveyor failure",
            event_time=sample_now,
            effective_from=sample_now,
        )

    # 7. Contract
    with pytest.raises(TenantRequiredError):
        Contract(
            tenant_id=invalid_tenant,
            id="ctr_001",
            customer_id="cus_001",
            title="Enterprise Master Agreement",
            contract_type=ContractType.ENTERPRISE_SLA,
            document_uri="s3://contracts/ctr_001.pdf",
            document_digest="a" * 64,
            event_time=sample_now,
            effective_from=sample_now,
        )

    # 8. ContractClause
    with pytest.raises(TenantRequiredError):
        ContractClause(
            tenant_id=invalid_tenant,
            id="cls_001",
            contract_id="ctr_001",
            clause_number="Sec 4.1",
            clause_type=ClauseType.DELIVERY_SLA,
            clause_text="Guaranteed fulfillment within 24h",
            event_time=sample_now,
            effective_from=sample_now,
        )

    # 9. PaymentReference
    with pytest.raises(TenantRequiredError):
        PaymentReference(
            tenant_id=invalid_tenant,
            id="pay_001",
            order_id="ord_001",
            gateway_provider=GatewayProvider.STRIPE,
            transaction_type=TransactionType.AUTHORIZATION,
            payment_status=PaymentStatus.SUCCEEDED,
            amount_cents=11300,
            currency=Currency.USD,
            processed_at=sample_now,
            event_time=sample_now,
            effective_from=sample_now,
        )


# =============================================================================
# AC-P01-001-02: Monetary Invariants
# =============================================================================

def test_order_monetary_invariant_strict(sample_tenant, sample_now, sample_future):
    """AC-P01-001-02: total_cents must strictly equal subtotal + tax + shipping."""
    # Valid order
    order = Order(
        tenant_id=sample_tenant,
        id="ord_001",
        customer_id="cus_001",
        order_number="ORD-1001",
        order_status=OrderStatus.PLACED,
        currency=Currency.USD,
        subtotal_cents=10000,
        tax_cents=800,
        shipping_cents=500,
        total_cents=11300,
        sla_delivery_deadline=sample_future,
        event_time=sample_now,
        effective_from=sample_now,
    )
    assert order.total_cents == 11300

    # Invariant breach: total_cents differs
    with pytest.raises(CanonicalValidationError) as exc:
        Order(
            tenant_id=sample_tenant,
            id="ord_001",
            customer_id="cus_001",
            order_number="ORD-1001",
            order_status=OrderStatus.PLACED,
            currency=Currency.USD,
            subtotal_cents=10000,
            tax_cents=800,
            shipping_cents=500,
            total_cents=11000,  # Should be 11300
            sla_delivery_deadline=sample_future,
            event_time=sample_now,
            effective_from=sample_now,
        )
    assert "Monetary invariant violated" in str(exc.value)


@pytest.mark.parametrize("subtotal,tax,shipping,total", [
    (-100, 0, 0, -100),
    (100, -10, 0, 90),
    (100, 10, -5, 105),
])
def test_order_rejects_negative_monetary_components(sample_tenant, sample_now, sample_future, subtotal, tax, shipping, total):
    """Negative money amounts are rejected in Order."""
    with pytest.raises(CanonicalValidationError):
        Order(
            tenant_id=sample_tenant,
            id="ord_001",
            customer_id="cus_001",
            order_number="ORD-1001",
            order_status=OrderStatus.PLACED,
            currency=Currency.USD,
            subtotal_cents=subtotal,
            tax_cents=tax,
            shipping_cents=shipping,
            total_cents=total,
            sla_delivery_deadline=sample_future,
            event_time=sample_now,
            effective_from=sample_now,
        )


def test_order_line_monetary_invariants(sample_tenant, sample_now):
    """OrderLine enforces quantity > 0, unit_price >= 0, and total == quantity * unit_price."""
    # Valid
    line = OrderLine(
        tenant_id=sample_tenant,
        id="orl_001",
        order_id="ord_001",
        sku="SKU-1",
        product_name="Item",
        product_category="GENERAL",
        quantity=3,
        unit_price_cents=1500,
        total_price_cents=4500,
        event_time=sample_now,
        effective_from=sample_now,
    )
    assert line.total_price_cents == 4500

    # Quantity zero
    with pytest.raises(CanonicalValidationError):
        OrderLine(
            tenant_id=sample_tenant,
            id="orl_001",
            order_id="ord_001",
            sku="SKU-1",
            product_name="Item",
            product_category="GENERAL",
            quantity=0,
            unit_price_cents=1500,
            total_price_cents=0,
            event_time=sample_now,
            effective_from=sample_now,
        )

    # Quantity negative
    with pytest.raises(CanonicalValidationError):
        OrderLine(
            tenant_id=sample_tenant,
            id="orl_001",
            order_id="ord_001",
            sku="SKU-1",
            product_name="Item",
            product_category="GENERAL",
            quantity=-1,
            unit_price_cents=1500,
            total_price_cents=-1500,
            event_time=sample_now,
            effective_from=sample_now,
        )

    # Total mismatch
    with pytest.raises(CanonicalValidationError):
        OrderLine(
            tenant_id=sample_tenant,
            id="orl_001",
            order_id="ord_001",
            sku="SKU-1",
            product_name="Item",
            product_category="GENERAL",
            quantity=3,
            unit_price_cents=1500,
            total_price_cents=4000,
            event_time=sample_now,
            effective_from=sample_now,
        )


def test_customer_rejects_negative_mrr(sample_tenant, sample_now):
    """Customer rejects contract_mrr_cents < 0."""
    with pytest.raises(CanonicalValidationError):
        Customer(
            tenant_id=sample_tenant,
            id="cus_001",
            name="Acme Corp",
            email="ops@acme.com",
            segment=CustomerSegment.SMB,
            account_tier=AccountTier.TIER_3_STANDARD,
            billing_country="US",
            contract_mrr_cents=-500,
            currency=Currency.USD,
            status=CustomerStatus.ACTIVE,
            event_time=sample_now,
            effective_from=sample_now,
        )


def test_payment_reference_rejects_negative_amount(sample_tenant, sample_now):
    """PaymentReference rejects amount_cents < 0."""
    with pytest.raises(CanonicalValidationError):
        PaymentReference(
            tenant_id=sample_tenant,
            id="pay_001",
            order_id="ord_001",
            gateway_provider=GatewayProvider.STRIPE,
            transaction_type=TransactionType.AUTHORIZATION,
            payment_status=PaymentStatus.SUCCEEDED,
            amount_cents=-100,
            currency=Currency.USD,
            processed_at=sample_now,
            event_time=sample_now,
            effective_from=sample_now,
        )


# =============================================================================
# AC-P01-001-03: Enum Validation & Rejection
# =============================================================================

def test_enums_reject_unregistered_strings(sample_tenant, sample_now, sample_future):
    """AC-P01-001-03: Enums reject unregistered string values with CanonicalValidationError."""
    # Customer invalid segment
    with pytest.raises(CanonicalValidationError):
        Customer(
            tenant_id=sample_tenant,
            id="cus_001",
            name="Acme",
            email="acme@corp.com",
            segment="NON_EXISTENT_SEGMENT",
            account_tier=AccountTier.TIER_1_PLATINUM,
            billing_country="US",
            contract_mrr_cents=1000,
            currency=Currency.USD,
            status=CustomerStatus.ACTIVE,
            event_time=sample_now,
            effective_from=sample_now,
        )

    # Order invalid status
    with pytest.raises(CanonicalValidationError):
        Order(
            tenant_id=sample_tenant,
            id="ord_001",
            customer_id="cus_001",
            order_number="ORD-01",
            order_status="UNKNOWN_STATUS",
            currency=Currency.USD,
            subtotal_cents=100,
            tax_cents=0,
            shipping_cents=0,
            total_cents=100,
            sla_delivery_deadline=sample_future,
            event_time=sample_now,
            effective_from=sample_now,
        )

    # Shipment invalid dispatch status
    with pytest.raises(CanonicalValidationError):
        Shipment(
            tenant_id=sample_tenant,
            id="shp_001",
            order_id="ord_001",
            tracking_number="TRK1",
            carrier_id="C1",
            carrier_name="Carrier",
            warehouse_id="WH1",
            origin_region="US-MIDWEST",
            destination_region="US-EAST",
            dispatch_status="TELEPORTED",
            estimated_delivery_at=sample_future,
            event_time=sample_now,
            effective_from=sample_now,
        )

    # Support ticket invalid priority
    with pytest.raises(CanonicalValidationError):
        SupportTicket(
            tenant_id=sample_tenant,
            id="tkt_001",
            customer_id="cus_001",
            ticket_number="T1",
            topic=TicketTopic.GENERAL_SUPPORT,
            priority="CRITICAL_HYPER_URGENT",
            status=TicketStatus.OPEN,
            subject="Sub",
            transcript_text="Txt",
            event_time=sample_now,
            effective_from=sample_now,
        )

    # Maintenance event invalid severity
    with pytest.raises(CanonicalValidationError):
        MaintenanceEvent(
            tenant_id=sample_tenant,
            id="mte_001",
            facility_id="WH1",
            facility_type=FacilityType.WAREHOUSE,
            event_type=MaintenanceEventType.WEATHER_CLOSURE,
            severity="APOCALYPTIC",
            start_window=sample_now,
            impact_capacity_reduction_pct=Decimal("50"),
            description="Snow",
            event_time=sample_now,
            effective_from=sample_now,
        )


# =============================================================================
# Temporal Disambiguation & Invariants (INV-DATA-001)
# =============================================================================

def test_effective_to_preceding_effective_from_rejected(sample_tenant, sample_now, sample_future):
    """effective_to < effective_from is rejected across entities."""
    earlier = UtcDateTime.from_iso("2026-09-03T12:00:00.000000Z")
    with pytest.raises(CanonicalValidationError) as exc:
        Customer(
            tenant_id=sample_tenant,
            id="cus_001",
            name="Acme",
            email="acme@corp.com",
            segment=CustomerSegment.SMB,
            account_tier=AccountTier.TIER_3_STANDARD,
            billing_country="US",
            contract_mrr_cents=1000,
            currency=Currency.USD,
            status=CustomerStatus.ACTIVE,
            event_time=sample_now,
            effective_from=sample_now,
            effective_to=earlier,
        )
    assert "cannot precede effective_from" in str(exc.value)


def test_shipment_actual_delivered_preceding_dispatched_rejected(sample_tenant, sample_now, sample_future):
    """Shipment: actual_delivered_at < dispatched_at is rejected."""
    dispatched = sample_future
    delivered_earlier = sample_now
    with pytest.raises(CanonicalValidationError):
        Shipment(
            tenant_id=sample_tenant,
            id="shp_001",
            order_id="ord_001",
            tracking_number="TRK1",
            carrier_id="C1",
            carrier_name="Carrier",
            warehouse_id="WH1",
            origin_region="US-MIDWEST",
            destination_region="US-EAST",
            dispatch_status=DispatchStatus.DELIVERED,
            estimated_delivery_at=sample_future,
            dispatched_at=dispatched,
            actual_delivered_at=delivered_earlier,
            event_time=sample_now,
            effective_from=sample_now,
        )


def test_support_ticket_resolved_preceding_event_rejected(sample_tenant, sample_now, sample_future):
    """SupportTicket: resolved_at < event_time is rejected."""
    earlier = UtcDateTime.from_iso("2026-09-03T12:00:00.000000Z")
    with pytest.raises(CanonicalValidationError):
        SupportTicket(
            tenant_id=sample_tenant,
            id="tkt_001",
            customer_id="cus_001",
            ticket_number="T1",
            topic=TicketTopic.GENERAL_SUPPORT,
            priority=TicketPriority.P3_NORMAL,
            status=TicketStatus.RESOLVED,
            subject="Sub",
            transcript_text="Txt",
            resolved_at=earlier,
            event_time=sample_now,
            effective_from=sample_now,
        )


def test_maintenance_event_end_preceding_start_rejected(sample_tenant, sample_now):
    """MaintenanceEvent: end_window < start_window is rejected."""
    earlier = UtcDateTime.from_iso("2026-09-03T12:00:00.000000Z")
    with pytest.raises(CanonicalValidationError):
        MaintenanceEvent(
            tenant_id=sample_tenant,
            id="mte_001",
            facility_id="WH1",
            facility_type=FacilityType.WAREHOUSE,
            event_type=MaintenanceEventType.EQUIPMENT_BREAKDOWN,
            severity=MaintenanceSeverity.MINOR,
            start_window=sample_now,
            end_window=earlier,
            impact_capacity_reduction_pct=Decimal("10.0"),
            description="Conveyor check",
            event_time=sample_now,
            effective_from=sample_now,
        )


# =============================================================================
# Specific Quality Rules & Bounds
# =============================================================================

def test_customer_email_and_country_validation(sample_tenant, sample_now):
    """Customer validates RFC email and 2-letter ISO country code."""
    # Invalid email
    with pytest.raises(CanonicalValidationError) as exc:
        Customer(
            tenant_id=sample_tenant,
            id="cus_001",
            name="Acme",
            email="not-an-email",
            segment=CustomerSegment.SMB,
            account_tier=AccountTier.TIER_3_STANDARD,
            billing_country="US",
            contract_mrr_cents=1000,
            currency=Currency.USD,
            status=CustomerStatus.ACTIVE,
            event_time=sample_now,
            effective_from=sample_now,
        )
    assert "Invalid customer email" in str(exc.value)

    # Invalid country code (3 chars instead of 2)
    with pytest.raises(CanonicalValidationError) as exc:
        Customer(
            tenant_id=sample_tenant,
            id="cus_001",
            name="Acme",
            email="valid@email.com",
            segment=CustomerSegment.SMB,
            account_tier=AccountTier.TIER_3_STANDARD,
            billing_country="USA",
            contract_mrr_cents=1000,
            currency=Currency.USD,
            status=CustomerStatus.ACTIVE,
            event_time=sample_now,
            effective_from=sample_now,
        )
    assert "billing_country" in str(exc.value)


def test_maintenance_reduction_percentage_bounds(sample_tenant, sample_now):
    """MaintenanceEvent capacity reduction must be 0.00 to 100.00."""
    # > 100%
    with pytest.raises(CanonicalValidationError):
        MaintenanceEvent(
            tenant_id=sample_tenant,
            id="mte_001",
            facility_id="WH1",
            facility_type=FacilityType.WAREHOUSE,
            event_type=MaintenanceEventType.EQUIPMENT_BREAKDOWN,
            severity=MaintenanceSeverity.CRITICAL,
            start_window=sample_now,
            impact_capacity_reduction_pct=Decimal("105.00"),
            description="Catastrophic failure",
            event_time=sample_now,
            effective_from=sample_now,
        )

    # < 0%
    with pytest.raises(CanonicalValidationError):
        MaintenanceEvent(
            tenant_id=sample_tenant,
            id="mte_001",
            facility_id="WH1",
            facility_type=FacilityType.WAREHOUSE,
            event_type=MaintenanceEventType.EQUIPMENT_BREAKDOWN,
            severity=MaintenanceSeverity.MINOR,
            start_window=sample_now,
            impact_capacity_reduction_pct=Decimal("-5.00"),
            description="Negative reduction",
            event_time=sample_now,
            effective_from=sample_now,
        )


def test_contract_document_digest_hex64(sample_tenant, sample_now):
    """Contract requires 64-char hex digest."""
    # 63 chars (too short)
    with pytest.raises(CanonicalValidationError):
        Contract(
            tenant_id=sample_tenant,
            id="ctr_001",
            customer_id="cus_001",
            title="Agreement",
            contract_type=ContractType.ENTERPRISE_SLA,
            document_uri="s3://contracts/1.pdf",
            document_digest="a" * 63,
            event_time=sample_now,
            effective_from=sample_now,
        )

    # Non-hex characters
    with pytest.raises(CanonicalValidationError):
        Contract(
            tenant_id=sample_tenant,
            id="ctr_001",
            customer_id="cus_001",
            title="Agreement",
            contract_type=ContractType.ENTERPRISE_SLA,
            document_uri="s3://contracts/1.pdf",
            document_digest="z" * 64,
            event_time=sample_now,
            effective_from=sample_now,
        )


# =============================================================================
# Serialization / Deserialization Round-Trip Tests
# =============================================================================

def test_all_entities_serialization_round_trip(sample_tenant, sample_now, sample_future):
    """All 9 entities correctly serialize to dict and reconstruct identically."""
    # 1. Customer
    c = Customer(
        tenant_id=sample_tenant,
        id="cus_001",
        name="Acme Corp",
        email="ops@acme.com",
        segment=CustomerSegment.ENTERPRISE,
        account_tier=AccountTier.TIER_1_PLATINUM,
        billing_country="US",
        contract_mrr_cents=500000,
        currency=Currency.USD,
        status=CustomerStatus.ACTIVE,
        event_time=sample_now,
        effective_from=sample_now,
    )
    c_dict = c.to_dict()
    assert c_dict["tenant_id"] == sample_tenant.value
    assert c_dict["segment"] == "ENTERPRISE"
    assert c_dict["currency"] == "USD"
    c_reconstructed = Customer.from_dict(c_dict)
    assert c_reconstructed == c

    # 2. Order
    o = Order(
        tenant_id=sample_tenant,
        id="ord_001",
        customer_id="cus_001",
        order_number="ORD-1001",
        order_status=OrderStatus.PLACED,
        currency=Currency.USD,
        subtotal_cents=10000,
        tax_cents=800,
        shipping_cents=500,
        total_cents=11300,
        sla_delivery_deadline=sample_future,
        event_time=sample_now,
        effective_from=sample_now,
    )
    o_dict = o.to_dict()
    assert o_dict["total_cents"] == 11300
    o_reconstructed = Order.from_dict(o_dict)
    assert o_reconstructed == o

    # 3. OrderLine
    ol = OrderLine(
        tenant_id=sample_tenant,
        id="orl_001",
        order_id="ord_001",
        sku="SKU-1",
        product_name="Gadget",
        product_category="TECH",
        quantity=2,
        unit_price_cents=5000,
        total_price_cents=10000,
        event_time=sample_now,
        effective_from=sample_now,
    )
    ol_dict = ol.to_dict()
    ol_reconstructed = OrderLine.from_dict(ol_dict)
    assert ol_reconstructed == ol

    # 4. Shipment
    s = Shipment(
        tenant_id=sample_tenant,
        id="shp_001",
        order_id="ord_001",
        tracking_number="TRK100",
        carrier_id="CAR_01",
        carrier_name="Swift Carrier",
        warehouse_id="WH_01",
        origin_region="US-MIDWEST",
        destination_region="US-EAST",
        dispatch_status=DispatchStatus.IN_TRANSIT,
        estimated_delivery_at=sample_future,
        event_time=sample_now,
        effective_from=sample_now,
    )
    s_dict = s.to_dict()
    s_reconstructed = Shipment.from_dict(s_dict)
    assert s_reconstructed == s

    # 5. SupportTicket
    st = SupportTicket(
        tenant_id=sample_tenant,
        id="tkt_001",
        customer_id="cus_001",
        ticket_number="TKT-001",
        topic=TicketTopic.ORDER_STATUS_DELAY,
        priority=TicketPriority.P2_HIGH,
        status=TicketStatus.OPEN,
        subject="Where is my shipment?",
        transcript_text="Customer reached out about delay",
        event_time=sample_now,
        effective_from=sample_now,
    )
    st_dict = st.to_dict()
    st_reconstructed = SupportTicket.from_dict(st_dict)
    assert st_reconstructed == st

    # 6. MaintenanceEvent
    me = MaintenanceEvent(
        tenant_id=sample_tenant,
        id="mte_001",
        facility_id="WH_01",
        facility_type=FacilityType.WAREHOUSE,
        event_type=MaintenanceEventType.EQUIPMENT_BREAKDOWN,
        severity=MaintenanceSeverity.MAJOR,
        start_window=sample_now,
        impact_capacity_reduction_pct=Decimal("35.00"),
        description="Conveyor malfunction",
        event_time=sample_now,
        effective_from=sample_now,
    )
    me_dict = me.to_dict()
    assert me_dict["impact_capacity_reduction_pct"] == 35.0
    me_reconstructed = MaintenanceEvent.from_dict(me_dict)
    assert me_reconstructed == me

    # 7. Contract
    ctr = Contract(
        tenant_id=sample_tenant,
        id="ctr_001",
        customer_id="cus_001",
        title="Service Level Agreement 2026",
        contract_type=ContractType.ENTERPRISE_SLA,
        document_uri="s3://contracts/sla.pdf",
        document_digest="e" * 64,
        event_time=sample_now,
        effective_from=sample_now,
    )
    ctr_dict = ctr.to_dict()
    ctr_reconstructed = Contract.from_dict(ctr_dict)
    assert ctr_reconstructed == ctr

    # 8. ContractClause
    cl = ContractClause(
        tenant_id=sample_tenant,
        id="cls_001",
        contract_id="ctr_001",
        clause_number="4.2",
        clause_type=ClauseType.PENALTY_CREDIT,
        clause_text="Credit 5% per day delayed",
        sla_threshold_hours=24,
        penalty_per_hour_cents=1000,
        event_time=sample_now,
        effective_from=sample_now,
    )
    cl_dict = cl.to_dict()
    cl_reconstructed = ContractClause.from_dict(cl_dict)
    assert cl_reconstructed == cl

    # 9. PaymentReference
    pr = PaymentReference(
        tenant_id=sample_tenant,
        id="pay_001",
        order_id="ord_001",
        gateway_provider=GatewayProvider.STRIPE,
        transaction_type=TransactionType.CAPTURE,
        payment_status=PaymentStatus.SUCCEEDED,
        amount_cents=11300,
        currency=Currency.USD,
        processed_at=sample_now,
        event_time=sample_now,
        effective_from=sample_now,
    )
    pr_dict = pr.to_dict()
    pr_reconstructed = PaymentReference.from_dict(pr_dict)
    assert pr_reconstructed == pr


# =============================================================================
# Functional Result Constructor Tests
# =============================================================================

def test_try_create_returns_success_and_failure(sample_tenant, sample_now, sample_future):
    """try_create returns Result.is_success or Result.is_failure without unhandled exceptions."""
    # Valid
    res_ok = Order.try_create(
        tenant_id=sample_tenant,
        id="ord_001",
        customer_id="cus_001",
        order_number="ORD-1",
        order_status=OrderStatus.PLACED,
        currency=Currency.USD,
        subtotal_cents=100,
        tax_cents=10,
        shipping_cents=5,
        total_cents=115,
        sla_delivery_deadline=sample_future,
        event_time=sample_now,
        effective_from=sample_now,
    )
    assert res_ok.is_success
    assert res_ok.unwrap().id == "ord_001"

    # Invalid: monetary mismatch
    res_err = Order.try_create(
        tenant_id=sample_tenant,
        id="ord_001",
        customer_id="cus_001",
        order_number="ORD-1",
        order_status=OrderStatus.PLACED,
        currency=Currency.USD,
        subtotal_cents=100,
        tax_cents=10,
        shipping_cents=5,
        total_cents=999,  # Mismatch
        sla_delivery_deadline=sample_future,
        event_time=sample_now,
        effective_from=sample_now,
    )
    assert res_err.is_failure
    assert isinstance(res_err.unwrap_error(), CanonicalValidationError)


# =============================================================================
# Aliases and Record Type Equivalences
# =============================================================================

def test_entity_record_aliases():
    """Verify EntityRecord aliases point to exact Entity classes."""
    assert CustomerRecord is Customer
    assert OrderRecord is Order
    assert OrderLineRecord is OrderLine
    assert ShipmentRecord is Shipment
    assert SupportTicketRecord is SupportTicket
    assert MaintenanceEventRecord is MaintenanceEvent
    assert ContractRecord is Contract
    assert ContractClauseRecord is ContractClause
    assert PaymentReferenceRecord is PaymentReference
    assert ShipmentStatus is DispatchStatus
    assert TicketSeverity is TicketPriority
    assert MaintenanceType is MaintenanceEventType
    assert CurrencyCode is Currency
