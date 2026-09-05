# Multi-Tenancy Specification (Canonical Tenant Isolation and Propagation Contract)

Status: Accepted Canonical Specification
Initiative: REVPILOT
Rail Alignment: Rail 2 (Tenant Context & Lifecycle) & Rail 5 (Persistence Isolation Foundation)
Owner: Security Architecture + Tenancy Architecture
Traceability: `INV-TEN-001`, `INV-TEN-002`, `INV-TEN-003`, `NFR-TEN-001`, `NFR-TEN-002`, `INV-REL-001`, `ADR-0001`, `ADR-0005`
Approver: Duong Vinh (Repository Owner)
Version: v1.0
Last Reviewed Date: 2026-09-04

## Revision History

| Version | Date | Author | Reviewer | Approval | Summary of Changes |
|---|---|---|---|---|---|
| v1.0 | 2026-09-04 | Tenancy Architecture | Security Architect | Dương Vinh | Canonical tenant isolation and RLS propagation contract |

---

## 1. Executive Summary and Invariants

This specification governs multi-tenant isolation, context propagation, and data boundaries across all RevPilot AI architectural components. It defines how tenancy is represented, resolved, verified, propagated, and enforced across storage engines, background workers, caches, event outboxes, and object storage.

### Foundational Invariants
1. `INV-TEN-001`: Every tenant-owned persistent or derived record has enforceable Tenant ownership; a query filter alone is legally and technically insufficient.
2. `INV-TEN-002`: Tenant context is server-derived from authenticated membership and cannot be supplied or overridden by client or model payload.
3. `INV-TEN-003`: A global/platform operation uses an explicit privileged context, never `tenant = null` or implicit bypass.
4. `NFR-TEN-001`: Cross-tenant read/write/result/cache/event/export leakage must equal zero (0) across every build, test, and production release.
5. `NFR-TEN-002`: Multi-tenant isolation controls must hold under degraded or 120% accepted peak load. Never disable isolation controls to preserve availability.

---

## 2. Core Tenancy Primitives and Envelopes

### 2.1. TenantId
`TenantId` is an opaque, immutable identifier string adhering to `packages/backend/src/revpilot/shared/identifiers.py`:
- Format: `ten_[a-z0-9]{8,32}` (e.g. `ten_01h7abcde123456789`).
- Immutable: Cannot be modified once created.
- Case-sensitive: Validated against strict alphanumeric regex.

### 2.2. TenantContext and PrincipalContext Value Objects
`TenantContext` and `PrincipalContext` are immutable execution context envelopes (`packages/backend/src/revpilot/shared/context.py`):
```python
@dataclass(frozen=True, slots=True)
class TenantContext:
    tenant_id: TenantId
    organization_id: OrganizationId
    tier: str = "growth"
    is_active: bool = True

@dataclass(frozen=True, slots=True)
class PrincipalContext:
    principal_id: PrincipalId
    tenant_id: TenantId | None
    roles: frozenset[str] = frozenset()
    permissions: frozenset[str] = frozenset()
    is_system: bool = False
```

- **Strict Non-Null Tenant Invariant**: `TenantContext.tenant_id` is strictly non-nullable and validated on instantiation. Normal tenant business operations must never carry a null tenant context (`INV-TEN-002`). Any suspended or deactivated tenant raises `TenancyViolationError`.
- **System and Platform Boundary**:
  - Regular callers require `tenant_id is not None`. If `is_system` is `False` and `tenant_id is None`, `TenancyViolationError` is raised fail-closed (`INV-TEN-003`).
  - Platform maintenance, migrations, and cross-tenant reconciliation use either a verified platform `PrincipalContext(is_system=True, tenant_id=None)` or the canonical opaque `PrivilegedContext` (`packages/backend/src/revpilot/modules/identity/domain/models.py`), produced only by server-side authentication with cryptographic platform signature. Setting a caller-supplied flag or calling `TenantContext(tenant_id=None)` is structurally prohibited.
- **Server-Derived**: Created solely by verified server-side identity resolution (`TenancyService` / `AuthenticationPort`).
- **Immutable**: Once instantiated, attributes cannot be modified. Any tenant switch requires deriving a new, distinct context.
- **Expiration**: Context instances have bounded validity matching token/session lifetime. Expired contexts are immediately rejected.


---

## 3. Multi-Tenancy Tiers (`ADR-0005`)

| Tier | Persistent Isolation Boundary | Vector / Cache / Object Boundary | Promotion Trigger |
|---|---|---|---|
| **Shared (SMB)** | Shared PostgreSQL tables with composite tenant keys (`(tenant_id, id)`), transaction-scoped PostgreSQL Row-Level Security (RLS) | Tenant prefix key namespacing in Redis/Valkey, S3 tenant prefix keys, metadata filtering | Default baseline tier |
| **Enterprise** | Dedicated PostgreSQL database or dedicated PostgreSQL schema, dedicated connection pool | Dedicated vector collection / partition, dedicated Redis database / isolated prefix, dedicated KMS key | Contractual residency requirement, high throughput noisy-neighbor SLA, custom encryption |
| **Regulated** | Dedicated database cluster, dedicated cloud tenant VPC / subnet, client-managed encryption key (CMEK) | Dedicated vector cluster, physically isolated object bucket, zero data co-mingling | Strict compliance / regulatory sovereignty (FedRAMP, HIPAA, FINRA), dedicated restore requirements |

---

## 4. Tenant Context Propagation Across Subsystems

Tenant context must be propagated explicitly across every layer of the RevPilot system without relying on fragile global mutable singletons:

```text
HTTP Request (Authorization Header)
  │
  ▼ [API Middleware]
  Validates Token Claims ──▶ Resolves Active Membership ──▶ Instantiates TenantContext
  │
  ├─────────────────────────────────────────────────────────────────────────────┐
  ▼                                                                             ▼
[Application Services]                                                [Background Workers / Temporal]
  Passes TenantContext as first argument                                  Envelopes TenantContext in Workflow Input
  │                                                                             │
  ├──▶ [SQL Repositories]: Sets SET LOCAL revpilot.current_tenant_id            ├──▶ Unpacks Context & Revalidates Status
  ├──▶ [Cache]: Namespaces key as {tenant_id}:{cache_key}                       ├──▶ Sets RLS session context per Activity
  ├──▶ [Object Storage]: Namespaces prefix as {tenant_id}/{object_path}         └──▶ Dispatches with TenantCorrelationId
  ├──▶ [Event Outbox]: Injects tenant_id into Event Envelope header
  └──▶ [Vector/RAG Engine]: Injects hard filter (tenant_id == ctx.tenant_id)
```

### 4.1. HTTP API Boundary
- Incoming requests provide authentication credentials (e.g. Bearer token).
- Controller middleware normalizes claims, verifies active tenant status in `TenancyService`, and constructs `TenantContext`.
- Client-supplied tenant IDs in headers (`X-Tenant-ID`) or payload bodies are rejected or ignored (`INV-TEN-002`).

### 4.2. Relational Database Boundary (PostgreSQL)
- Every transaction targeting tenant-owned tables executes `SET LOCAL revpilot.current_tenant_id = :tenant_id` at transaction start.
- PostgreSQL Row-Level Security (RLS) policies enforce `tenant_id = current_setting('revpilot.current_tenant_id')`.
- On connection release / rollback, session context is cleared (`RESET revpilot.current_tenant_id`).
- If `current_setting('revpilot.current_tenant_id')` is missing, empty, or malformed, RLS denies 100% of rows (fail closed).

### 4.3. Cache and Ephemeral Storage
- Cache keys MUST use strict namespacing: `{tenant_id}:{entity_name}:{id}`.
- Global cache reads across multiple tenants are prohibited.
- Eviction and cache invalidation operations are strictly scoped by tenant key prefixes.

### 4.4. Event Streaming and Outbox
- All transactional outbox events MUST include `tenant_id` in the top-level envelope metadata.
- Event consumers unpack the envelope, verify recipient tenant context, and execute within that isolated boundary.
- Cross-tenant event broadcasting is prohibited unless the event is an explicit platform operational notification.

### 4.5. Retrieval-Augmented Generation (RAG) and Vector Stores
- Every chunk and index metadata record contains `tenant_id`.
- Hybrid search queries (dense embeddings + BM25 sparse search) enforce a mandatory pre-filter: `tenant_id == :tenant_id`.
- Search queries without an explicit, server-derived tenant filter are rejected before submission to the vector engine.

### 4.6. Audit Logging and Telemetry
- Every audit record records `tenant_id` or explicit `privileged_operator_id`.
- Telemetry traces and metrics carry low-cardinality `tenant_id` attribute.
- Cross-tenant queries in observability backends are restricted to authorized platform auditors.

---

## 5. Platform Privileged Operations (`INV-TEN-003`)

- Platform maintenance, migrations, and cross-tenant reconciliation MUST use a dedicated opaque `PrivilegedContext` issued by the verified authentication factory; `TenantContext(is_system=True, tenant_id=None)` is not a permitted construction pattern.
- Bypassing tenancy by passing `tenant_id = None`, `tenant_id = ""`, or `tenant_id = "*"` to tenant-scoped repository methods is strictly forbidden.
- Privileged operations emit an unsampled audit event at invocation (`identity.privileged_access.invoked`).
- Autonomous AI agents can never assume, receive, or be delegated privileged platform context.

---

## 6. Lifecycle Propagation: Provisioning, Suspension, Legal Hold, Deletion, and Export

Complete operational and state machine contracts are specified in `docs/13-multi-tenancy/TENANT-OPERATIONS-SPEC.md`.

1. **Provisioning and Activation**:
   - Resources (PostgreSQL RLS/schema, Redis `{tenant_id}:`, S3 `{tenant_id}/`, vector collections, default quotas, and audit partitions) must be 100% provisioned and verified before a tenant is activated.
   - Partial provisioning never grants active status (`INV-REL-001`).
2. **Suspension**:
   - `Tenant.suspend(reason)` transitions tenant status to `SUSPENDED`.
   - All subsequent attempts to create active `TenantContext` raise `TenancyViolationError` immediately.
   - Ongoing background workflows for the suspended tenant pause or cancel gracefully.
   - 100% of tool gateway actions and inbound webhooks are blocked.
   - Audit records and recovery metadata are strictly preserved.
3. **Legal Hold (`LEGAL_HOLD`)**:
   - Compliance lock prevents automated or manual deletion.
   - Any deletion request targeting a tenant under legal hold fails closed with `LEGAL_HOLD_ACTIVE` (409).
4. **Data Deletion & Export Propagation**:
   - Export operations generate an encrypted bundle containing exclusively records matching target `tenant_id`, accompanied by a cryptographic SHA-256 manifest.
   - Deletion workflows propagate irreversible cascade deletion across PostgreSQL, Redis cache, vector/search collections, object storage, Temporal workflow histories, connector sync cursors, and ML feature projections.
   - Completed deletions emit an immutable `tenancy.data.deletion_completed` audit event containing SHA-256 partition purge proofs.

---

## 7. Degraded System and Failure Modes (`INV-REL-001`)

- If the tenancy verification service, RLS context setter, or session policy encounters an error, timeout, or transient failure:
  - **The system fails closed**: 100% of write operations and external actions are blocked.
  - Read operations cannot bypass tenant boundaries under degraded mode.
  - Under no circumstances is tenant isolation relaxed or bypassed to increase availability or clear error alerts (`NFR-TEN-002`).

---

## 8. Cross-Tenant Negative Test Matrix

The following test scenarios must be executed and verified as 100% passing before any rail exit gate:

| Test Identifier | Surface | Description | Expected Result |
|---|---|---|---|
| `TEST-TEN-001` | Repository | Tenant A attempts to read Tenant B record by ID | Returns empty / raises `EntityNotFoundError` |
| `TEST-TEN-002` | Repository | Tenant A attempts to update or delete Tenant B record | 0 rows affected / raises `EntityNotFoundError` |
| `TEST-TEN-003` | RLS Context | Query executed with missing / unset RLS session setting | PostgreSQL RLS returns 0 rows / fails closed |
| `TEST-TEN-004` | RLS Context | Query executed with malformed / invalid tenant setting | Fails closed with database error |
| `TEST-TEN-005` | Cache | Tenant A requests cache key of Tenant B | Cache miss (keys are strictly partitioned) |
| `TEST-TEN-006` | Event Outbox | Consumer receives Tenant A event with Tenant B context | Rejects event / raises `TenancyViolationError` |
| `TEST-TEN-007` | Vector / RAG | Tenant A semantic query attempts to retrieve Tenant B chunks | 0 results returned from Tenant B index |
| `TEST-TEN-008` | Object Storage | Tenant A requests file URI belonging to Tenant B prefix | Access Denied / raises `TenancyViolationError` |
| `TEST-TEN-009` | Client Override | Request header includes `X-Tenant-ID: ten_evil` over token | Ignored; context derived strictly from token |
| `TEST-TEN-010` | Suspended Tenant | Inactive / suspended tenant attempts API action | Rejects with 403 `TENANCY_VIOLATION` |
| `TEST-TEN-011` | Null Context | Tenant repository called with `tenant_id = None` | Fails closed with `TenancyViolationError` |
