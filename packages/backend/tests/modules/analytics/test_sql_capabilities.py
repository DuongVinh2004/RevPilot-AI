"""
RevPilot AI — Unit and Integration Tests for Registered SQL Capabilities
Specification: docs/06-agent-platform/SQL-CAPABILITY-CATALOG.md
Verifies AC-P03-003-01: All 7 registered capabilities executable with parameterized inputs.
"""

from __future__ import annotations
import sqlite3
import sys
import pytest
from decimal import Decimal

from revpilot.shared.identifiers import TenantId, PrincipalId, OrganizationId
from revpilot.shared.context import TenantContext, PrincipalContext


@pytest.fixture(autouse=True)
def _isolate_analytics_module():
    """Ensure analytics module is clean between test runs and during collection."""
    yield
    for mod in list(sys.modules.keys()):
        if mod.startswith("revpilot.modules.analytics"):
            sys.modules.pop(mod, None)


@pytest.fixture
def analytics_cap_module():
    """Lazily import analytics capabilities to avoid collection phase dependency pollution."""
    import revpilot.modules.analytics.capabilities as mod
    return mod


@pytest.fixture
def sqlite_canonical_db():
    """In-memory SQLite database populated with canonical tables and seeded multi-tenant test data."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Create canonical tables
    cur.executescript("""
    CREATE TABLE canonical_customers (
        tenant_id TEXT NOT NULL,
        id TEXT NOT NULL,
        name TEXT NOT NULL,
        segment TEXT NOT NULL,
        tier TEXT NOT NULL,
        region TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'ACTIVE',
        PRIMARY KEY (tenant_id, id)
    );

    CREATE TABLE canonical_orders (
        tenant_id TEXT NOT NULL,
        id TEXT NOT NULL,
        customer_id TEXT NOT NULL,
        order_status TEXT NOT NULL,
        total_cents INTEGER NOT NULL,
        event_time TEXT NOT NULL,
        PRIMARY KEY (tenant_id, id)
    );

    CREATE TABLE canonical_order_lines (
        tenant_id TEXT NOT NULL,
        id TEXT NOT NULL,
        order_id TEXT NOT NULL,
        sku TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        unit_price_cents INTEGER NOT NULL,
        total_price_cents INTEGER NOT NULL,
        event_time TEXT NOT NULL,
        PRIMARY KEY (tenant_id, id)
    );

    CREATE TABLE canonical_shipments (
        tenant_id TEXT NOT NULL,
        id TEXT NOT NULL,
        order_id TEXT NOT NULL,
        carrier_code TEXT NOT NULL,
        origin_warehouse TEXT NOT NULL,
        estimated_delivery_at TEXT NOT NULL,
        actual_delivered_at TEXT,
        event_time TEXT NOT NULL,
        PRIMARY KEY (tenant_id, id)
    );

    CREATE TABLE canonical_tickets (
        tenant_id TEXT NOT NULL,
        id TEXT NOT NULL,
        customer_id TEXT NOT NULL,
        category TEXT NOT NULL,
        priority TEXT NOT NULL,
        first_response_at TEXT,
        event_time TEXT NOT NULL,
        PRIMARY KEY (tenant_id, id)
    );

    CREATE TABLE canonical_maintenance_events (
        tenant_id TEXT NOT NULL,
        id TEXT NOT NULL,
        system_component TEXT NOT NULL,
        event_type TEXT NOT NULL,
        scheduled_start TEXT NOT NULL,
        scheduled_end TEXT NOT NULL,
        status TEXT NOT NULL,
        PRIMARY KEY (tenant_id, id)
    );

    CREATE TABLE canonical_contracts (
        tenant_id TEXT NOT NULL,
        id TEXT NOT NULL,
        customer_id TEXT NOT NULL,
        title TEXT NOT NULL,
        contract_type TEXT NOT NULL,
        effective_from TEXT NOT NULL,
        effective_to TEXT,
        PRIMARY KEY (tenant_id, id)
    );

    CREATE TABLE canonical_contract_clauses (
        tenant_id TEXT NOT NULL,
        id TEXT NOT NULL,
        contract_id TEXT NOT NULL,
        clause_number TEXT NOT NULL,
        clause_type TEXT NOT NULL,
        sla_threshold_hours INTEGER,
        penalty_per_hour_cents INTEGER,
        PRIMARY KEY (tenant_id, id)
    );
    """)

    # Seed data for tenant tnt_alpha123
    t1 = "tnt_alpha123"
    cur.executescript(f"""
    INSERT INTO canonical_customers VALUES ('{t1}', 'cust_01', 'Acme Corp', 'ENTERPRISE', 'TIER_1', 'US_EAST', 'ACTIVE');
    INSERT INTO canonical_customers VALUES ('{t1}', 'cust_02', 'Beta LLC', 'SMB', 'TIER_2', 'US_WEST', 'ACTIVE');

    INSERT INTO canonical_orders VALUES ('{t1}', 'ord_01', 'cust_01', 'COMPLETED', 10000, '2026-05-10T10:00:00Z');
    INSERT INTO canonical_orders VALUES ('{t1}', 'ord_02', 'cust_01', 'CANCELLED', 5000, '2026-05-11T11:00:00Z');
    INSERT INTO canonical_orders VALUES ('{t1}', 'ord_03', 'cust_02', 'COMPLETED', 8000, '2026-05-12T12:00:00Z');
    INSERT INTO canonical_orders VALUES ('{t1}', 'ord_04', 'cust_02', 'CANCELLED', 4000, '2026-05-12T14:00:00Z');

    INSERT INTO canonical_shipments VALUES ('{t1}', 'shp_01', 'ord_01', 'FEDEX', 'WH_EAST', '2026-05-11T12:00:00Z', '2026-05-11T16:00:00Z', '2026-05-10T12:00:00Z');
    INSERT INTO canonical_shipments VALUES ('{t1}', 'shp_02', 'ord_03', 'UPS', 'WH_WEST', '2026-05-13T12:00:00Z', '2026-05-13T10:00:00Z', '2026-05-12T13:00:00Z');

    INSERT INTO canonical_tickets VALUES ('{t1}', 'tkt_01', 'cust_01', 'BILLING', 'P1', '2026-05-11T13:00:00Z', '2026-05-11T12:00:00Z');
    INSERT INTO canonical_tickets VALUES ('{t1}', 'tkt_02', 'cust_02', 'TECHNICAL', 'P2', '2026-05-12T16:00:00Z', '2026-05-12T14:00:00Z');

    INSERT INTO canonical_maintenance_events VALUES ('{t1}', 'maint_01', 'API_GATEWAY', 'UPGRADE', '2026-05-11T02:00:00Z', '2026-05-11T04:00:00Z', 'COMPLETED');

    INSERT INTO canonical_contracts VALUES ('{t1}', 'cnt_01', 'cust_01', 'Master Enterprise Agreement', 'MSA', '2026-01-01T00:00:00Z', '2027-01-01T00:00:00Z');
    INSERT INTO canonical_contract_clauses VALUES ('{t1}', 'cls_01', 'cnt_01', '1.1', 'SLA_AVAILABILITY', 4, 10000);
    """)

    # Seed data for another tenant tnt_beta456
    t2 = "tnt_beta456"
    cur.executescript(f"""
    INSERT INTO canonical_customers VALUES ('{t2}', 'cust_99', 'Gamma Inc', 'SMB', 'TIER_3', 'EU_WEST', 'ACTIVE');
    INSERT INTO canonical_orders VALUES ('{t2}', 'ord_99', 'cust_99', 'CANCELLED', 99999, '2026-05-11T12:00:00Z');
    """)

    conn.commit()
    yield conn
    conn.close()


@pytest.fixture
def tenant_alpha():
    return TenantContext(
        tenant_id=TenantId("tnt_alpha123"),
        organization_id=OrganizationId("org_alpha123"),
        tier="growth",
    )


@pytest.fixture
def principal_alpha():
    return PrincipalContext(
        principal_id=PrincipalId("usr_alpha123"),
        tenant_id=TenantId("tnt_alpha123"),
        roles=frozenset(["analyst"]),
        permissions=frozenset(["analytics:query"]),
    )


@pytest.fixture
def executor(analytics_cap_module):
    return analytics_cap_module.SqlCapabilityExecutor()


# =============================================================================
# AC-P03-003-01: Test Registration & Execution for all 7 Capabilities
# =============================================================================

def test_all_seven_capabilities_registered(analytics_cap_module):
    """Verify exactly the 7 authoritative capabilities are registered."""
    expected_ids = {
        "CAP-SQL-DRILLDOWN-DIM",
        "CAP-SQL-METRIC-TIMESERIES",
        "CAP-SQL-SEGMENT-COMPARE",
        "CAP-SQL-SHIPMENT-DELAY",
        "CAP-SQL-TICKET-VOLUME",
        "CAP-SQL-MAINTENANCE-WINDOW",
        "CAP-SQL-CONTRACT-SLA",
    }
    caps = analytics_cap_module.REGISTERED_SQL_CAPABILITIES
    assert set(caps.keys()) == expected_ids
    for cap_id, cap_def in caps.items():
        assert cap_def.capability_id == cap_id
        assert cap_def.max_rows > 0
        assert cap_def.timeout_ms <= 5000
        assert cap_def.required_permission == "analytics:query"


@pytest.mark.asyncio
async def test_exec_drilldown_dim(analytics_cap_module, sqlite_canonical_db, tenant_alpha, principal_alpha, executor):
    """Execute CAP-SQL-DRILLDOWN-DIM and verify aggregations."""
    req = analytics_cap_module.CapabilityRequest(
        capability_id="CAP-SQL-DRILLDOWN-DIM",
        tenant_context=tenant_alpha,
        principal_context=principal_alpha,
        investigation_id="inv_01",
        as_of_time="2026-05-18T00:00:00Z",
        parameters={
            "dimension": "order_status",
            "start_time": "2026-05-01T00:00:00Z",
            "end_time": "2026-05-17T00:00:00Z",
        },
    )

    res = await executor.execute(req, sqlite_canonical_db)
    assert res.is_success
    data = res.value
    assert data.capability_id == "CAP-SQL-DRILLDOWN-DIM"
    assert data.row_count == 2
    assert len(data.rows) == 2
    assert data.is_truncated is False
    assert len(data.query_digest) == 64
    assert data.cost_usd == Decimal("0.01")

    # Check row aggregations (COMPLETED: 2 orders $180, CANCELLED: 2 orders $90)
    rows_by_status = {r["dimension_value"]: r for r in data.rows}
    assert "COMPLETED" in rows_by_status
    assert "CANCELLED" in rows_by_status
    assert rows_by_status["COMPLETED"]["total_orders"] == 2
    assert rows_by_status["CANCELLED"]["total_orders"] == 2


@pytest.mark.asyncio
async def test_exec_metric_timeseries(analytics_cap_module, sqlite_canonical_db, tenant_alpha, principal_alpha, executor):
    """Execute CAP-SQL-METRIC-TIMESERIES and verify time-bucketed output."""
    req = analytics_cap_module.CapabilityRequest(
        capability_id="CAP-SQL-METRIC-TIMESERIES",
        tenant_context=tenant_alpha,
        principal_context=principal_alpha,
        investigation_id="inv_01",
        as_of_time="2026-05-18T00:00:00Z",
        parameters={
            "interval": "day",
            "start_time": "2026-05-01T00:00:00Z",
            "end_time": "2026-05-17T00:00:00Z",
        },
    )

    res = await executor.execute(req, sqlite_canonical_db)
    assert res.is_success
    data = res.value
    assert data.capability_id == "CAP-SQL-METRIC-TIMESERIES"
    assert data.row_count >= 1
    assert "time_bucket" in data.rows[0]
    assert "total_orders" in data.rows[0]


@pytest.mark.asyncio
async def test_exec_segment_compare(analytics_cap_module, sqlite_canonical_db, tenant_alpha, principal_alpha, executor):
    """Execute CAP-SQL-SEGMENT-COMPARE and verify cross-segment breakdown."""
    req = analytics_cap_module.CapabilityRequest(
        capability_id="CAP-SQL-SEGMENT-COMPARE",
        tenant_context=tenant_alpha,
        principal_context=principal_alpha,
        investigation_id="inv_01",
        as_of_time="2026-05-18T00:00:00Z",
        parameters={
            "segment_a": "ENTERPRISE",
            "segment_b": "SMB",
            "start_time": "2026-05-01T00:00:00Z",
            "end_time": "2026-05-17T00:00:00Z",
        },
    )

    res = await executor.execute(req, sqlite_canonical_db)
    assert res.is_success
    data = res.value
    assert data.capability_id == "CAP-SQL-SEGMENT-COMPARE"
    assert data.row_count == 2
    segments = {r["segment"] for r in data.rows}
    assert segments == {"ENTERPRISE", "SMB"}


@pytest.mark.asyncio
async def test_exec_shipment_delay(analytics_cap_module, sqlite_canonical_db, tenant_alpha, principal_alpha, executor):
    """Execute CAP-SQL-SHIPMENT-DELAY and verify delayed count aggregation."""
    req = analytics_cap_module.CapabilityRequest(
        capability_id="CAP-SQL-SHIPMENT-DELAY",
        tenant_context=tenant_alpha,
        principal_context=principal_alpha,
        investigation_id="inv_01",
        as_of_time="2026-05-18T00:00:00Z",
        parameters={
            "start_time": "2026-05-01T00:00:00Z",
            "end_time": "2026-05-17T00:00:00Z",
        },
    )

    res = await executor.execute(req, sqlite_canonical_db)
    assert res.is_success
    data = res.value
    assert data.capability_id == "CAP-SQL-SHIPMENT-DELAY"
    assert data.row_count >= 1
    carrier_codes = {r["carrier_code"] for r in data.rows}
    assert "FEDEX" in carrier_codes or "UPS" in carrier_codes


@pytest.mark.asyncio
async def test_exec_ticket_volume(analytics_cap_module, sqlite_canonical_db, tenant_alpha, principal_alpha, executor):
    """Execute CAP-SQL-TICKET-VOLUME and verify category/priority counts."""
    req = analytics_cap_module.CapabilityRequest(
        capability_id="CAP-SQL-TICKET-VOLUME",
        tenant_context=tenant_alpha,
        principal_context=principal_alpha,
        investigation_id="inv_01",
        as_of_time="2026-05-18T00:00:00Z",
        parameters={
            "start_time": "2026-05-01T00:00:00Z",
            "end_time": "2026-05-17T00:00:00Z",
        },
    )

    res = await executor.execute(req, sqlite_canonical_db)
    assert res.is_success
    data = res.value
    assert data.capability_id == "CAP-SQL-TICKET-VOLUME"
    assert data.row_count == 2
    assert "ticket_count" in data.rows[0]


@pytest.mark.asyncio
async def test_exec_maintenance_window(analytics_cap_module, sqlite_canonical_db, tenant_alpha, principal_alpha, executor):
    """Execute CAP-SQL-MAINTENANCE-WINDOW and verify window overlap results."""
    req = analytics_cap_module.CapabilityRequest(
        capability_id="CAP-SQL-MAINTENANCE-WINDOW",
        tenant_context=tenant_alpha,
        principal_context=principal_alpha,
        investigation_id="inv_01",
        as_of_time="2026-05-18T00:00:00Z",
        parameters={
            "start_time": "2026-05-10T00:00:00Z",
            "end_time": "2026-05-12T00:00:00Z",
        },
    )

    res = await executor.execute(req, sqlite_canonical_db)
    assert res.is_success
    data = res.value
    assert data.capability_id == "CAP-SQL-MAINTENANCE-WINDOW"
    assert data.row_count == 1
    assert data.rows[0]["system_component"] == "API_GATEWAY"


@pytest.mark.asyncio
async def test_exec_contract_sla(analytics_cap_module, sqlite_canonical_db, tenant_alpha, principal_alpha, executor):
    """Execute CAP-SQL-CONTRACT-SLA and verify clause retrieval."""
    req = analytics_cap_module.CapabilityRequest(
        capability_id="CAP-SQL-CONTRACT-SLA",
        tenant_context=tenant_alpha,
        principal_context=principal_alpha,
        investigation_id="inv_01",
        as_of_time="2026-05-18T00:00:00Z",
        parameters={
            "customer_id": "cust_01",
        },
    )

    res = await executor.execute(req, sqlite_canonical_db)
    assert res.is_success
    data = res.value
    assert data.capability_id == "CAP-SQL-CONTRACT-SLA"
    assert data.row_count == 1
    assert data.rows[0]["clause_number"] == "1.1"
    assert data.rows[0]["sla_threshold_hours"] == 4


def test_executor_sync_execution(analytics_cap_module, sqlite_canonical_db, tenant_alpha, principal_alpha, executor):
    """Verify synchronous execution wrapper works properly."""
    req = analytics_cap_module.CapabilityRequest(
        capability_id="CAP-SQL-DRILLDOWN-DIM",
        tenant_context=tenant_alpha,
        principal_context=principal_alpha,
        investigation_id="inv_01",
        as_of_time="2026-05-18T00:00:00Z",
        parameters={
            "dimension": "order_status",
            "start_time": "2026-05-01T00:00:00Z",
            "end_time": "2026-05-17T00:00:00Z",
        },
    )
    res = executor.execute_sync(req, sqlite_canonical_db)
    assert res.is_success
    assert res.value.row_count == 2


@pytest.mark.asyncio
async def test_budget_exhaustion_guard(analytics_cap_module, sqlite_canonical_db, tenant_alpha, principal_alpha, executor):
    """Reject execution if budget remaining is less than capability cost estimate."""
    req = analytics_cap_module.CapabilityRequest(
        capability_id="CAP-SQL-METRIC-TIMESERIES",
        tenant_context=tenant_alpha,
        principal_context=principal_alpha,
        investigation_id="inv_01",
        as_of_time="2026-05-18T00:00:00Z",
        parameters={
            "start_time": "2026-05-01T00:00:00Z",
            "end_time": "2026-05-17T00:00:00Z",
        },
        budget_remaining_usd=Decimal("0.005"),  # Cost is 0.02
    )

    res = await executor.execute(req, sqlite_canonical_db)
    assert res.is_failure
    assert res.error.code == "ERR_INSUFFICIENT_BUDGET"
    assert res.error.http_status == 402


@pytest.mark.asyncio
async def test_query_digest_deterministic(analytics_cap_module):
    """Verify query digest generation is deterministic given identical inputs."""
    sql = "SELECT * FROM orders WHERE tenant_id = :tenant_id"
    params1 = {"tenant_id": "t1", "limit": 100}
    params2 = {"limit": 100, "tenant_id": "t1"}

    d1 = analytics_cap_module.canonicalize_query_digest(sql, params1)
    d2 = analytics_cap_module.canonicalize_query_digest(sql, params2)
    assert d1 == d2
    assert len(d1) == 64
