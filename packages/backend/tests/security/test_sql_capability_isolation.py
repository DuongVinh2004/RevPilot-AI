"""
RevPilot AI — Security and Tenancy Isolation Tests for SQL Capabilities
Specification: docs/06-agent-platform/SQL-CAPABILITY-CATALOG.md §5
Verifies AC-P03-003-02: 100% rejection of DDL/DML, parameter tampering, and temporal leakage.
Enforces INV-TEN-001, INV-TEN-002, INV-ACT-001, INV-DATA-001, and INV-IAM-001.
"""

from __future__ import annotations
import asyncio
import sqlite3
import sys
import pytest

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
def sqlite_multi_tenant_db():
    """In-memory SQLite database populated with canonical tables and seeded with 2 separate tenants."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

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
    """)

    # Tenant Alpha data
    cur.executescript("""
    INSERT INTO canonical_customers VALUES ('tnt_alpha', 'c1', 'Alpha Corp', 'ENTERPRISE', 'TIER_1', 'US_EAST', 'ACTIVE');
    INSERT INTO canonical_orders VALUES ('tnt_alpha', 'o1', 'c1', 'COMPLETED', 10000, '2026-05-10T10:00:00Z');
    INSERT INTO canonical_orders VALUES ('tnt_alpha', 'o2', 'c1', 'CANCELLED', 2000, '2026-05-11T10:00:00Z');
    """)

    # Tenant Beta data
    cur.executescript("""
    INSERT INTO canonical_customers VALUES ('tnt_beta', 'c2', 'Beta Inc', 'SMB', 'TIER_2', 'US_WEST', 'ACTIVE');
    INSERT INTO canonical_orders VALUES ('tnt_beta', 'o3', 'c2', 'COMPLETED', 999999, '2026-05-10T10:00:00Z');
    INSERT INTO canonical_orders VALUES ('tnt_beta', 'o4', 'c2', 'CANCELLED', 888888, '2026-05-11T10:00:00Z');
    """)

    conn.commit()
    yield conn
    conn.close()


@pytest.fixture
def tenant_alpha():
    return TenantContext(
        tenant_id=TenantId("tnt_alpha"),
        organization_id=OrganizationId("org_alpha"),
        tier="growth",
    )


@pytest.fixture
def principal_alpha():
    return PrincipalContext(
        principal_id=PrincipalId("usr_alpha"),
        tenant_id=TenantId("tnt_alpha"),
        roles=frozenset(["analyst"]),
        permissions=frozenset(["analytics:query"]),
    )


@pytest.fixture
def executor(analytics_cap_module):
    return analytics_cap_module.SqlCapabilityExecutor()


# =============================================================================
# AC-P03-003-02: Tenancy & Safety Isolation Tests
# =============================================================================

@pytest.mark.asyncio
async def test_tenant_isolation_negative(analytics_cap_module, sqlite_multi_tenant_db, tenant_alpha, principal_alpha, executor):
    """Verify Tenant Alpha never sees any data belonging to Tenant Beta (INV-TEN-001)."""
    req = analytics_cap_module.CapabilityRequest(
        capability_id="CAP-SQL-DRILLDOWN-DIM",
        tenant_context=tenant_alpha,
        principal_context=principal_alpha,
        investigation_id="inv_sec_01",
        as_of_time="2026-05-18T00:00:00Z",
        parameters={
            "dimension": "order_status",
            "start_time": "2026-05-01T00:00:00Z",
            "end_time": "2026-05-17T00:00:00Z",
        },
    )

    res = await executor.execute(req, sqlite_multi_tenant_db)
    assert res.is_success
    data = res.value
    # Alpha only has 2 orders (1 COMPLETED, 1 CANCELLED)
    total_orders = sum(r["total_orders"] for r in data.rows)
    assert total_orders == 2
    # Revenue should be (10000 + 2000) / 100 = 120.0, Beta's million-dollar orders must not appear
    total_rev = sum(r["total_revenue"] for r in data.rows)
    assert total_rev == 120.0


@pytest.mark.asyncio
async def test_tenant_parameter_tampering_ignored(analytics_cap_module, sqlite_multi_tenant_db, tenant_alpha, principal_alpha, executor):
    """
    Attempt to inject foreign tenant_id into parameters.
    System must discard parameter and enforce server-derived tenant context (INV-TEN-002).
    """
    req = analytics_cap_module.CapabilityRequest(
        capability_id="CAP-SQL-DRILLDOWN-DIM",
        tenant_context=tenant_alpha,
        principal_context=principal_alpha,
        investigation_id="inv_sec_02",
        as_of_time="2026-05-18T00:00:00Z",
        parameters={
            "tenant_id": "tnt_beta",  # Adversarial parameter tampering attempt
            "dimension": "order_status",
            "start_time": "2026-05-01T00:00:00Z",
            "end_time": "2026-05-17T00:00:00Z",
        },
    )

    res = await executor.execute(req, sqlite_multi_tenant_db)
    assert res.is_success
    data = res.value
    total_orders = sum(r["total_orders"] for r in data.rows)
    # Must still strictly return Alpha's 2 orders, not Beta's
    assert total_orders == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "malicious_payload",
    [
        "; DROP TABLE canonical_orders; --",
        "'; DELETE FROM canonical_orders WHERE '1'='1",
        "; UPDATE canonical_orders SET total_cents = 0; --",
        "; INSERT INTO canonical_orders VALUES ('tnt_alpha', 'bad', 'c1', 'COMPLETED', 1, '2026-05-10'); --",
        "; ALTER TABLE canonical_orders ADD COLUMN hacked TEXT; --",
        "; TRUNCATE canonical_orders; --",
        "order_status; DROP TABLE canonical_orders",
        "/* comment */ DROP",
    ],
)
async def test_ddl_dml_injection_blocked(
    analytics_cap_module, sqlite_multi_tenant_db, tenant_alpha, principal_alpha, executor, malicious_payload
):
    """
    Verify all DDL/DML injection attacks in any parameter are blocked 100% (INV-ACT-001).
    """
    req = analytics_cap_module.CapabilityRequest(
        capability_id="CAP-SQL-DRILLDOWN-DIM",
        tenant_context=tenant_alpha,
        principal_context=principal_alpha,
        investigation_id="inv_sec_03",
        as_of_time="2026-05-18T00:00:00Z",
        parameters={
            "dimension": malicious_payload,
            "start_time": "2026-05-01T00:00:00Z",
            "end_time": "2026-05-17T00:00:00Z",
        },
    )

    res = await executor.execute(req, sqlite_multi_tenant_db)
    assert res.is_failure
    assert res.error.code in ("ERR_PROHIBITED_SQL_OPERATION", "ERR_DISALLOWED_DIMENSION")
    assert res.error.http_status in (400, 403)

    # Verify table is intact and uncorrupted
    cur = sqlite_multi_tenant_db.cursor()
    cur.execute("SELECT COUNT(*) FROM canonical_orders")
    count = cur.fetchone()[0]
    assert count == 4


@pytest.mark.asyncio
async def test_disallowed_dimension_rejected(analytics_cap_module, sqlite_multi_tenant_db, tenant_alpha, principal_alpha, executor):
    """Attempting to drill down on unwhitelisted dimension is rejected (ERR_DISALLOWED_DIMENSION)."""
    req = analytics_cap_module.CapabilityRequest(
        capability_id="CAP-SQL-DRILLDOWN-DIM",
        tenant_context=tenant_alpha,
        principal_context=principal_alpha,
        investigation_id="inv_sec_04",
        as_of_time="2026-05-18T00:00:00Z",
        parameters={
            "dimension": "customer_credit_card_number",
            "start_time": "2026-05-01T00:00:00Z",
            "end_time": "2026-05-17T00:00:00Z",
        },
    )

    res = await executor.execute(req, sqlite_multi_tenant_db)
    assert res.is_failure
    assert res.error.code == "ERR_DISALLOWED_DIMENSION"
    assert res.error.http_status == 400


@pytest.mark.asyncio
async def test_temporal_leakage_rejected(analytics_cap_module, sqlite_multi_tenant_db, tenant_alpha, principal_alpha, executor):
    """Attempting to query past the as_of_time boundary is rejected (INV-DATA-001, ERR_TEMPORAL_LEAKAGE)."""
    req = analytics_cap_module.CapabilityRequest(
        capability_id="CAP-SQL-DRILLDOWN-DIM",
        tenant_context=tenant_alpha,
        principal_context=principal_alpha,
        investigation_id="inv_sec_05",
        as_of_time="2026-05-15T00:00:00Z",
        parameters={
            "dimension": "order_status",
            "start_time": "2026-05-01T00:00:00Z",
            "end_time": "2026-05-20T00:00:00Z",  # In the future relative to as_of_time
        },
    )

    res = await executor.execute(req, sqlite_multi_tenant_db)
    assert res.is_failure
    assert res.error.code == "ERR_TEMPORAL_LEAKAGE"
    assert res.error.http_status == 400


@pytest.mark.asyncio
async def test_unauthorized_permission_rejected(analytics_cap_module, sqlite_multi_tenant_db, tenant_alpha, executor):
    """Caller lacking analytics:query permission is denied (INV-IAM-001, ERR_UNAUTHORIZED_PERMISSION)."""
    unauthorized_principal = PrincipalContext(
        principal_id=PrincipalId("usr_guest"),
        tenant_id=TenantId("tnt_alpha"),
        roles=frozenset(["viewer"]),
        permissions=frozenset(["reports:read"]),  # Missing analytics:query
    )

    req = analytics_cap_module.CapabilityRequest(
        capability_id="CAP-SQL-DRILLDOWN-DIM",
        tenant_context=tenant_alpha,
        principal_context=unauthorized_principal,
        investigation_id="inv_sec_06",
        as_of_time="2026-05-18T00:00:00Z",
        parameters={
            "dimension": "order_status",
            "start_time": "2026-05-01T00:00:00Z",
            "end_time": "2026-05-17T00:00:00Z",
        },
    )

    res = await executor.execute(req, sqlite_multi_tenant_db)
    assert res.is_failure
    assert res.error.code == "ERR_UNAUTHORIZED_PERMISSION"
    assert res.error.http_status == 403


@pytest.mark.asyncio
async def test_unregistered_capability_rejected(analytics_cap_module, sqlite_multi_tenant_db, tenant_alpha, principal_alpha, executor):
    """Unknown capability identifier is rejected with ERR_UNREGISTERED_CAPABILITY."""
    req = analytics_cap_module.CapabilityRequest(
        capability_id="CAP-SQL-RAW-ARBITRARY",
        tenant_context=tenant_alpha,
        principal_context=principal_alpha,
        investigation_id="inv_sec_07",
        as_of_time="2026-05-18T00:00:00Z",
    )

    res = await executor.execute(req, sqlite_multi_tenant_db)
    assert res.is_failure
    assert res.error.code == "ERR_UNREGISTERED_CAPABILITY"
    assert res.error.http_status == 404


@pytest.mark.asyncio
async def test_statement_timeout_enforced(analytics_cap_module, tenant_alpha, principal_alpha, executor):
    """Simulated statement timeout returns ERR_QUERY_TIMEOUT (NFR-AI-004)."""
    req = analytics_cap_module.CapabilityRequest(
        capability_id="CAP-SQL-DRILLDOWN-DIM",
        tenant_context=tenant_alpha,
        principal_context=principal_alpha,
        investigation_id="inv_sec_08",
        as_of_time="2026-05-18T00:00:00Z",
        parameters={
            "dimension": "order_status",
            "start_time": "2026-05-01T00:00:00Z",
            "end_time": "2026-05-17T00:00:00Z",
        },
    )

    # Pass an execute error that mimics postgres statement timeout
    class TimeoutDbSession:
        def cursor(self):
            raise Exception("canceling statement due to statement timeout")

    res = await executor.execute(req, TimeoutDbSession())
    assert res.is_failure
    assert res.error.code == "ERR_QUERY_TIMEOUT"
    assert res.error.http_status == 504
