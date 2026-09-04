"""
RevPilot AI — Midwest Truck Capacity Scenario Injector (Phase 01)
Adheres to docs/03-requirements/SYNTHETIC-DATASET-SPEC.md §6 and INV-DATA-001.
"""

from __future__ import annotations
from datetime import timedelta
import random
from typing import Tuple, List, Dict, Any

from revpilot.shared.identifiers import TenantId
from revpilot.shared.temporal import UtcDateTime
from revpilot.modules.canonical.enums import (
    OrderStatus,
    CancellationReason,
    DispatchStatus,
    TicketTopic,
    TicketPriority,
    TicketStatus,
)
from revpilot.modules.canonical.models import (
    Order,
    Shipment,
    SupportTicket,
)
from revpilot.modules.benchmark.generator import GeneratedDatasetBundle
from revpilot.modules.benchmark.ground_truth import (
    GroundTruthIncident,
    ScenarioInjectionError,
)


class TruckCapacityScenarioInjector:
    """
    Scenario injector for INC-SYNTH-TRUCK-001 (Midwest Regional Carrier Disruption).
    Injects realistic shipment latency spikes and elevated cancellation rates into
    the Midwest cohort of ten_alpha while leaving control groups at baseline.
    """

    AFFECTED_TENANT = TenantId("tnt_alpha")
    CONTROL_TENANT = TenantId("tnt_beta")
    AFFECTED_FACILITY = "WH-MIDWEST-01"
    CONTROL_FACILITY = "WH-WEST-01"
    AFFECTED_CARRIER = "CARRIER_REGIONAL_LOGISTICS"
    CONTROL_CARRIER = "CARRIER_AIR_EXPRESS"

    BASELINE_CANCELLATION_RATE = 0.0180  # 1.8%
    TARGET_AFFECTED_CANCELLATION_RATE = 0.0840  # 8.4%
    TARGET_ATE_DELTA = 0.0660  # +6.60%

    def inject(
        self,
        dataset: GeneratedDatasetBundle,
        seed: int = 42,
    ) -> Tuple[GeneratedDatasetBundle, GroundTruthIncident]:
        """
        Inject the Midwest truck capacity disruption into the dataset.
        Returns:
            (Modified GeneratedDatasetBundle, Isolated GroundTruthIncident)
        """
        rng = random.Random(seed)

        start_dt = dataset.config.start_date.value
        duration_days = dataset.config.duration_days

        # 1. Determine disruption time window
        if duration_days >= 53:
            causal_start_time = UtcDateTime.from_datetime(start_dt + timedelta(days=44, hours=8))
            causal_end_time = UtcDateTime.from_datetime(start_dt + timedelta(days=51, hours=23, minutes=59, seconds=59))
        elif duration_days >= 10:
            # Scaled window for CI / development profile
            causal_start_time = UtcDateTime.from_datetime(start_dt + timedelta(days=int(duration_days * 0.45), hours=8))
            causal_end_time = UtcDateTime.from_datetime(start_dt + timedelta(days=int(duration_days * 0.75), hours=23, minutes=59, seconds=59))
        else:
            raise ScenarioInjectionError("SCENARIO_INJECTION_FAILED: Inconsistent cohort timestamps")

        # 2. Partition and assign facilities to shipments
        # Ten_alpha shipments get warehouse assignment: 60% WH-MIDWEST-01, 40% WH-WEST-01
        updated_shipments: List[Shipment] = []
        shipment_by_order_id: Dict[str, Shipment] = {}

        affected_shipment_ids: set[str] = set()
        affected_order_ids: set[str] = set()
        delayed_shipment_count = 0

        for idx, shp in enumerate(dataset.shipments):
            tenant = shp.tenant_id
            order_id = shp.order_id

            if tenant == self.AFFECTED_TENANT:
                # Assign facilities consistently
                wh_id = self.AFFECTED_FACILITY if (idx % 5 < 3) else self.CONTROL_FACILITY
                origin_reg = "US-MIDWEST" if wh_id == self.AFFECTED_FACILITY else "US-WEST"
                carr_id = self.AFFECTED_CARRIER if (idx % 2 == 0) else self.CONTROL_CARRIER

                # Check if this shipment falls within the affected causal cohort
                is_in_window = (causal_start_time.value <= shp.event_time.value <= causal_end_time.value)
                is_affected = (wh_id == self.AFFECTED_FACILITY and carr_id == self.AFFECTED_CARRIER and is_in_window)

                if is_affected:
                    affected_shipment_ids.add(shp.id)
                    affected_order_ids.add(order_id)
                    delayed_shipment_count += 1

                    # Mechanistic delay: dispatch latency rises from 12h to 84h (+72h delay)
                    disp_at = UtcDateTime.from_datetime(shp.event_time.value + timedelta(hours=84))
                    act_del = UtcDateTime.from_datetime(shp.event_time.value + timedelta(hours=156))

                    new_shp = Shipment(
                        tenant_id=shp.tenant_id,
                        id=shp.id,
                        order_id=shp.order_id,
                        tracking_number=shp.tracking_number,
                        carrier_id=carr_id,
                        carrier_name="Regional Express",
                        warehouse_id=wh_id,
                        origin_region=origin_reg,
                        destination_region=shp.destination_region,
                        dispatch_status=DispatchStatus.DELIVERED,
                        estimated_delivery_at=shp.estimated_delivery_at,
                        dispatched_at=disp_at,
                        actual_delivered_at=act_del,
                        is_delayed=True,
                        event_time=shp.event_time,
                        effective_from=shp.effective_from,
                        ingested_at=shp.ingested_at,
                    )
                else:
                    new_shp = Shipment(
                        tenant_id=shp.tenant_id,
                        id=shp.id,
                        order_id=shp.order_id,
                        tracking_number=shp.tracking_number,
                        carrier_id=carr_id,
                        carrier_name=shp.carrier_name,
                        warehouse_id=wh_id,
                        origin_region=origin_reg,
                        destination_region=shp.destination_region,
                        dispatch_status=shp.dispatch_status,
                        estimated_delivery_at=shp.estimated_delivery_at,
                        dispatched_at=shp.dispatched_at,
                        actual_delivered_at=shp.actual_delivered_at,
                        is_delayed=shp.is_delayed,
                        event_time=shp.event_time,
                        effective_from=shp.effective_from,
                        ingested_at=shp.ingested_at,
                    )
            else:
                # Control tenant (ten_beta): preserve intact
                new_shp = shp

            updated_shipments.append(new_shp)
            shipment_by_order_id[order_id] = new_shp

        # 3. Process Orders with calibrated cancellation rates
        # Separate orders into:
        # A. Affected cohort (ten_alpha Midwest + carrier regional within window) -> target 8.4% cancellations
        # B. Control cohorts (ten_beta, or unaffected ten_alpha facilities) -> target 1.8% cancellations
        affected_orders_list: List[Order] = []
        control_alpha_orders_list: List[Order] = []
        control_beta_orders_list: List[Order] = []

        for o in dataset.orders:
            if o.tenant_id == self.CONTROL_TENANT:
                control_beta_orders_list.append(o)
            elif o.id in affected_order_ids:
                affected_orders_list.append(o)
            else:
                control_alpha_orders_list.append(o)

        # Calibrate cancellation flags deterministically
        def calibrate_cohort(
            orders: List[Order],
            target_rate: float,
            cohort_rng: random.Random,
            is_affected_cohort: bool = False,
        ) -> List[Order]:
            n = len(orders)
            if n == 0:
                return []
            target_cancel_count = max(1, round(n * target_rate))
            cancel_indices = set(cohort_rng.sample(range(n), target_cancel_count))

            calibrated: List[Order] = []
            for i, order in enumerate(orders):
                should_cancel = i in cancel_indices
                if should_cancel:
                    c_reason = (
                        CancellationReason.CUSTOMER_REQUEST_DELAY
                        if is_affected_cohort
                        else CancellationReason.CUSTOMER_REQUEST_DELAY
                    )
                    c_time = UtcDateTime.from_datetime(order.event_time.value + timedelta(hours=36))
                    new_order = Order(
                        tenant_id=order.tenant_id,
                        id=order.id,
                        customer_id=order.customer_id,
                        order_number=order.order_number,
                        order_status=OrderStatus.CANCELLED,
                        currency=order.currency,
                        subtotal_cents=order.subtotal_cents,
                        tax_cents=order.tax_cents,
                        shipping_cents=order.shipping_cents,
                        total_cents=order.total_cents,
                        sla_delivery_deadline=order.sla_delivery_deadline,
                        event_time=order.event_time,
                        effective_from=order.effective_from,
                        ingested_at=order.ingested_at,
                        cancellation_reason=c_reason,
                        cancelled_at=c_time,
                    )
                else:
                    new_order = Order(
                        tenant_id=order.tenant_id,
                        id=order.id,
                        customer_id=order.customer_id,
                        order_number=order.order_number,
                        order_status=OrderStatus.DELIVERED,
                        currency=order.currency,
                        subtotal_cents=order.subtotal_cents,
                        tax_cents=order.tax_cents,
                        shipping_cents=order.shipping_cents,
                        total_cents=order.total_cents,
                        sla_delivery_deadline=order.sla_delivery_deadline,
                        event_time=order.event_time,
                        effective_from=order.effective_from,
                        ingested_at=order.ingested_at,
                        cancellation_reason=None,
                        cancelled_at=None,
                    )
                calibrated.append(new_order)
            return calibrated

        calibrated_affected = calibrate_cohort(
            affected_orders_list,
            self.TARGET_AFFECTED_CANCELLATION_RATE,
            random.Random(seed + 1),
            is_affected_cohort=True,
        )
        calibrated_alpha_ctrl = calibrate_cohort(
            control_alpha_orders_list,
            self.BASELINE_CANCELLATION_RATE,
            random.Random(seed + 2),
            is_affected_cohort=False,
        )
        calibrated_beta_ctrl = calibrate_cohort(
            control_beta_orders_list,
            self.BASELINE_CANCELLATION_RATE,
            random.Random(seed + 3),
            is_affected_cohort=False,
        )

        all_updated_orders = calibrated_affected + calibrated_alpha_ctrl + calibrated_beta_ctrl

        # 4. Calculate True Impact Metrics for GroundTruthIncident
        total_revenue_at_risk_cents = sum(o.total_cents for o in calibrated_affected if o.order_status == OrderStatus.CANCELLED)

        # 5. Elevate support ticket volume for affected cohort
        updated_tickets: List[SupportTicket] = list(dataset.support_tickets)
        tkt_idx = len(updated_tickets) + 1
        t_suffix = "alpha"

        for o in calibrated_affected:
            if o.order_status == OrderStatus.CANCELLED:
                t_time = UtcDateTime.from_datetime(o.event_time.value + timedelta(hours=16))
                ticket = SupportTicket(
                    tenant_id=self.AFFECTED_TENANT,
                    id=f"tkt_{t_suffix}_{tkt_idx:04d}",
                    customer_id=o.customer_id,
                    order_id=o.id,
                    ticket_number=f"TKT-{t_suffix.upper()}-{tkt_idx:05d}",
                    topic=TicketTopic.ORDER_STATUS_DELAY,
                    priority=TicketPriority.P2_HIGH,
                    status=TicketStatus.OPEN,
                    subject=f"Delivery inquiry for delayed package {tkt_idx}",
                    transcript_text=f"Customer inquiring regarding package transit timeline for order {o.id}.",
                    event_time=t_time,
                    effective_from=t_time,
                    ingested_at=t_time,
                )
                updated_tickets.append(ticket)
                tkt_idx += 1

        # 6. Construct Ground Truth Incident Container
        ground_truth = GroundTruthIncident(
            tenant_id=self.AFFECTED_TENANT,
            incident_id="INC-SYNTH-TRUCK-001",
            scenario_name="Midwest Regional Carrier Fleet Capacity Disruption",
            causal_start_time=causal_start_time,
            causal_end_time=causal_end_time,
            primary_root_cause="TRUCK_CAPACITY_SHORTAGE_MIDWEST",
            affected_facility_id=self.AFFECTED_FACILITY,
            affected_carrier_id=self.AFFECTED_CARRIER,
            true_ate_cancellation_rate_delta=self.TARGET_ATE_DELTA,
            true_delayed_shipment_count=delayed_shipment_count,
            true_revenue_at_risk_cents=total_revenue_at_risk_cents,
            competing_hypotheses=[
                {
                    "hypothesis_id": "HYP-001",
                    "description": "Northeast Winter Storm Event causing delivery delays",
                    "status": "DISPROVED_CONFOUNDER",
                },
                {
                    "hypothesis_id": "HYP-002",
                    "description": "Payment Gateway Timeout Outage causing checkout drops",
                    "status": "DISPROVED_ALTERNATIVE",
                },
                {
                    "hypothesis_id": "HYP-003",
                    "description": "Product Quality Defect in SKU prompting cancellations",
                    "status": "DISPROVED_ALTERNATIVE",
                },
            ],
        )

        injected_bundle = GeneratedDatasetBundle(
            customers=dataset.customers,
            orders=all_updated_orders,
            order_lines=dataset.order_lines,
            shipments=updated_shipments,
            support_tickets=updated_tickets,
            maintenance_events=dataset.maintenance_events,
            contracts=dataset.contracts,
            contract_clauses=dataset.contract_clauses,
            payment_references=dataset.payment_references,
            config=dataset.config,
        )

        return injected_bundle, ground_truth


__all__ = [
    "TruckCapacityScenarioInjector",
]
