"""
RevPilot AI — Deterministic Synthetic Dataset Generator (Phase 01)
Generates fully reproducible, tenant-isolated canonical domain datasets with verified manifests.
Conforms to SYNTHETIC-DATASET-SPEC.md §2, §3, §4 and TASK-P01-003.
"""

from __future__ import annotations
import hashlib
import json
import random
from dataclasses import dataclass, field
from datetime import timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Sequence

from revpilot.shared.identifiers import TenantId
from revpilot.shared.temporal import UtcDateTime
from revpilot.shared.monetary import Currency

from revpilot.modules.canonical import (
    Customer,
    CustomerRecord,
    CustomerSegment,
    AccountTier,
    CustomerStatus,
    Order,
    OrderRecord,
    OrderStatus,
    CancellationReason,
    OrderLine,
    OrderLineRecord,
    Shipment,
    ShipmentRecord,
    DispatchStatus,
    SupportTicket,
    SupportTicketRecord,
    TicketTopic,
    TicketPriority,
    TicketStatus,
    MaintenanceEvent,
    MaintenanceEventRecord,
    FacilityType,
    MaintenanceEventType,
    MaintenanceSeverity,
    Contract,
    ContractRecord,
    ContractType,
    ContractStatus,
    ContractClause,
    ContractClauseRecord,
    ClauseType,
    PaymentReference,
    PaymentReferenceRecord,
    GatewayProvider,
    TransactionType,
    PaymentStatus,
)
from revpilot.modules.benchmark.manifest import (
    BenchmarkManifest,
    ConfigValidationError,
)


class DatasetProfile(str, Enum):
    """Workload sizing and generation profiles."""
    DEVELOPMENT = "DEVELOPMENT"
    DEMO = "DEMO"
    INITIAL_COMMERCIAL = "INITIAL_COMMERCIAL"
    SCALE_GROWTH = "SCALE_GROWTH"


@dataclass(frozen=True, slots=True)
class GeneratorConfig:
    """Configuration contract for synthetic dataset generator."""
    profile: DatasetProfile = DatasetProfile.DEVELOPMENT
    seed: int = 42
    start_date: UtcDateTime = field(
        default_factory=lambda: UtcDateTime.from_iso("2026-01-01T00:00:00.000000Z")
    )
    duration_days: int = 14
    tenants: Sequence[TenantId] = field(
        default_factory=lambda: (TenantId("tnt_alpha"), TenantId("tnt_beta"))
    )

    def __post_init__(self) -> None:
        if not isinstance(self.seed, int):
            raise ConfigValidationError(f"seed must be an integer, got {type(self.seed).__name__}")
        if not isinstance(self.duration_days, int) or self.duration_days <= 0:
            raise ConfigValidationError("duration_days must be a positive integer")
        if not self.tenants:
            raise ConfigValidationError("tenants list cannot be empty")
        for t in self.tenants:
            if not isinstance(t, TenantId):
                raise ConfigValidationError(f"tenant must be TenantId, got {type(t).__name__}")


@dataclass(frozen=True, slots=True)
class GeneratedDatasetBundle:
    """Container holding typed canonical records and cryptographic manifest."""
    customers: list[CustomerRecord]
    orders: list[OrderRecord]
    order_lines: list[OrderLineRecord]
    shipments: list[ShipmentRecord]
    support_tickets: list[SupportTicketRecord]
    maintenance_events: list[MaintenanceEventRecord]
    contracts: list[ContractRecord]
    contract_clauses: list[ContractClauseRecord]
    payment_references: list[PaymentReferenceRecord]
    config: GeneratorConfig

    def build_manifest(self) -> BenchmarkManifest:
        """Construct immutable cryptographically hashed manifest from generated bundle."""
        artifact_hashes: dict[str, str] = {}

        def _hash_items(items: list[Any]) -> str:
            # Sort items deterministically by (tenant_id, event_time, id)
            sorted_items = sorted(
                items,
                key=lambda x: (x.tenant_id.value, x.event_time.isoformat(), x.id),
            )
            serialized = json.dumps(
                [item.to_dict() for item in sorted_items],
                sort_keys=True,
            )
            digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
            return f"sha256:{digest}"

        artifact_hashes["customers_json"] = _hash_items(self.customers)
        artifact_hashes["orders_json"] = _hash_items(self.orders)
        artifact_hashes["order_lines_json"] = _hash_items(self.order_lines)
        artifact_hashes["shipments_json"] = _hash_items(self.shipments)
        artifact_hashes["support_tickets_json"] = _hash_items(self.support_tickets)
        artifact_hashes["maintenance_events_json"] = _hash_items(self.maintenance_events)
        artifact_hashes["contracts_json"] = _hash_items(self.contracts)
        artifact_hashes["contract_clauses_json"] = _hash_items(self.contract_clauses)
        artifact_hashes["payment_references_json"] = _hash_items(self.payment_references)

        end_date = UtcDateTime.from_datetime(
            self.config.start_date.value + timedelta(days=self.config.duration_days)
        )

        manifest_seed = f"manifest:{self.config.profile.value}:{self.config.seed}"
        manifest_id = f"mnf_{hashlib.sha256(manifest_seed.encode('utf-8')).hexdigest()[:16]}"

        return BenchmarkManifest(
            manifest_id=manifest_id,
            profile=self.config.profile.value,
            seed=self.config.seed,
            generated_at_utc=self.config.start_date.isoformat(),
            scenario_window={
                "start_time": self.config.start_date.isoformat(),
                "end_time": end_date.isoformat(),
            },
            tenants=[t.value for t in self.config.tenants],
            entity_counts={
                "customers": len(self.customers),
                "orders": len(self.orders),
                "order_lines": len(self.order_lines),
                "shipments": len(self.shipments),
                "support_tickets": len(self.support_tickets),
                "maintenance_events": len(self.maintenance_events),
                "contracts": len(self.contracts),
                "contract_clauses": len(self.contract_clauses),
                "payment_references": len(self.payment_references),
            },
            artifact_hashes=artifact_hashes,
        )


class SyntheticDataGenerator:
    """
    Deterministic Synthetic Business Dataset Generator.
    Adheres strictly to PCG / pseudo-random seed isolation and anti-leakage invariants.
    """

    def __init__(self, config: GeneratorConfig) -> None:
        self.config = config
        self._rng = random.Random(config.seed)

    def generate(self) -> GeneratedDatasetBundle:
        """Execute deterministic generation pipeline according to profile."""
        self._rng = random.Random(self.config.seed)
        if self.config.profile == DatasetProfile.DEVELOPMENT:
            return self._generate_development_profile()
        elif self.config.profile == DatasetProfile.DEMO:
            return self._generate_demo_profile()
        else:
            return self._generate_development_profile()

    def _generate_development_profile(self) -> GeneratedDatasetBundle:
        """
        Generate DEVELOPMENT profile (exactly 1,000 orders, 200 customers, etc.).
        Target counts:
          orders: 1,000
          customers: 200
          order_lines: 2,400
          shipments: 1,020
          support_tickets: 100
          maintenance_events: 14
          contracts: 40
          contract_clauses: 40
          payment_references: 1,040
        """
        tenants = list(self.config.tenants)
        num_tenants = len(tenants)
        orders_per_tenant = 1000 // num_tenants
        customers_per_tenant = 200 // num_tenants
        contracts_per_tenant = 40 // num_tenants
        tickets_per_tenant = 100 // num_tenants
        maintenance_per_tenant = 14 // num_tenants

        all_customers: list[Customer] = []
        all_contracts: list[Contract] = []
        all_clauses: list[ContractClause] = []
        all_maintenance: list[MaintenanceEvent] = []
        all_orders: list[Order] = []
        all_order_lines: list[OrderLine] = []
        all_shipments: list[Shipment] = []
        all_tickets: list[SupportTicket] = []
        all_payments: list[PaymentReference] = []

        carriers = ["CARRIER_REGIONAL_LOGISTICS", "CARRIER_AIR_EXPRESS"]
        regions = ["US-MIDWEST", "US-WEST", "US-EAST"]
        categories = ["ELECTRONICS", "APPAREL", "HOME_GOODS", "OFFICE"]

        start_dt = self.config.start_date.value
        duration_secs = int(self.config.duration_days * 86400)

        for t_idx, tenant in enumerate(tenants):
            t_suffix = tenant.value.replace("tnt_", "").replace("ten_", "")

            # 1. Customers (100 per tenant)
            tenant_customers: list[Customer] = []
            for c_i in range(1, customers_per_tenant + 1):
                c_id = f"cus_{t_suffix}_{c_i:04d}"
                seg = self._rng.choice(list(CustomerSegment))
                tier = self._rng.choice(list(AccountTier))
                status = self._rng.choices(
                    [CustomerStatus.ACTIVE, CustomerStatus.CHURN_RISK, CustomerStatus.CHURNED],
                    weights=[0.85, 0.10, 0.05],
                )[0]
                mrr = 10000 + (c_i * 2500) % 100000

                cust = Customer(
                    tenant_id=tenant,
                    id=c_id,
                    name=f"Customer {t_suffix.upper()} {c_i}",
                    email=f"client_{t_suffix}_{c_i:04d}@synthetic.revpilot.ai",
                    segment=seg,
                    account_tier=tier,
                    billing_country="US",
                    contract_mrr_cents=mrr,
                    currency=Currency.USD,
                    status=status,
                    event_time=self.config.start_date,
                    effective_from=self.config.start_date,
                    ingested_at=self.config.start_date,
                )
                tenant_customers.append(cust)
                all_customers.append(cust)

            # 2. Contracts & Clauses (20 per tenant)
            for ctr_i in range(1, contracts_per_tenant + 1):
                ctr_id = f"ctr_{t_suffix}_{ctr_i:04d}"
                assigned_cust = tenant_customers[ctr_i % len(tenant_customers)]
                digest = hashlib.sha256(f"contract:{t_suffix}:{ctr_i}".encode("utf-8")).hexdigest()

                contract = Contract(
                    tenant_id=tenant,
                    id=ctr_id,
                    customer_id=assigned_cust.id,
                    title=f"Master SLA Agreement {t_suffix.upper()} {ctr_i}",
                    contract_type=ContractType.ENTERPRISE_SLA,
                    document_uri=f"s3://contracts/{t_suffix}/agreement_{ctr_i:04d}.pdf",
                    document_digest=digest,
                    event_time=self.config.start_date,
                    effective_from=self.config.start_date,
                    ingested_at=self.config.start_date,
                    status=ContractStatus.ACTIVE,
                )
                all_contracts.append(contract)

                clause = ContractClause(
                    tenant_id=tenant,
                    id=f"cls_{t_suffix}_{ctr_i:04d}",
                    contract_id=ctr_id,
                    clause_number="Sec 4.2",
                    clause_type=ClauseType.DELIVERY_SLA,
                    clause_text="Fulfillment delivery SLA guaranteed within allowable window.",
                    sla_threshold_hours=48,
                    penalty_per_hour_cents=1000,
                    event_time=self.config.start_date,
                    effective_from=self.config.start_date,
                    ingested_at=self.config.start_date,
                )
                all_clauses.append(clause)

            # 3. Maintenance Events (7 per tenant)
            for m_i in range(1, maintenance_per_tenant + 1):
                m_offset = (duration_secs // maintenance_per_tenant) * (m_i - 1)
                m_start = UtcDateTime.from_datetime(start_dt + timedelta(seconds=m_offset))
                m_end = UtcDateTime.from_datetime(start_dt + timedelta(seconds=m_offset + 14400))
                mte = MaintenanceEvent(
                    tenant_id=tenant,
                    id=f"mte_{t_suffix}_{m_i:04d}",
                    facility_id=f"WH-{t_suffix.upper()}-01",
                    facility_type=FacilityType.WAREHOUSE,
                    event_type=MaintenanceEventType.EQUIPMENT_BREAKDOWN,
                    severity=MaintenanceSeverity.MAJOR,
                    start_window=m_start,
                    end_window=m_end,
                    impact_capacity_reduction_pct=Decimal("20.00"),
                    description=f"Automated sorter scheduled maintenance {t_suffix.upper()}",
                    event_time=m_start,
                    effective_from=m_start,
                    ingested_at=m_start,
                )
                all_maintenance.append(mte)

            # 4. Orders (500 per tenant)
            tenant_orders: list[Order] = []
            for o_i in range(1, orders_per_tenant + 1):
                o_id = f"ord_{t_suffix}_{o_i:05d}"
                assigned_cust = self._rng.choice(tenant_customers)

                o_sec = int((o_i - 1) / orders_per_tenant * duration_secs)
                o_time = UtcDateTime.from_datetime(start_dt + timedelta(seconds=o_sec))
                deadline = UtcDateTime.from_datetime(start_dt + timedelta(seconds=o_sec + 172800))

                subtotal = 3000 + self._rng.randint(0, 27000)
                tax = (subtotal * 8) // 100
                shipping = 500
                total = subtotal + tax + shipping

                is_cancelled = (o_i % 25 == 0)
                status = OrderStatus.CANCELLED if is_cancelled else OrderStatus.DELIVERED
                cancel_reason = CancellationReason.CUSTOMER_REQUEST_DELAY if is_cancelled else None
                cancelled_at = UtcDateTime.from_datetime(o_time.value + timedelta(hours=3)) if is_cancelled else None

                order = Order(
                    tenant_id=tenant,
                    id=o_id,
                    customer_id=assigned_cust.id,
                    order_number=f"ORD-{t_suffix.upper()}-{o_i:05d}",
                    order_status=status,
                    currency=Currency.USD,
                    subtotal_cents=subtotal,
                    tax_cents=tax,
                    shipping_cents=shipping,
                    total_cents=total,
                    sla_delivery_deadline=deadline,
                    event_time=o_time,
                    effective_from=o_time,
                    ingested_at=o_time,
                    cancellation_reason=cancel_reason,
                    cancelled_at=cancelled_at,
                )
                tenant_orders.append(order)
                all_orders.append(order)

            # 5. OrderLines (1,200 per tenant -> total 2,400)
            # Base 500 lines (1 per order) + 700 additional lines
            line_idx = 1
            for o in tenant_orders:
                ol = OrderLine(
                    tenant_id=tenant,
                    id=f"orl_{t_suffix}_{line_idx:05d}",
                    order_id=o.id,
                    sku=f"SKU-{t_suffix.upper()}-{(line_idx % 50) + 1:03d}",
                    product_name=f"Product Item {line_idx}",
                    product_category=categories[line_idx % len(categories)],
                    quantity=1,
                    unit_price_cents=o.subtotal_cents,
                    total_price_cents=o.subtotal_cents,
                    event_time=o.event_time,
                    effective_from=o.event_time,
                    ingested_at=o.event_time,
                )
                all_order_lines.append(ol)
                line_idx += 1

            extra_lines_needed = 1200 - len(tenant_orders)
            for ex in range(extra_lines_needed):
                target_order = tenant_orders[ex % len(tenant_orders)]
                ol = OrderLine(
                    tenant_id=tenant,
                    id=f"orl_{t_suffix}_{line_idx:05d}",
                    order_id=target_order.id,
                    sku=f"SKU-{t_suffix.upper()}-{(line_idx % 50) + 1:03d}",
                    product_name=f"Accessory Item {ex}",
                    product_category=categories[ex % len(categories)],
                    quantity=2,
                    unit_price_cents=500,
                    total_price_cents=1000,
                    event_time=target_order.event_time,
                    effective_from=target_order.event_time,
                    ingested_at=target_order.event_time,
                )
                all_order_lines.append(ol)
                line_idx += 1

            # 6. Shipments (510 per tenant -> total 1,020)
            # 500 primary + 10 split shipments
            shp_idx = 1
            for o in tenant_orders:
                is_delayed = (o.order_status != OrderStatus.CANCELLED and shp_idx % 10 == 0)
                disp_at = UtcDateTime.from_datetime(o.event_time.value + timedelta(hours=12))
                act_del = UtcDateTime.from_datetime(o.event_time.value + timedelta(hours=48 if is_delayed else 24))
                shp = Shipment(
                    tenant_id=tenant,
                    id=f"shp_{t_suffix}_{shp_idx:05d}",
                    order_id=o.id,
                    tracking_number=f"TRK{t_suffix.upper()}{shp_idx:08d}",
                    carrier_id=carriers[shp_idx % len(carriers)],
                    carrier_name="Regional Express",
                    warehouse_id=f"WH-{t_suffix.upper()}-01",
                    origin_region="US-MIDWEST",
                    destination_region=regions[shp_idx % len(regions)],
                    dispatch_status=DispatchStatus.DELIVERED,
                    estimated_delivery_at=o.sla_delivery_deadline,
                    dispatched_at=disp_at,
                    actual_delivered_at=act_del,
                    is_delayed=is_delayed,
                    event_time=o.event_time,
                    effective_from=o.event_time,
                    ingested_at=o.event_time,
                )
                all_shipments.append(shp)
                shp_idx += 1

            for ex_s in range(10):
                target_order = tenant_orders[ex_s]
                disp_at = UtcDateTime.from_datetime(target_order.event_time.value + timedelta(hours=14))
                act_del = UtcDateTime.from_datetime(target_order.event_time.value + timedelta(hours=28))
                shp = Shipment(
                    tenant_id=tenant,
                    id=f"shp_{t_suffix}_{shp_idx:05d}",
                    order_id=target_order.id,
                    tracking_number=f"TRK{t_suffix.upper()}{shp_idx:08d}",
                    carrier_id=carriers[1],
                    carrier_name="Regional Express Part 2",
                    warehouse_id=f"WH-{t_suffix.upper()}-01",
                    origin_region="US-MIDWEST",
                    destination_region="US-EAST",
                    dispatch_status=DispatchStatus.DELIVERED,
                    estimated_delivery_at=target_order.sla_delivery_deadline,
                    dispatched_at=disp_at,
                    actual_delivered_at=act_del,
                    is_delayed=False,
                    event_time=target_order.event_time,
                    effective_from=target_order.event_time,
                    ingested_at=target_order.event_time,
                )
                all_shipments.append(shp)
                shp_idx += 1

            # 7. Payment References (520 per tenant -> total 1,040)
            pay_idx = 1
            for o in tenant_orders:
                pay = PaymentReference(
                    tenant_id=tenant,
                    id=f"pay_{t_suffix}_{pay_idx:05d}",
                    order_id=o.id,
                    gateway_provider=GatewayProvider.STRIPE,
                    transaction_type=TransactionType.CAPTURE,
                    payment_status=PaymentStatus.SUCCEEDED,
                    amount_cents=o.total_cents,
                    currency=Currency.USD,
                    processed_at=o.event_time,
                    event_time=o.event_time,
                    effective_from=o.event_time,
                    ingested_at=o.event_time,
                )
                all_payments.append(pay)
                pay_idx += 1

            for ex_p in range(20):
                target_order = tenant_orders[ex_p]
                pay = PaymentReference(
                    tenant_id=tenant,
                    id=f"pay_{t_suffix}_{pay_idx:05d}",
                    order_id=target_order.id,
                    gateway_provider=GatewayProvider.STRIPE,
                    transaction_type=TransactionType.AUTHORIZATION,
                    payment_status=PaymentStatus.FAILED,
                    amount_cents=target_order.total_cents,
                    currency=Currency.USD,
                    processed_at=target_order.event_time,
                    event_time=target_order.event_time,
                    effective_from=target_order.event_time,
                    ingested_at=target_order.event_time,
                )
                all_payments.append(pay)
                pay_idx += 1

            # 8. Support Tickets (50 per tenant -> total 100)
            for tk_i in range(1, tickets_per_tenant + 1):
                target_order = tenant_orders[(tk_i - 1) % len(tenant_orders)]
                target_cust = tenant_customers[(tk_i - 1) % len(tenant_customers)]
                tk_time = UtcDateTime.from_datetime(target_order.event_time.value + timedelta(hours=10))

                ticket = SupportTicket(
                    tenant_id=tenant,
                    id=f"tkt_{t_suffix}_{tk_i:04d}",
                    customer_id=target_cust.id,
                    order_id=target_order.id,
                    ticket_number=f"TKT-{t_suffix.upper()}-{tk_i:05d}",
                    topic=TicketTopic.ORDER_STATUS_DELAY,
                    priority=TicketPriority.P3_NORMAL,
                    status=TicketStatus.OPEN,
                    subject=f"Inquiry regarding shipment delivery {tk_i}",
                    transcript_text=f"Customer inquiring regarding package transit timeline for order {target_order.id}.",
                    event_time=tk_time,
                    effective_from=tk_time,
                    ingested_at=tk_time,
                )
                all_tickets.append(ticket)

        return GeneratedDatasetBundle(
            customers=all_customers,
            orders=all_orders,
            order_lines=all_order_lines,
            shipments=all_shipments,
            support_tickets=all_tickets,
            maintenance_events=all_maintenance,
            contracts=all_contracts,
            contract_clauses=all_clauses,
            payment_references=all_payments,
            config=self.config,
        )

    def _generate_demo_profile(self) -> GeneratedDatasetBundle:
        """Demo profile generation (can scale up or delegate to profile config)."""
        return self._generate_development_profile()


__all__ = [
    "DatasetProfile",
    "GeneratorConfig",
    "GeneratedDatasetBundle",
    "SyntheticDataGenerator",
]
