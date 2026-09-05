# IAM and Delegation Specification (Rail 3 & Rail 4 Canonical Contract)

Status: Accepted Canonical Specification
Initiative: REVPILOT
Rails: Rail 3 (Authentication) & Rail 4 (Authorization and Delegation)
Owner: Security Architecture / Identity Module
Traceability: `INV-IAM-001`, `INV-IAM-002`, `INV-TEN-002`, `INV-TEN-003`, `INV-SEC-001`, `INV-SEC-002`, `INV-REL-001`, `NFR-SEC-001`, `NFR-SEC-002`, `ADR-0001`, `ADR-0005`, `ADR-0009`
Approver: Duong Vinh (Repository Owner)
Version: v1.0
Last Reviewed Date: 2026-09-04

## Revision History

| Version | Date | Author | Reviewer | Approval | Summary of Changes |
|---|---|---|---|---|---|
| v1.0 | 2026-09-04 | Security Architecture | Identity Leads | Dương Vinh | Canonical IAM and delegation model specification |

---

## 1. Executive Summary and Architectural Invariants

This document defines the canonical specification for identity authentication (Rail 3) and authorization/delegation (Rail 4) within RevPilot AI. It establishes mathematical rigor, fail-closed defaults, and provider-neutral boundaries.

### Architectural Invariants
1. `INV-IAM-001`: Authorization is deny-by-default and server-side at every sensitive capability boundary.
2. `INV-IAM-002`: Delegated Agent Identity is tenant/task/time scoped and cannot exceed its delegating Principal.
3. `INV-TEN-002`: Tenant context is server-derived from authenticated membership and cannot be supplied/overridden by client or model payload.
4. `INV-TEN-003`: Global/platform operations use an explicit privileged context, never `tenant = null` or implicit bypass.
5. `INV-SEC-001`: Agent Runtime never receives reusable connector/model/enterprise credentials.
6. `INV-SEC-002`: Documents, tickets, websites, model/tool outputs are untrusted content and cannot grant authority or override policy.
7. `INV-REL-001`: IAM/Policy/Audit uncertainty fails closed for writes; degraded reads are explicit and cannot authorize action.

---

## 2. Authentication Specification (Rail 3)

### 2.1. Principal Model and Types
An authenticated actor is modeled as a verified `Principal` aggregate root with an immutable `PrincipalId`.

```python
class PrincipalType(str, Enum):
    USER = "user"                      # Human interactive user
    SERVICE_ACCOUNT = "service_account"# Machine-to-machine service principal
    AGENT = "agent"                    # Delegated AI agent actor
    SYSTEM = "system"                  # Internal platform maintenance worker
```

### 2.2. Authentication Claims Normalization
External authentication assertions (e.g. JWT tokens, mutual TLS assertions, session envelopes) are normalized into an immutable `AuthTokenClaims` value object before any domain processing:

- `sub` (`str`): Subject identifier (prefixed, e.g. `usr_...`, `svc_...`, `agt_...`). Non-empty string.
- `iss` (`str`): Token issuer identifier. Must match trusted issuer registry.
- `aud` (`str`): Target audience. Must strictly match the RevPilot platform audience identifier (`revpilot-api`).
- `exp` (`UtcDateTime`): Expiration timestamp in UTC.
- `nbf` (`UtcDateTime | None`): Not-before timestamp in UTC.
- `iat` (`UtcDateTime`): Issued-at timestamp in UTC.
- `tenant_id` (`str | None`): Associated tenant identifier string. Required for all non-system actors (`INV-TEN-003`).
- `roles` (`frozenset[str]`): Verified assigned role names.
- `permissions` (`frozenset[str]`): Verified fine-grained permissions.
- `email` (`str | None`): User email address (human users only).
- `is_system` (`bool`): Internal privilege marker. It is never accepted directly from a caller, deserializer, client header, or unverified claims object. Only the verified authentication factory may construct a privileged principal after signature, issuer/audience, service-account registry, ticket/justification and audit checks.

### 2.3. Token and Session Validation Rules
1. **Clock Skew Policy**: Maximum allowable clock skew is 60 seconds. Evaluation:
   - Expired check: `as_of >= (claims.exp + 60s)` raises `AuthenticationError(AUTHENTICATION_ERROR, "Token has expired")`.
   - Not yet active check: If `claims.nbf` is present and `as_of < (claims.nbf - 60s)`, raises `AuthenticationError(AUTHENTICATION_ERROR, "Token not yet active")`.
2. **Issuer & Audience**: Any token where `iss != expected_issuer` or `aud != expected_audience` is immediately rejected with `AuthenticationError(AUTHENTICATION_ERROR, "Invalid token issuer or audience")`.
3. **Cryptographic Signature**: Signature verification is mandatory. Unsigned tokens, malformed headers, or invalid signatures raise `AuthenticationError(AUTHENTICATION_ERROR, "Invalid token signature")`.
4. **Tenant Binding**:
   - If `claims.is_system is False`: `claims.tenant_id` MUST be present and parse as a valid `TenantId`. If missing, raises `TenancyViolationError(TENANCY_VIOLATION, "Principal lacks required tenant association")`.
   - If verified privileged claims resolve to a registered platform service account: `tenant_id` may be omitted only inside an opaque `PrivilegedContext` created by the authentication factory. A plain `PrincipalContext(is_system=True)` constructed by application code is invalid.
5. **Revocation & Logout**:
   - Token revocation lists and active session version numbers are checked at authentication verification.
   - Revoked sessions/tokens fail closed with `AuthenticationError(AUTHENTICATION_ERROR, "Token or session has been revoked")`.
   - Nonce/JTI reuse within validity window triggers immediate rejection as replay attack.

### 2.4. Server-Derived Context Resolution
Client-supplied headers such as `X-Tenant-ID` or payload tenant fields are strictly untrusted. Tenant association is derived exclusively from verified cryptographic claims and active tenant status:
- Tenant status must be `ACTIVE` in `TenancyService`. If suspended or deactivated, context resolution fails closed with `TenancyViolationError`.

### 2.5. Provider-Neutral Architecture Boundary
RevPilot does not store raw passwords, does not implement custom password hashing, and does not hard-code any specific third-party identity provider (IdP). Authentication is mediated via `AuthenticationPort`:
- The domain and application layers consume `AuthenticationPort` and verified `Principal` entities.
- Concrete adapters (e.g. `InMemoryAuthAdapter` for testing, OIDC/OAuth2/mTLS adapters for infrastructure) implement `AuthenticationPort`.
- Under no circumstances does raw credential data reach the Agent Runtime (`INV-SEC-001`).

---

## 3. Authorization and Delegation Specification (Rail 4)

### 3.1. Hybrid RBAC/ABAC Model
RevPilot implements a hybrid model:
1. **RBAC (Role-Based Access Control)** provides coarse-grained capability groupings.
2. **ABAC (Attribute-Based Access Control)** provides fine-grained contextual constraints (tenant isolation, resource ownership, temporal boundaries, classification).

### 3.2. Role Hierarchy and Roles
Standard platform and tenant roles:
- `platform_admin`: Cross-tenant administration and break-glass operations (requires `is_system=True`).
- `tenant_admin`: Tenant user management, settings, billing configuration.
- `analyst`: Read investigations, execute analytical queries, view evidence.
- `operator`: Initiate investigations, request tool actions, approve eligible low-risk proposals.
- `auditor`: Read-only access to audit logs, compliance reports, and integrity checkpoints.
- `agent_delegate`: Scoped execution identity for AI agents running within an approved workflow.

### 3.3. Permission and Resource Model
Permissions use the canonical format: `resource:action`.
Examples:
- `investigation:read`, `investigation:create`, `investigation:cancel`
- `evidence:read`, `evidence:attach`
- `tool:invoke`, `tool:read`
- `policy:evaluate`, `approval:request`, `approval:grant`
- `audit:read`, `tenant:manage`

### 3.4. Role-Permission Matrix

| Role | Permissions |
|---|---|
| `platform_admin` | `*` (scoped by explicit audit and break-glass justification) |
| `tenant_admin` | `tenant:manage`, `user:manage`, `investigation:*`, `evidence:*`, `audit:read`, `policy:read` |
| `operator` | `investigation:create`, `investigation:read`, `evidence:read`, `tool:invoke`, `approval:request` |
| `analyst` | `investigation:read`, `evidence:read`, `analytics:read`, `audit:read` |
| `auditor` | `audit:read`, `compliance:read`, `investigation:read`, `evidence:read` |
| `agent_delegate` | strictly defined subset of delegator permissions; maximum: `investigation:read`, `evidence:read`, `tool:invoke` (subject to tool whitelist) |

### 3.5. Delegation Model and Constraints (`INV-IAM-002`)
A `DelegationToken` represents a constrained, time-bound transfer of authority from a human principal to an AI agent:

Attributes:
- `delegation_id` (`str`): Unique delegation reference (`del_...`).
- `delegator_id` (`PrincipalId`): The human principal issuing the delegation.
- `tenant_id` (`TenantId`): Strict tenant binding.
- `task_id` (`str`): The specific investigation or workflow task ID.
- `allowed_capabilities` (`frozenset[str]`): Whitelist of permitted capability actions.
- `target_resources` (`frozenset[str]`): Whitelist of resource IDs or resource prefixes.
- `issued_at` (`UtcDateTime`): Creation timestamp in UTC.
- `expires_at` (`UtcDateTime`): Short-lived expiration (maximum 24 hours).
- `revocation_version` (`int`): Revocation epoch counter.

#### Mandatory Delegation Invariants
1. **Never Exceeds Delegator**: `allowed_capabilities` must be a strict subset of the delegator's active permissions. Any attempt to request capabilities outside the delegator's roles is rejected as privilege escalation (`AuthorizationError`).
2. **No Credential Grant**: A delegation token never grants API keys, secrets, or raw connection strings (`INV-SEC-001`).
3. **No Approval Authority**: An agent delegate CANNOT approve actions, modify policy, or grant approval to itself or other agents (`INV-ACT-003`). Approvals strictly require a non-agent human `Principal`.
4. **No Unrestricted Access**: Delegation tokens MUST have an explicit `expires_at` and non-empty `allowed_capabilities`. Wildcard capabilities (`*`) are prohibited.
5. **Rechecked at Every Capability Boundary**: Capability calls (Tool Gateway, RAG query, database read) validate the active delegation token and fail closed on expiration or revocation.

### 3.6. Privileged Platform Context and Break-Glass (`INV-TEN-003`)
- Platform-level operations (cross-tenant maintenance, system migrations) require an explicit `PrivilegedContext`.
- Setting `tenant = None` or bypassing tenant checks in normal workflows is strictly forbidden.
- Break-glass procedures:
  - Must specify human requester ID, emergency ticket ID, and business justification.
  - Time-bounded to a maximum of 60 minutes.
  - Automatically emits high-priority, unsampled audit event `identity.break_glass.activated`.
  - Autonomous agents are structurally prohibited from activating or holding break-glass context.

### 3.7. Authorization Enforcement and Policy Uncertainty (`INV-REL-001`)
- Enforcement happens at the entry of every application service and Tool Gateway adapter.
- **Fail-Closed Rule**: If the authorization engine encounters any error, database timeout, ambiguous policy rule, or corrupted delegation record:
  - ALL writes and actions are 100% blocked (`INV-REL-001`).
  - Read queries fail closed unless an explicit, non-authorizing degraded read mode is configured.
  - Error code returned: `AUTHORIZATION_DENIED` (403).

---

## 4. Audit and Observability Contracts

### 4.1. Mandatory Audit Events
Every identity and access event emits an immutable audit event conforming to `docs/22-billing/AUDIT-LOG-SPEC.md` and `INV-AUD-001`:

| Event Type | Trigger | Required Fields |
|---|---|---|
| `identity.principal.created` | New user/service account provisioned | `principal_id`, `type`, `tenant_id`, `actor_id` |
| `identity.principal.deactivated` | User/service account disabled | `principal_id`, `tenant_id`, `reason`, `actor_id` |
| `identity.membership.updated` | Roles or tenant association changed | `principal_id`, `tenant_id`, `old_roles`, `new_roles`, `actor_id` |
| `identity.auth.failure` | Missing, expired, forged, or revoked token | `attempt_id`, `failure_reason`, `source_ip`, `correlation_id` (NO credentials) |
| `identity.auth.success` | Successful authentication session | `principal_id`, `tenant_id`, `session_id`, `correlation_id` |
| `identity.authorization.denied` | Permission denied or cross-tenant attempt | `principal_id`, `tenant_id`, `resource`, `action`, `required_permission` |
| `identity.delegation.issued` | Agent delegation issued | `delegation_id`, `delegator_id`, `tenant_id`, `task_id`, `expires_at`, `capabilities` |
| `identity.delegation.revoked` | Agent delegation revoked early | `delegation_id`, `delegator_id`, `tenant_id`, `reason` |
| `identity.break_glass.activated` | Emergency privileged access assumed | `actor_id`, `ticket_id`, `justification`, `duration_seconds` |
| `identity.policy.uncertainty_denied`| Policy failure/timeout resulting in deny | `principal_id`, `tenant_id`, `resource`, `action`, `failure_detail` |

### 4.2. Sensitive Data Redaction (`INV-AUD-002`, `NFR-PRV-001`)
- Under no circumstances are raw JWT tokens, API keys, session secrets, or passwords logged in audit records or operational telemetry.
- Telemetry labels must be low-cardinality and exclude personally identifiable information (PII).

---

## 5. Stable Error Codes

| Code | HTTP Status | Description |
|---|---:|---|
| `AUTHENTICATION_ERROR` | 401 | Missing, malformed, forged, or invalid signature token |
| `TOKEN_EXPIRED` | 401 | Token expiration timestamp `exp` has passed |
| `TOKEN_NOT_YET_VALID` | 401 | Current time is before `nbf` timestamp |
| `TOKEN_REVOKED` | 401 | Token or session has been explicitly revoked |
| `TENANCY_VIOLATION` | 403 | Principal lacks required tenant or attempted cross-tenant breach |
| `AUTHORIZATION_DENIED` | 403 | Principal or agent lacks required role, permission, or scope |
| `DELEGATION_EXPIRED` | 403 | Agent delegation token expiration timestamp has passed |
| `DELEGATION_REVOKED` | 403 | Agent delegation token has been revoked |
| `DELEGATION_SCOPE_EXCEEDED` | 403 | Agent requested capability outside delegation or delegator scope |
| `VALIDATION_ERROR` | 400 | Malformed claim envelope or schema invalidity |

---

## 6. Comprehensive Verification and Test Matrix

The test suite must enforce positive and negative test cases with 100% automated verification:

| Scenario | Input / Trigger | Expected Outcome | Exit Gate Check |
|---|---|---|---|
| **Missing Token** | Unauthenticated request | Rejects with `AUTHENTICATION_ERROR` (401) | Rail 3 Gate |
| **Malformed Token** | Non-base64 or invalid JSON structure | Rejects with `VALIDATION_ERROR` / `AUTHENTICATION_ERROR` | Rail 3 Gate |
| **Forged Signature** | Tampered claims or wrong signature key | Rejects with `AUTHENTICATION_ERROR` (401) | Rail 3 Gate |
| **Wrong Issuer/Audience** | Valid signature, but `iss != expected` or `aud != expected` | Rejects with `AUTHENTICATION_ERROR` (401) | Rail 3 Gate |
| **Expired Token** | `as_of >= exp + 60s` | Rejects with `TOKEN_EXPIRED` / `AUTHENTICATION_ERROR` (401) | Rail 3 Gate |
| **Not Yet Active Token** | `as_of < nbf - 60s` | Rejects with `TOKEN_NOT_YET_VALID` / `AUTHENTICATION_ERROR` (401) | Rail 3 Gate |
| **Revoked Session** | Valid token but session in revocation store | Rejects with `TOKEN_REVOKED` / `AUTHENTICATION_ERROR` (401) | Rail 3 Gate |
| **Missing Tenant Association**| Non-system user without `tenant_id` | Rejects with `TENANCY_VIOLATION` (403) | Rail 3 Gate |
| **Cross-Tenant Access** | Principal of Tenant A accesses Tenant B resource | Rejects with `TENANCY_VIOLATION` (403) | Rail 4 Gate |
| **Privilege Escalation** | Role `analyst` calls `tool:invoke` | Rejects with `AUTHORIZATION_DENIED` (403) | Rail 4 Gate |
| **Expired Delegation** | Agent uses delegation where `as_of >= expires_at` | Rejects with `DELEGATION_EXPIRED` (403) | Rail 4 Gate |
| **Revoked Delegation** | Agent uses revoked delegation token | Rejects with `DELEGATION_REVOKED` (403) | Rail 4 Gate |
| **Delegation Exceeds Delegator**| Delegator has `analyst`; attempts to delegate `tool:invoke` | Rejects issuance with `DELEGATION_SCOPE_EXCEEDED` (403) | Rail 4 Gate |
| **Agent Approval Attempt** | Agent identity calls `approval:grant` | Rejects with `AUTHORIZATION_DENIED` (403) | Rail 4 Gate |
| **Break-Glass Misuse** | Non-human or unauthenticated break-glass request | Rejects with `AUTHORIZATION_DENIED` (403) | Rail 4 Gate |
| **Policy Uncertainty** | Dependency timeout during permission evaluation | Fails closed: 100% writes blocked, returns 403 | Rail 4 Gate |

---

## 7. Phase 06 Approval Authority, Tiered Delegation, and Separation of Duties

### 7.1. Approval Authority Tiers (`INV-ACT-003`)
Approval grants require explicit human authentication with tiered authorization scopes:

| Approval Tier | Required Scope | Maximum Spend Limit | Eligible Principal Roles |
|---|---|---|---|
| **Tier 1 (Operational)** | `approval:tier_1` | $\le \$250.00$ USD | Operations Manager, Dispatch Supervisor |
| **Tier 2 (Tactical)** | `approval:tier_2` | $\le \$1,000.00$ USD | Operations Director, Regional Logistics Lead |
| **Tier 3 (Executive)** | `approval:tier_3` | $\le \$10,000.00$ | VP Operations, Chief Operating Officer |

Amounts above USD 10,000 require a separately approved exception policy and cannot be silently treated as Tier 3.

### 7.2. Separation of Duties and Agent Exclusion (`INV-ACT-003`)
1. **Agent Self-Approval Barred**: Delegation tokens granted to AI agents strictly forbid `approval:*` scopes. Any attempt by an agent principal to approve an action fails closed with `ERR_AGENT_SELF_APPROVAL` (403).
2. **Proposer Disqualification**: The human principal who triggered or proposed an action investigation cannot sign as its sole approver if spend $> \$250.00$. Dual authorization is enforced.
3. **Six-Point Continuous Revalidation**: The authorization service revalidates the approver's active session, tenant membership, and revocation status at all 6 lifecycle checkpoints before Tool Gateway dispatch.

---

## 8. Phase 07 Enterprise Identity Federation (OIDC, SAML, SCIM)

Full protocol specifications, claim mapping schemas, and token validation rules are specified in `docs/14-iam/ENTERPRISE-IDENTITY-INTEGRATION-SPEC.md`.

1. **Protocol Sequencing**:
   - Baseline Pilot: OpenID Connect (OIDC) with Authorization Code Flow and mandatory PKCE (`S256`), cryptographic state verification, and nonce binding.
   - Enterprise Legacy: SAML 2.0 Web Browser SSO profile with signed assertions (`SHA-256`+), XSW mitigation, and dual-certificate rotation.
   - Lifecycle Automation: SCIM 2.0 endpoints for just-in-time and automated batch user provisioning, role group mapping, and rapid deprovisioning (`active: false`).
2. **Key Security Guarantees**:
   - Zero Password Storage: RevPilot never stores human passwords or raw IdP client secrets.
   - Server-Derived Tenancy (`INV-TEN-002`): Tenant binding is derived exclusively from IdP domain claims or tenant administrative mapping; client-supplied tenant headers are discarded.
   - Agent Isolation (`INV-SEC-001`): External IdP tokens or session keys never enter the Agent Runtime. Agents operate strictly on internal scoped delegation tokens.
   - Rapid Session Invalidation: SCIM deprovisioning or OIDC back-channel logout revokes all active sessions and pending approvals within 1000ms.
