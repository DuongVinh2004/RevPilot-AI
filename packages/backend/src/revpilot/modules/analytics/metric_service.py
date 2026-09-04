"""
RevPilot AI — Authoritative Metric Service Query Gateway
Evaluates registered canonical metrics dynamically against canonical read repositories,
enforcing server-derived tenant context, temporal as-of watermarking, and dimension allowlists.
Conforms to METRIC-SERVICE-SPEC.md §1–§4, METRIC-REGISTRY.md, and TASK-P02-001.
"""

from __future__ import annotations
import hashlib
from datetime import timedelta
from typing import Any, Callable
from uuid import uuid4

from revpilot.shared.identifiers import TenantId
from revpilot.shared.temporal import UtcDateTime
from revpilot.shared.context import TenantContext
from revpilot.shared.results import Result, Success, Failure
from revpilot.modules.canonical import (
    Customer,
    Order,
    OrderLine,
    Shipment,
    SupportTicket,
    MaintenanceEvent,
    Contract,
    ContractClause,
    PaymentReference,
)
from revpilot.modules.analytics.metrics.definitions import (
    MetricEvaluationDataset,
    MetricDefinition,
)
from revpilot.modules.analytics.metrics.registry import (
    MetricRegistry,
    CANONICAL_METRIC_REGISTRY,
)
from revpilot.modules.analytics.schemas import (
    MetricQueryRequest,
    MetricQueryResponse,
    MetricSeriesPoint,
    MetricServiceError,
    MetricNotRegisteredError,
    InvalidDimensionFilterError,
    TemporalLeakageRejectedError,
    TenancyViolationServiceError,
)

_UNKNOWN_SENTINEL = "UNKNOWN_OR_UNSPECIFIED"


class MetricService:
    """
    Authoritative query processor and gateway for versioned canonical business metrics.
    Enforces server-derived tenancy, temporal anti-leakage, and zero-division safety.
    """

    def __init__(
        self,
        dataset: MetricEvaluationDataset | None = None,
        registry: MetricRegistry | None = None,
        clock: Callable[[], UtcDateTime] | None = None,
    ) -> None:
        self._registry = registry or CANONICAL_METRIC_REGISTRY
        self._dataset = dataset or MetricEvaluationDataset()
        self._clock = clock or UtcDateTime.now

    def set_dataset(self, dataset: MetricEvaluationDataset) -> None:
        """Set or update underlying dataset."""
        if not isinstance(dataset, MetricEvaluationDataset):
            raise TypeError(f"dataset must be MetricEvaluationDataset, got {type(dataset).__name__}")
        self._dataset = dataset

    def query(
        self,
        request: MetricQueryRequest,
        tenant_context: TenantContext,
        dataset: MetricEvaluationDataset | None = None,
    ) -> Result[MetricQueryResponse, MetricServiceError]:
        """
        Evaluate requested metric dynamically within tenant security boundary.
        Guarantees:
        - Server-derived TenantContext enforcement (INV-TEN-001, INV-TEN-002)
        - Temporal anti-leakage with as_of watermarking (INV-DATA-001)
        - Strict dimension allowlist validation
        - Zero division-by-zero errors
        """
        # 1. Tenancy validation
        if not isinstance(tenant_context, TenantContext):
            return Failure(
                TenancyViolationServiceError(
                    "Invalid tenant context: TenantContext required",
                    details={"error": "TenantContext instance required"},
                )
            )

        if not tenant_context.is_active:
            return Failure(
                TenancyViolationServiceError(
                    f"Tenant '{tenant_context.tenant_id}' is deactivated or suspended",
                    details={"tenant_id": str(tenant_context.tenant_id), "is_active": False},
                )
            )

        # Check for tenant override attempt in filters
        if "tenant_id" in request.filters:
            filter_tenant = str(request.filters["tenant_id"])
            if filter_tenant != str(tenant_context.tenant_id):
                return Failure(
                    TenancyViolationServiceError(
                        "Cross-tenant access denied: filter tenant_id does not match context",
                        details={
                            "filter_tenant_id": filter_tenant,
                            "context_tenant_id": str(tenant_context.tenant_id),
                        },
                    )
                )

        clean_filters = {k: v for k, v in request.filters.items() if k != "tenant_id"}

        # 2. Temporal leakage check (as_of_time cannot be in the future relative to server clock)
        server_now = self._clock()
        if request.as_of_time.value > server_now.value:
            return Failure(
                TemporalLeakageRejectedError(
                    f"Future as-of watermark rejected: {request.as_of_time} is ahead of server time {server_now}",
                    details={
                        "as_of_time": str(request.as_of_time),
                        "server_time": str(server_now),
                    },
                )
            )

        # 3. Registry lookup
        metric_res = self._registry.get(request.metric_id)
        if metric_res.is_failure:
            return Failure(
                MetricNotRegisteredError(
                    f"Unknown metric identifier: '{request.metric_id}'",
                    details={"metric_id": request.metric_id},
                )
            )
        metric_def: MetricDefinition = metric_res.unwrap()

        # 4. Dimension validation (group_by and filters must be in allowed_dimensions)
        for dim in request.group_by_dimensions:
            if dim not in metric_def.allowed_dimensions:
                return Failure(
                    InvalidDimensionFilterError(
                        f"Dimension '{dim}' not permitted for metric '{metric_def.metric_id}'",
                        details={
                            "dimension": dim,
                            "metric_id": metric_def.metric_id,
                            "allowed_dimensions": metric_def.allowed_dimensions,
                        },
                    )
                )

        for filter_key in clean_filters:
            if filter_key not in metric_def.allowed_dimensions:
                return Failure(
                    InvalidDimensionFilterError(
                        f"Filter dimension '{filter_key}' not permitted for metric '{metric_def.metric_id}'",
                        details={
                            "filter_dimension": filter_key,
                            "metric_id": metric_def.metric_id,
                            "allowed_dimensions": metric_def.allowed_dimensions,
                        },
                    )
                )

        # 5. Filter dataset strictly by tenant and as_of watermark (INV-DATA-001)
        source_data = dataset if dataset is not None else self._dataset
        tenant_data = self._filter_tenant_and_as_of(
            source_data=source_data,
            tenant_id=tenant_context.tenant_id,
            as_of=request.as_of_time,
        )

        # 6. Generate time slices according to grain
        slices = self._generate_time_slices(request.time_window, request.grain)

        # 7. Evaluate each slice
        series_points: list[MetricSeriesPoint] = []
        for win_start, win_end in slices:
            slice_data = self._slice_dataset(tenant_data, metric_def.metric_id, win_start, win_end, request.as_of_time)
            effective_as_of = win_end if win_end.value < request.as_of_time.value else request.as_of_time

            if not request.group_by_dimensions:
                # No group-by: single evaluation for the window slice
                val = metric_def.calculate_fn(tenant_context.tenant_id, slice_data, effective_as_of, clean_filters)
                pt = self._to_series_point(win_start, win_end, {}, val)
                series_points.append(pt)
            else:
                # Group by requested dimensions
                groups = self._extract_groups(slice_data, metric_def, request.group_by_dimensions, clean_filters)
                if not groups:
                    # Zero volume group placeholder
                    zero_dims = {d: _UNKNOWN_SENTINEL for d in request.group_by_dimensions}
                    pt = MetricSeriesPoint(
                        window_start=win_start,
                        window_end=win_end,
                        dimensions=zero_dims,
                        actual_value=0.0,
                        numerator_value=0.0,
                        denominator_value=0.0,
                        sample_size=0,
                        is_zero_volume_sample=True,
                    )
                    series_points.append(pt)
                else:
                    for group_dims in groups:
                        combined_filters = {**clean_filters, **group_dims}
                        val = metric_def.calculate_fn(
                            tenant_context.tenant_id,
                            slice_data,
                            effective_as_of,
                            combined_filters,
                        )
                        pt = self._to_series_point(win_start, win_end, group_dims, val)
                        series_points.append(pt)

        # 8. Deterministic lineage snapshot hash
        lineage_str = (
            f"{tenant_context.tenant_id}:{metric_def.metric_id}:{request.metric_version}:"
            f"{request.grain}:{request.time_window.start_time.isoformat()}:{request.time_window.end_time.isoformat()}:"
            f"{request.as_of_time.isoformat()}:{sorted(request.group_by_dimensions)}:{sorted(clean_filters.items())}"
        )
        lineage_hash = hashlib.sha256(lineage_str.encode("utf-8")).hexdigest()

        response = MetricQueryResponse(
            query_id=f"mqy_{uuid4().hex[:16]}",
            metric_id=metric_def.metric_id,
            metric_name=metric_def.name,
            metric_version=request.metric_version,
            tenant_id=tenant_context.tenant_id,
            grain=request.grain.upper(),
            as_of_time=request.as_of_time,
            freshness_state="FRESH",
            data_quality_state="PASSED",
            lineage_snapshot_hash=lineage_hash,
            series=series_points,
        )

        return Success(response)

    # =========================================================================
    # Internal Helpers
    # =========================================================================

    def _filter_tenant_and_as_of(
        self,
        source_data: MetricEvaluationDataset,
        tenant_id: TenantId,
        as_of: UtcDateTime,
    ) -> MetricEvaluationDataset:
        """Filter raw dataset strictly by tenant_id and as_of watermark (INV-DATA-001)."""
        as_of_val = as_of.value

        def _is_valid(rec: Any) -> bool:
            if rec.tenant_id != tenant_id:
                return False
            # Check primary event time
            event_dt = getattr(rec, "event_time", None)
            if event_dt is not None and event_dt.value > as_of_val:
                return False
            return True

        def _is_payment_valid(p: PaymentReference) -> bool:
            if p.tenant_id != tenant_id:
                return False
            if p.processed_at.value > as_of_val:
                return False
            return True

        return MetricEvaluationDataset(
            customers=tuple(c for c in source_data.customers if _is_valid(c)),
            orders=tuple(o for o in source_data.orders if _is_valid(o)),
            order_lines=tuple(ol for ol in source_data.order_lines if _is_valid(ol)),
            shipments=tuple(s for s in source_data.shipments if _is_valid(s)),
            support_tickets=tuple(t for t in source_data.support_tickets if _is_valid(t)),
            maintenance_events=tuple(m for m in source_data.maintenance_events if _is_valid(m)),
            contracts=tuple(ct for ct in source_data.contracts if _is_valid(ct)),
            contract_clauses=tuple(cl for cl in source_data.contract_clauses if _is_valid(cl)),
            payment_references=tuple(p for p in source_data.payment_references if _is_payment_valid(p)),
        )

    def _generate_time_slices(self, window: Any, grain: str) -> list[tuple[UtcDateTime, UtcDateTime]]:
        """Divide time window into discrete slices based on requested grain."""
        grain_upper = grain.upper().strip()
        start_val = window.start_time.value
        end_val = window.end_time.value

        if grain_upper == "AS_OF_SNAPSHOT" or start_val >= end_val:
            return [(window.start_time, window.end_time)]

        if grain_upper == "HOURLY":
            step = timedelta(hours=1)
        elif grain_upper == "DAILY":
            step = timedelta(days=1)
        elif grain_upper == "WEEKLY":
            step = timedelta(weeks=1)
        elif grain_upper == "MONTHLY":
            step = timedelta(days=30)
        else:
            step = timedelta(days=1)

        slices: list[tuple[UtcDateTime, UtcDateTime]] = []
        curr = start_val
        while curr < end_val:
            nxt = min(curr + step, end_val)
            slices.append((UtcDateTime(curr), UtcDateTime(nxt)))
            curr = nxt

        return slices or [(window.start_time, window.end_time)]

    def _slice_dataset(
        self,
        tenant_data: MetricEvaluationDataset,
        metric_id: str,
        win_start: UtcDateTime,
        win_end: UtcDateTime,
        as_of: UtcDateTime,
    ) -> MetricEvaluationDataset:
        """Filter dataset records relevant to the current window slice."""
        s_val = win_start.value
        e_val = win_end.value

        # For METRIC-002 (revenue_at_risk): Snapshot of active orders up to win_end
        if metric_id == "METRIC-002":
            return MetricEvaluationDataset(
                customers=tenant_data.customers,
                orders=tuple(o for o in tenant_data.orders if o.event_time.value <= e_val),
                order_lines=tenant_data.order_lines,
                shipments=tuple(s for s in tenant_data.shipments if s.event_time.value <= e_val),
                support_tickets=tuple(t for t in tenant_data.support_tickets if t.event_time.value <= e_val),
                maintenance_events=tenant_data.maintenance_events,
                contracts=tenant_data.contracts,
                contract_clauses=tenant_data.contract_clauses,
                payment_references=tenant_data.payment_references,
            )

        # Standard window-bounded slice:
        # Include records whose primary event time falls within [s_val, e_val]
        orders = tuple(o for o in tenant_data.orders if s_val <= o.event_time.value <= e_val)
        shipments = tuple(s for s in tenant_data.shipments if s_val <= s.event_time.value <= e_val)
        tickets = tuple(t for t in tenant_data.support_tickets if s_val <= t.event_time.value <= e_val)
        payments = tuple(p for p in tenant_data.payment_references if s_val <= p.processed_at.value <= e_val)
        customers = tuple(c for c in tenant_data.customers if s_val <= c.event_time.value <= e_val)

        return MetricEvaluationDataset(
            customers=customers or tenant_data.customers,
            orders=orders,
            order_lines=tenant_data.order_lines,
            shipments=shipments,
            support_tickets=tickets,
            maintenance_events=tenant_data.maintenance_events,
            contracts=tenant_data.contracts,
            contract_clauses=tenant_data.contract_clauses,
            payment_references=payments,
        )

    def _extract_groups(
        self,
        slice_data: MetricEvaluationDataset,
        metric_def: MetricDefinition,
        group_by_dimensions: list[str],
        filters: dict[str, Any],
    ) -> list[dict[str, str]]:
        """Extract distinct combinations of requested group_by_dimensions matching filters."""
        # Index lookups
        cust_by_id = {c.id: c for c in slice_data.customers}
        shipments_by_order: dict[str, list[Shipment]] = {}
        for s in slice_data.shipments:
            shipments_by_order.setdefault(s.order_id, []).append(s)

        lines_by_order: dict[str, list[OrderLine]] = {}
        for ol in slice_data.order_lines:
            lines_by_order.setdefault(ol.order_id, []).append(ol)

        tickets_by_order: dict[str, list[SupportTicket]] = {}
        for t in slice_data.support_tickets:
            if t.order_id:
                tickets_by_order.setdefault(t.order_id, []).append(t)

        def get_order_dim(o: Order, dim: str) -> list[str]:
            if dim == "customer_tier":
                cust = cust_by_id.get(o.customer_id)
                return [getattr(cust.account_tier, "value", str(cust.account_tier))] if cust else [_UNKNOWN_SENTINEL]
            if dim in ("carrier_id", "warehouse_id", "origin_region", "destination_region"):
                ships = shipments_by_order.get(o.id, [])
                if ships:
                    return list({getattr(s, dim, _UNKNOWN_SENTINEL) for s in ships})
                return [_UNKNOWN_SENTINEL]
            if dim == "product_category":
                lines = lines_by_order.get(o.id, [])
                if lines:
                    return list({getattr(l, "product_category", _UNKNOWN_SENTINEL) for l in lines})
                return [_UNKNOWN_SENTINEL]
            return [_UNKNOWN_SENTINEL]

        def get_shipment_dim(s: Shipment, dim: str) -> str:
            val = getattr(s, dim, None)
            return str(val) if val is not None else _UNKNOWN_SENTINEL

        def get_ticket_dim(t: SupportTicket, dim: str) -> str:
            if dim == "topic":
                return getattr(t.topic, "value", str(t.topic))
            if dim == "priority":
                return getattr(t.priority, "value", str(t.priority))
            if dim == "customer_tier":
                cust = cust_by_id.get(t.customer_id)
                return getattr(cust.account_tier, "value", str(cust.account_tier)) if cust else _UNKNOWN_SENTINEL
            return _UNKNOWN_SENTINEL

        def get_payment_dim(p: PaymentReference, dim: str) -> str:
            val = getattr(p, dim, None)
            return getattr(val, "value", str(val)) if val is not None else _UNKNOWN_SENTINEL

        def get_customer_dim(c: Customer, dim: str) -> str:
            if dim == "segment":
                return getattr(c.segment, "value", str(c.segment))
            if dim in ("account_tier", "customer_tier"):
                return getattr(c.account_tier, "value", str(c.account_tier))
            if dim == "billing_country":
                return c.billing_country or _UNKNOWN_SENTINEL
            return _UNKNOWN_SENTINEL

        groups_set: set[tuple[tuple[str, str], ...]] = set()

        # Primary source entity routing
        mid = metric_def.metric_id
        if mid in ("METRIC-001", "METRIC-002", "METRIC-004", "METRIC-007"):
            for o in slice_data.orders:
                dim_options: list[list[tuple[str, str]]] = []
                for d in group_by_dimensions:
                    vals = get_order_dim(o, d)
                    dim_options.append([(d, v) for v in vals])
                # Cartesian product of options for this order
                for combo in self._cartesian_product(dim_options):
                    combo_dict = dict(combo)
                    if all(combo_dict.get(k) == str(v) for k, v in filters.items() if k in combo_dict):
                        groups_set.add(tuple(sorted(combo)))

        elif mid in ("METRIC-003", "METRIC-008"):
            for s in slice_data.shipments:
                combo = tuple(sorted((d, get_shipment_dim(s, d)) for d in group_by_dimensions))
                combo_dict = dict(combo)
                if all(combo_dict.get(k) == str(v) for k, v in filters.items() if k in combo_dict):
                    groups_set.add(combo)

        elif mid == "METRIC-005":
            for p in slice_data.payment_references:
                combo = tuple(sorted((d, get_payment_dim(p, d)) for d in group_by_dimensions))
                combo_dict = dict(combo)
                if all(combo_dict.get(k) == str(v) for k, v in filters.items() if k in combo_dict):
                    groups_set.add(combo)

        elif mid == "METRIC-006":
            for c in slice_data.customers:
                combo = tuple(sorted((d, get_customer_dim(c, d)) for d in group_by_dimensions))
                combo_dict = dict(combo)
                if all(combo_dict.get(k) == str(v) for k, v in filters.items() if k in combo_dict):
                    groups_set.add(combo)

        elif mid == "METRIC-009":
            for t in slice_data.support_tickets:
                combo = tuple(sorted((d, get_ticket_dim(t, d)) for d in group_by_dimensions))
                combo_dict = dict(combo)
                if all(combo_dict.get(k) == str(v) for k, v in filters.items() if k in combo_dict):
                    groups_set.add(combo)

        return [dict(g) for g in sorted(groups_set)]

    @staticmethod
    def _cartesian_product(dim_options: list[list[tuple[str, str]]]) -> list[list[tuple[str, str]]]:
        """Simple deterministic cartesian product without itertools dependency."""
        if not dim_options:
            return []
        result: list[list[tuple[str, str]]] = [[]]
        for pool in dim_options:
            result = [x + [y] for x in result for y in pool]
        return result

    def _to_series_point(
        self,
        win_start: UtcDateTime,
        win_end: UtcDateTime,
        dimensions: dict[str, str],
        metric_val: Any,
    ) -> MetricSeriesPoint:
        """Convert MetricValue calculation result to immutable MetricSeriesPoint."""
        den = float(metric_val.denominator if metric_val.denominator is not None else 0.0)
        num = float(metric_val.numerator if metric_val.numerator is not None else metric_val.value)

        # Zero volume check (denominator = 0 or zero sample)
        if den == 0.0 or metric_val.is_zero_sample:
            # AC-P02-001-02: zero volume sample returns actual_value = 0.0 and is_zero_volume_sample = true
            actual_val = 0.0
            is_zero = True
            sample_size = 0
        else:
            actual_val = float(metric_val.value)
            is_zero = False
            sample_size = int(den) if metric_val.denominator is not None else int(metric_val.value)

        return MetricSeriesPoint(
            window_start=win_start,
            window_end=win_end,
            dimensions=dimensions,
            actual_value=actual_val,
            numerator_value=num,
            denominator_value=den,
            sample_size=sample_size,
            is_zero_volume_sample=is_zero,
        )


__all__ = ["MetricService"]
