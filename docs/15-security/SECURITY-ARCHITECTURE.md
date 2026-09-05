# Security Architecture Specification (Rails 3–5 Security Control Mapping)

Status: Accepted Canonical Specification
Initiative: REVPILOT
Scope: Control Plane Security Architecture (Rails 3–5 Alignment)
Owner: Security Architecture
Traceability: `SEC-001..010`, `INV-SEC-001..003`, `INV-IAM-001..002`, `INV-TEN-001..003`, `INV-ACT-001..004`, `INV-REL-001`, `INV-AUD-001..002`, `NFR-SEC-001..002`, `NFR-TEN-001..002`, `ADR-0005`, `ADR-0009`
Approver: Duong Vinh (Repository Owner)
Version: v1.0
Last Reviewed Date: 2026-09-04

## Revision History

| Version | Date | Author | Reviewer | Approval | Summary of Changes |
|---|---|---|---|---|---|
| v1.0 | 2026-09-04 | Security Architecture | Principal Architect | Dương Vinh | Rails 3–5 control plane security mapping |

---

## 1. Security Philosophy and Boundaries

RevPilot operates on a zero-trust model where all incoming requests, user inputs, external documents, and model-generated outputs are untrusted by default. Authority, tenant context, and access permissions are established exclusively through verified server-side evaluations.

### Certification Disclaimer
RevPilot makes zero claims of formal security certification (e.g. SOC 2 Type II, ISO 27001, FedRAMP, HIPAA) at this stage. All security controls defined herein are internal architectural invariants and design obligations that must be proven through automated negative test matrices and operational telemetry.

---

## 2. Rails 3–5 Security Control Mapping

The following comprehensive control matrix maps every control plane security obligation to its owning component, applicable invariant, failure behavior, negative test suite, operational alert signal, and audit requirement:

| Control Name | Enforcing Component / Owner | Invariant / Objective | Failure Behavior | Negative Test Suite | Operational Signal / Alert | Mandatory Audit Event |
|---|---|---|---|---|---|---|
| **1. Authentication Trust Boundary** | `IdentityModule` / API Gateway Middleware | `INV-IAM-001`, `SEC-003` | Deny by default; return HTTP 401 `AUTHENTICATION_ERROR` | `test_authentication_negative.py` (missing/malformed/forged/expired tokens) | `identity.auth.failure_rate > 5%` | `identity.auth.failure` |
| **2. Server-Derived Tenant Context** | `IdentityModule` + `TenancyModule` | `INV-TEN-002`, `SEC-001` | Discard client headers; fail closed if tenant invalid/inactive (HTTP 403 `TENANCY_VIOLATION`) | `test_tenant_isolation_negative.py` (forged `X-Tenant-ID`, suspended tenant) | `identity.tenant.violation_count > 0` | `identity.auth.failure` |
| **3. Deny-by-Default Authorization** | `IdentityModule` (`AuthorizationService`) | `INV-IAM-001`, `SEC-003` | Block access; return HTTP 403 `AUTHORIZATION_DENIED` | `test_authorization_delegation_negative.py` (unauthorized role/permission) | `identity.authz.denial_rate > 2%` | `identity.authorization.denied` |
| **4. Delegated Agent Capability Bounds** | `IdentityModule` (`DelegationManager`) | `INV-IAM-002`, `SEC-002` | Reject delegation exceeding delegator scope; block expired/revoked delegation | `test_authorization_delegation_negative.py` (scope escalation, expired token) | `identity.delegation.escalation_attempt` | `identity.delegation.issued`, `identity.delegation.revoked` |
| **5. Autonomous Agent Credential Isolation** | `AgentRuntime` + `ToolGateway` | `INV-SEC-001`, `SEC-002` | Agent context receives zero credentials/tokens; Credential Broker brokers narrow access | `test_credential_isolation_negative.py` (context/log secret scanning) | `security.secret_in_context_detected` (P0 Alert) | `security.secret_broker.accessed` |
| **6. Untrusted Content Authority Neutralization** | Application Input Layer / Agent Prompts | `INV-SEC-002`, `SEC-004` | Prompts/documents cannot grant rights or modify policy rules; taint flags enforced | `test_injection_mitigation.py` (indirect prompt injection tests) | `security.prompt_injection_flagged` | `security.prompt_taint.detected` |
| **7. Multi-Tenant Storage Isolation** | PostgreSQL RLS + Composite Keys | `INV-TEN-001`, `SEC-001` | Query without context returns 0 rows; cross-tenant write raises RLS exception | `test_persistence_isolation_negative.py` (A/B cross-tenant query tests) | `database.rls_violation_count > 0` (P0 Alert) | `database.rls_violation.logged` |
| **8. Database Role Boundaries** | PostgreSQL Roles (`revpilot_app`, `revpilot_migrator`) | `INV-TEN-001`, `ADR-0004` | App role cannot alter DDL, drop tables, or bypass forced RLS | `test_database_role_privileges.py` (attempt DDL via app connection) | `database.permission_denied_error` | `database.unauthorized_ddl.attempted` |
| **9. Privileged Context & Break-Glass** | `IdentityModule` (`PrivilegedContextPolicy`) | `INV-TEN-003`, `SEC-001` | Reject null tenant; require dual authorization/ticket; enforce 60 min limit | `test_privileged_context_negative.py` (null tenant, unauthorized break-glass) | `identity.break_glass.invoked` (Immediate P0) | `identity.break_glass.activated` |
| **10. Fail-Closed Resilience Policy** | Global Middleware / Service Interceptors | `INV-REL-001`, `SEC-007` | On dependency outage, timeout, or ambiguity: 100% writes blocked, degraded reads only | `test_dependency_outage_matrix.py` (simulated auth/policy service outage) | `system.fail_closed_activated` | `identity.policy.uncertainty_denied` |
| **11. Immutable Security Audit Logging** | `AuditModule` (`AuditAppendPort`) | `INV-AUD-001`, `SEC-009` | If audit log append fails or integrity uncertain, block corresponding sensitive action | `test_audit_completeness_integrity.py` (tamper detection, append drop test) | `audit.append_failure_count > 0` (P0 Alert) | `audit.event.appended` |
| **12. Telemetry Privacy & Redaction** | Observability Interceptors / OpenTelemetry | `INV-AUD-002`, `NFR-PRV-001` | Secrets, passwords, raw prompts, and non-allowlisted PII redacted at source | `test_telemetry_redaction_negative.py` (secret injection into log parameters) | `telemetry.redaction_sanitizer_triggered` | None (telemetry is non-audit) |

---

## 3. Threat Model and Attack Vector Mitigations

### 3.1. Confused Deputy Attacks
- **Threat**: An attacker tricks an AI agent into using its system authority to access another tenant's data or perform unauthorized enterprise tool actions.
- **Mitigation**: Agents NEVER possess sovereign credentials or ambient permissions. An agent operates strictly under a `DelegationToken` that:
  1. Is strictly bound to the specific `tenant_id` and `investigation_id`.
  2. Whitelists permitted tools and specific target resources.
  3. Prohibits approval operations (`INV-ACT-003`).

### 3.2. Token Forgery and Signature Bypass
- **Threat**: An attacker fabricates an authentication token or modifies claims (e.g. escalating to `is_system=True` or altering `tenant_id`).
- **Mitigation**:
  1. Cryptographic signature verification is non-negotiable.
  2. Public verification keys are managed in a provider-neutral keystore.
  3. `is_system=True` requires verification against a restricted internal platform service account registry.

### 3.3. SQL Injection and Database RLS Circumvention
- **Threat**: Application logic flaw passes untrusted input into a SQL query, attempting to bypass tenant isolation.
- **Mitigation**:
  1. Parameterized queries only; raw SQL string formatting is prohibited.
  2. Composite primary and foreign keys include `tenant_id`.
  3. PostgreSQL Row-Level Security (`FORCE ROW LEVEL SECURITY`) is evaluated at the database engine level, independent of the query syntax.
  4. Session variable `revpilot.current_tenant_id` is set via `SET LOCAL` within a transaction and cleared on rollback/commit.

---

## 4. Operational Telemetry and Alert Ownership

| Alert Name | Severity | Owner | Condition | Playbook Action |
|---|---|---|---|---|
| `RLSViolationDetected` | P0 (Critical) | Security + Data Platform | Count > 0 in 1 min | Isolate connection, capture audit trace, page security on-call |
| `BreakGlassActivated` | P0 (Critical) | Security Incident Response | Invocation event emitted | Verify ticket authorization with requester manager |
| `SecretInTelemetryDetected` | P0 (Critical) | Security Platform | DLP / Redaction alert > 0 | Revoke detected credential immediately, purge log archive |
| `CrossTenantAttemptDetected` | P1 (High) | Tenancy + Security | HTTP 403 `TENANCY_VIOLATION` > 5 / min | Block offending IP/Principal, investigate potential breach attempt |
| `AuthFailureSpike` | P1 (High) | Identity Team | HTTP 401 > 10% total traffic | Check IdP connectivity, clock skew, or brute-force attack |

---

## 5. Phase 03 Read-Only Policy and Security Boundary

Phase 03 enforces a strictly read-only execution perimeter for all business operations and analytical queries.

### 5.1 Permitted Capabilities in Phase 03
1. **Registered Read-Only SQL Queries**: Bound strictly to `SQL-CAPABILITY-CATALOG.md`.
2. **Governed Hybrid Retrieval**: Bound strictly to `RAG-SPEC.md` with tenant/ACL/effective-date filtering.
3. **Ticket Intelligence Ingestion**: Sanitized, PII-masked support ticket analysis under `TICKET-INTELLIGENCE-SPEC.md`.
4. **Hypothesis Synthesis and Verification**: In-memory cognitive reasoning and citation verification under `MULTI-AGENT-SPEC.md`.
5. **Durable Workflow State Transitions**: Temporal internal lifecycle transitions without external side effects (`TEMPORAL-WORKFLOW-SPEC.md`).

### 5.2 Prohibited Capabilities in Phase 03 (`INV-ACT-001`, `SEC-001..004`)
The following actions are physically barred and blocked at the API, network, and gateway layers during Phase 03:
- External customer emails, notifications, or alerts.
- Payment initiation, refund processing, or financial ledger adjustments.
- CRM mutations (Salesforce, HubSpot record creation or updating).
- ERP/WMS mutations (NetSuite, fulfillment order alterations).
- Contract modifications or digital signature requests.
- Arbitrary network egress outside allowlisted internal endpoints.
- Raw database credentials access by Agent Runtime.
- Action execution or issuance of automated approval grants.

Any attempt by an agent or workflow to invoke an external write tool immediately raises `ERR_UNAUTHORIZED_PHASE03_MUTATION`, terminates the investigation task, and emits an immutable security audit event `security.phase03.mutation_blocked`.

### 5.1 Implementation-boundary findings (documentation status)

The following current-source observations are **implementation pending** and must not be described as resolved by this specification:

| Finding | Affected source boundary | Required implementation control | Required future evidence |
|---|---|---|---|
| Tenant lifecycle/context methods lack caller authorization | `modules/tenancy/service.py` | Require verified `SecurityContext`, membership and operation permission at every sensitive method | Unauthenticated/cross-tenant negative suite and audit decision log |
| `is_system` can be caller-constructed | `shared/context.py`, `modules/tenancy/ports/policy.py` | Opaque authentication factory, strict boolean validation and privileged registry verification | Forged-context and privilege-escalation tests |
| Context survives lifecycle revocation | `shared/context.py`, `domain/models.py` | Expiry, revocation/session version, and boundary revalidation | Suspend/deactivate reuse tests |
| Mutable aggregate state crosses caller boundary | `domain/models.py`, in-memory adapter | Immutable DTO/snapshot or copy-on-read plus persistence constraints | Aggregate mutation-isolation tests |
| Caller-supplied IDs can overwrite aggregates | tenancy service and in-memory adapter | Atomic create-if-absent and duplicate-ID rejection | Duplicate-ID/idempotency tests |

These findings are source-level security blockers. No network/API reachability is claimed because the production API boundary is not implemented in the current repository.

---

## 6. Phase 04 Causal and Verifier Security Boundary

Phase 04 governs statistical causal inference, competing hypothesis ranking, and deterministic claim verification. It enforces 6 strict security boundaries:

### 6.1. Tenant Isolation in Causal Studies (`INV-TEN-001..003`)
- Every `CausalStudy` is bound to server-derived `TenantContext` injected from authenticated JWT claims.
- Queries for treatment, outcome, and pre-treatment covariates execute with `SET LOCAL revpilot.current_tenant_id = :tenant_id` and strict PostgreSQL RLS. Cross-tenant pooling or estimation is physically impossible.

### 6.2. Ground-Truth Schema Air-Gap (`INV-DATA-001`, `AC-014`)
- Ground-truth tables (`ground_truth.incidents`, `ground_truth.dgp_parameters`) are owned by database role `revpilot_evaluator`.
- Application and agent runtime role `revpilot_app` has explicit `REVOKE ALL ON SCHEMA ground_truth FROM revpilot_app`.
- Any runtime query attempting to read hidden ground truth raises SQL error 42501 `insufficient_privilege`.

### 6.3. Untrusted Input Containment and Prompt Injection Defense (`INV-SEC-002`)
- Causal questions, hypotheses, and evidence text are framed inside `<untrusted_document>` or `<untrusted_claim>` delimiters.
- Untrusted text cannot alter causal DAG specifications, estimand definitions, or covariate selection sets.

### 6.4. Zero Action Escalation (`INV-ACT-001`)
- Causal estimates quantify retrospective attribution or theoretical counterfactuals.
- Causal point estimates, confidence intervals, and hypothesis ranking scores cannot trigger automated interventions, authorize financial refunds, or modify customer records.

### 6.5. Privacy Minimization and PII Redaction in Covariates (`INV-PRV-001`)
- Pre-treatment covariates are limited to aggregated dimensions, categorical tiers, and numeric totals.
- Direct identifiers (customer names, emails, phone numbers, payment card PANs) are barred from covariate matrices.

### 6.6. Audit Logging without Secret / Payload Leakage (`INV-AUD-001..002`)
- Audit events record SHA-256 hashes of study specifications (`study_digest`), row counts, runtime duration, and estimator hyperparameters.
- Raw customer data, prompt tokens, and proprietary model parameters are never serialized into audit ledgers.

---

## 7. Phase 07 Secrets, Keys, and Connector Credential Lifecycle (`ADR-0009`)

Phase 07 governs secret references, key management, connector credentials, and workload identity boundaries across multi-tenant pilot environments.

### 7.1. Credential Broker and Workload Identity Boundary (`INV-SEC-001`)
- **Zero Raw Secrets in Agent Runtime**: AI agents and Temporal workflow histories NEVER receive or store raw passwords, API keys, OAuth tokens, or private certificates. Agents handle only opaque, immutable `SecretReference` identifiers.
- **Short-Lived Downstream Credentials**: When external systems are queried or dispatched via the Tool Gateway, the `CredentialBroker` exchanges tenant workload identity for short-lived, least-privilege tokens with a maximum **15-minute** lifetime. This is the canonical dispatch-credential bound; older 60-minute wording is superseded by `DOCUMENTATION-CLOSURE-DECISIONS.md`.
- **Scope & Audience Containment**: Every issued credential is explicitly constrained by tenant ID, connector ID, permitted action scope, and target provider audience. Unrestricted or wildcard credentials are strictly prohibited.

### 7.2. Secret Versioning, Key Wrapping, and Rotation Lifecycle
1. **Secret Envelope and Wrapping**: Secrets stored at rest are encrypted via authenticated envelope encryption (`AES-256-GCM` or cloud-managed KMS). Data encryption keys (DEKs) are wrapped with key-encrypting keys (KEKs) partitioned per tenant tier.
2. **Dual-Version Zero-Downtime Rotation**:
   - Secret store maintains `version` (active) and `previous_version` (grace period).
   - Rotation triggers automated validation against the external provider before promoting the new version to `ACTIVE`.
   - If validation fails, rotation aborts, raises `FAILED_SECRET_ROTATION`, leaves existing version intact, and alerts the tenant administrator.
3. **Revocation and Session Purge**: Revoking a connector secret or IdP client secret immediately invalidates all active broker cached tokens within 1000ms.

### 7.3. Failure Modes and Fail-Closed Guardrails (`INV-REL-001`)
- **Secret Service Outage**: If the secret management service or KMS is unreachable or times out, all connector syncs and external actions FAIL CLOSED immediately with error `SECRET_BROKER_UNAVAILABLE` (503). No fallback to insecure or cached plaintext is permitted.
- **Expired / Revoked Credentials**: Any connector invocation with an expired or revoked credential halts execution, transitions the connector state to `AUTH_EXPIRED`, and emits an audit alert.
- **Provider Capability Gaps**: Where an external provider does not support short-lived OAuth tokens and requires long-lived API keys, the `CredentialBroker` isolates the key inside an egress enclave proxy; the connector worker communicates only with the proxy.

### 7.4. CMEK and Cloud Provider Neutrality
- Tenant-specific Customer Managed Encryption Keys (CMEK) and cloud-specific KMS integrations remain flagged as `UNKNOWN` until deployment cloud selection is approved (`ADR-0009`). The architecture provides provider-neutral `SecretProvider` and `KeyManagementPort` interfaces.
