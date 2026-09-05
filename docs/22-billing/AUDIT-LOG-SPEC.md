# Immutable Audit Log Specification (Canonical Audit Contract)

Status: Accepted Canonical Specification
Initiative: REVPILOT
Scope: Cross-Cutting Audit Logging and Integrity (Rails 3–5 Integration)
Owner: Security Architecture + Audit Module
Traceability: `INV-AUD-001`, `INV-AUD-002`, `INV-TEN-001..003`, `INV-IAM-001..002`, `INV-REL-001`, `NFR-AUD-001`, `NFR-OBS-002`, `NFR-PRV-001`, `ADR-0010`
Approver: Duong Vinh (Repository Owner)
Version: v1.0
Last Reviewed Date: 2026-09-04

---

## 1. Audit Log Philosophy and Non-Repudiation

The Audit system owns append-only `AuditEvent` and `IntegrityCheckpoint` records, physically and logically segregated from ephemeral operational telemetry (`ADR-0010`). Its purpose is to provide an indisputable, tamper-evident historical record of all security-sensitive events, policy evaluations, authorization denials, privileged platform operations, and external business side effects.

### Foundational Invariants
1. `INV-AUD-001`: Every security, policy, approval, action, and privileged change has a minimized, immutable audit event.
2. `INV-AUD-002`: Immutable audit is not a raw prompt, PII, or secret archive.
3. `NFR-AUD-001`: 100% of required audit events are captured with cryptographic integrity checks.

---

## 2. Mandatory Audit Event Types (Rails 3–5 Alignment)

| Event Type | Category | Emitting Module | Trigger / Condition | Required Payload Fields |
|---|---|---|---|---|
| `identity.principal.created` | Identity | `identity` | User or service principal created | `principal_id`, `type`, `tenant_id`, `created_by` |
| `identity.principal.deactivated` | Identity | `identity` | Principal disabled / terminated | `principal_id`, `tenant_id`, `reason`, `deactivated_by` |
| `identity.membership.updated` | Identity | `identity` | Roles or tenant association modified | `principal_id`, `tenant_id`, `old_roles`, `new_roles`, `actor_id` |
| `identity.auth.failure` | Authentication | `identity` | Token expired, forged, or missing | `attempt_id`, `failure_code`, `source_ip`, `correlation_id` (NO tokens/passwords) |
| `identity.auth.success` | Authentication | `identity` | New authentication session issued | `principal_id`, `tenant_id`, `session_id`, `correlation_id` |
| `identity.authorization.denied` | Authorization | `identity` | Insufficient role, permission, or cross-tenant | `principal_id`, `tenant_id`, `resource`, `action`, `required_permission` |
| `identity.delegation.issued` | Delegation | `identity` | Delegation issued to AI agent | `delegation_id`, `delegator_id`, `tenant_id`, `task_id`, `capabilities`, `expires_at` |
| `identity.delegation.revoked` | Delegation | `identity` | Delegation revoked before expiry | `delegation_id`, `delegator_id`, `tenant_id`, `reason` |
| `identity.privileged_access.invoked` | Privileged | `identity` | Operator assumes system context | `actor_id`, `ticket_id`, `justification`, `duration_seconds` |
| `identity.break_glass.activated` | Privileged | `identity` | Emergency break-glass override activated | `actor_id`, `ticket_id`, `reason`, `affected_tenant_id` |
| `identity.policy.uncertainty_denied` | Resilience | `identity` | Dependency timeout/error causing deny | `principal_id`, `tenant_id`, `resource`, `action`, `error_detail` |
| `database.rls_violation.logged` | Tenancy | `database` | PostgreSQL RLS policy rejection | `tenant_id`, `table_name`, `attempted_operation`, `connection_id` |

### 2.1. Phase 07 Commercial Pilot & Operational Audit Events

| Event Type | Category | Emitting Module | Trigger / Condition | Required Payload Fields |
|---|---|---|---|---|
| `tenancy.provisioning.started` | Tenancy | `tenancy` | Tenant provisioning saga begun | `tenant_id`, `tier`, `requested_by` |
| `tenancy.lifecycle.activated` | Tenancy | `tenancy` | Tenant activation probe passed | `tenant_id`, `activated_at`, `verifier_id` |
| `tenancy.lifecycle.suspended` | Tenancy | `tenancy` | Tenant suspended by policy/admin | `tenant_id`, `reason_code`, `actor_id` |
| `tenancy.data.export_generated`| Tenancy | `tenancy` | Export archive generated & sealed | `tenant_id`, `export_id`, `manifest_hash`, `size_bytes` |
| `tenancy.data.deletion_completed`| Tenancy| `tenancy` | Cascade deletion purge completed | `tenant_id`, `purged_partitions`, `deletion_digest` |
| `compliance.legal_hold.applied`| Tenancy | `compliance`| Legal hold placed on tenant | `tenant_id`, `matter_id`, `counsel_id` |
| `identity.oidc.login_success` | IAM | `identity` | OIDC federation login succeeded | `tenant_id`, `sub`, `email_masked`, `mapped_roles` |
| `identity.oidc.token_replay` | Security | `identity` | Replay attack detected (duplicate JTI)| `tenant_id`, `jti`, `ip_address` |
| `identity.scim.user_deactivated`| IAM | `identity` | User disabled via SCIM push | `tenant_id`, `user_id`, `revoked_sessions` |
| `connector.activated` | Connector | `connectors` | Connector health check verified | `tenant_id`, `connector_id`, `provider`, `mode` |
| `connector.auth_expired` | Connector | `connectors` | Provider 401/403 or token revoked | `tenant_id`, `connector_id`, `provider` |
| `connector.schema_drift` | Connector | `connectors` | Incompatible schema drift detected | `tenant_id`, `connector_id`, `drift_class`, `quarantine_id`|
| `finops.quota.exceeded` | FinOps | `finops` | Tenant hard quota exceeded | `tenant_id`, `dimension`, `requested`, `limit` |
| `finops.reconciliation.completed`| FinOps| `finops` | Usage matched with provider bill | `tenant_id`, `cycle_id`, `variance_pct`, `status` |

---

## 3. Audit Event Envelope Schema

Every audit event is represented as an immutable record:

```python
@dataclass(frozen=True, slots=True)
class AuditEvent:
    event_id: str                      # Unique event identifier (evt_...)
    occurred_at: UtcDateTime           # UTC timestamp
    event_type: str                    # Dot-delimited canonical type
    tenant_id: TenantId | None         # Explicit tenant identifier (None if global system)
    actor_id: PrincipalId              # Originating principal (user, service, or system)
    actor_type: PrincipalType          # user, service_account, agent, system
    delegation_id: str | None          # Delegation reference if emitted by an agent
    resource: str                      # Target resource identifier or URI
    action: str                        # Executed or attempted action
    outcome: str                       # SUCCESS, DENIED, FAILED, TIMEOUT
    correlation_id: CorrelationId      # Request correlation identifier
    causation_id: str | None           # Upstream causing event ID
    details: dict[str, Any]            # Minimized, allowlisted event metadata
    previous_event_hash: str           # Cryptographic hash of preceding event (hash chain)
    event_hash: str                    # SHA-256(event_id + occurred_at + ... + previous_hash)
```

---

## 4. Privacy, Redaction, and Secret Prevention (`INV-AUD-002`, `NFR-PRV-001`)

1. **Strict Field Allowlist**: The `details` payload accepts only predefined scalar types and schema-validated keys. Arbitrary dictionary blobs are rejected.
2. **Forbidden Data Classes**:
   - Authentication credentials (passwords, bearer tokens, API keys, private keys, session secrets).
   - Raw model prompts and internal chain-of-thought traces.
   - Unredacted customer personal identifiable information (PII) such as payment numbers or government IDs.
3. **Automated DLP Sanitization**: An interceptor scans the payload against secret regexes before persistence. Any violation causes the append to be rejected and triggers a security alert.

---

## 5. Failure Behavior and Outage Resilience (`INV-REL-001`)

- **100% Unsampled**: Security, authentication, authorization, and privileged audit events are never sampled away (`NFR-OBS-002`).
- **Fail-Closed High-Risk Writes**: If the audit persistence layer is unavailable or encounters database errors:
  - All high-risk writes, privileged actions, and tool invocations MUST fail closed (`INV-REL-001`).
  - Read queries continue with an audit-degraded warning marker.
  - Returns HTTP 503 `AUDIT_PERSISTENCE_UNAVAILABLE`.
