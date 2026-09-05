# Approval and Safe Action Loop Specification

Status: Accepted Canonical Specification
Initiative: REVPILOT
Scope: Phase 06 — Approval and Safe Action Loop (Rails 14, 15, 16)
Owner: Security & Action Governance Architecture
Traceability: `INV-ACT-001..004`, `INV-IAM-001..002`, `INV-TEN-001..003`, `INV-WF-001..002`, `INV-SEC-001..003`, `INV-AUD-001..002`, `INV-COST-001`, `INV-PRV-001`, `INV-REL-001..002`, `NFR-SEC-001..002`, `NFR-DUR-001`, `NFR-REL-001..002`, `NFR-AUD-001`, `NFR-COST-001..002`, `NFR-OBS-001..002`, `AC-008`, `AC-009`, `AC-010`, `AC-011`, `AC-012`, `AC-013`, `ADR-0002`, `ADR-0003`, `ADR-0009`, `ADR-0012`
Approver: Duong Vinh (Repository Owner)
Version: v1.0
Last Reviewed Date: 2026-09-04

---

## 1. Principles of Governed Action Execution

In RevPilot AI, autonomous agents and decision optimizers never possess direct authority or network egress to execute physical actions against external third-party systems (`INV-ACT-001`, `INV-ACT-003`). Every operational side effect (e.g. issuing freight re-routing orders, customer credits, carrier SLA penalties) must traverse a governed, stateful, and audited approval-action loop.

### 1.1 Non-Negotiable Invariants
1. **Cryptographic Digest Binding (`AC-008`, `INV-ACT-002`)**: Every approval request computes a SHA-256 digest over the canonical payload, target set, estimated cost, policy version, and decision references. Any tampering, parameter modification, or target alteration invalidates the approval request immediately (`ERR_APPROVAL_DIGEST_MISMATCH`).
2. **Strict Human-in-the-Loop Authority (`INV-ACT-003`)**: AI agents, automated planners, and LLM evaluators are strictly prohibited from approving actions or signing approval requests. Only authenticated human principals possessing the required role and approval tier within the tenant may sign (`ERR_AGENT_SELF_APPROVAL`).
3. **Six-Point Continuous Revalidation (`AC-008`)**: Policy, authorization, data freshness, budget balance, and kill-switch states are evaluated continuously across 6 lifecycle milestones:
   1. *Prior to approval creation* (Decision Engine boundary).
   2. *Upon approval request submission* (Approval Service intake).
   3. *Upon human signature submission* (Human approver signing).
   4. *Immediately prior to dry-run execution* (Pre-flight safety check).
   5. *Immediately prior to physical dispatch* (Tool Gateway dispatch gate).
   6. *Post-provider result during reconciliation* (Audit & Ledger closure).
4. **Dry-Run Parity (`AC-009`)**: Prior to real execution, every action must execute in dry-run simulation mode through the identical validation and policy logic, returning simulated impact, cost, blast radius, and provider requirements with zero external side effects.
5. **No Blind Retries on UNKNOWN (`NFR-REL-001`)**: If a provider call times out, returns HTTP 500/504, or loses network connectivity after request transmission, the action ledger transitions to `UNKNOWN`. Blind automated retries are prohibited. The workflow transitions to reconciliation via provider query or operator escalation.
6. **No Production Side Effects by Default**: In development, staging, and initial pilot phases, production external adapters remain physically disabled and gated behind mock test harnesses (`INV-ACT-001`).

---

## 2. The 10-Stage Safe Action Lifecycle

```text
 ┌────────────────────────────────────────────────────────────────────────┐
 │ Stage 1: Recommendation Generated (Phase 05 Expected Utility Optimizer)│
 ├────────────────────────────────────────────────────────────────────────┤
 │ Stage 2: Policy & Pre-Flight Evaluation (Eligibility, Cooldown, Limits)│
 ├────────────────────────────────────────────────────────────────────────┤
 │ Stage 3: Approval Request Creation & SHA-256 Digest Sealing            │
 ├────────────────────────────────────────────────────────────────────────┤
 │ Stage 4: Human Approval / Rejection / Amendment (Tiered Authority)     │
 ├────────────────────────────────────────────────────────────────────────┤
 │ Stage 5: Pre-Execution Revalidation (Budget, Expiry, Freshness Check)  │
 ├────────────────────────────────────────────────────────────────────────┤
 │ Stage 6: Dry-Run Simulation (Deterministic Validation, Zero Mutation)  │
 ├────────────────────────────────────────────────────────────────────────┤
 │ Stage 7: Tool Gateway Dispatch (Kill-Switch Check, Rate Limit, Egress) │
 ├────────────────────────────────────────────────────────────────────────┤
 │ Stage 8: Action Ledger Recording (Idempotency Key, Request Digest)     │
 ├────────────────────────────────────────────────────────────────────────┤
 │ Stage 9: Provider Result Evaluation (Success / UNKNOWN / Saga Compens) │
 ├────────────────────────────────────────────────────────────────────────┤
 │ Stage 10: Action Outcome Measurement (Actual ARR Retention, ROI Audit) │
 └────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Data Contracts and State Schemas

### 3.1. Approval Request Record (`ApprovalRequestRecord`)
```python
class ApprovalStatus(str, Enum):
    DRAFT = "DRAFT"
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    AMENDED = "AMENDED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"
    SUPERSEDED = "SUPERSEDED"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    UNKNOWN = "UNKNOWN"
    RECONCILIATION_REQUIRED = "RECONCILIATION_REQUIRED"

class ApprovalRequestRecord(BaseModel):
    approval_id: UUIDv7
    tenant_id: TenantId
    decision_id: UUIDv7
    investigation_id: Optional[UUIDv7]
    action_type: str                       # E.g. "FREIGHT_CARRIER_EXPEDITE"
    action_version: str                    # E.g. "1.0.0"
    target_customer_id: str
    target_entity_refs: List[str]          # E.g. ["order_midwest_12345"]
    action_payload: Dict[str, Any]
    payload_digest: str                    # SHA-256 over canonical JSON payload
    policy_digest: str                     # SHA-256 over active policy rules
    estimated_cost_usd: Decimal
    reserved_budget_usd: Decimal
    risk_tier: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    required_approval_tier: int            # 1: Operations, 2: Director, 3: VP/Executive
    approver_principal_id: Optional[str] = None
    approval_timestamp: Optional[UtcDateTime] = None
    rejection_reason: Optional[str] = None
    expiry_time: UtcDateTime               # Max TTL 24 hours
    status: ApprovalStatus = ApprovalStatus.PENDING
    decision_digest: str
    correlation_id: UUIDv7
    causation_id: UUIDv7
    created_at: UtcDateTime
```

### 3.2. Action Intent Record (`ActionIntentRecord`)
```python
class ActionClassification(str, Enum):
    REVERSIBLE = "REVERSIBLE"              # Can be undone via exact inverse API
    COMPENSATABLE = "COMPENSATABLE"        # Cannot be undone; requires financial/credit compensation
    PARTIALLY_COMPENSATABLE = "PARTIALLY_COMPENSATABLE"
    IRREVERSIBLE = "IRREVERSIBLE"          # Cannot be undone or compensated (physical dispatch)
    MANUAL_RECONCILIATION = "MANUAL_RECONCILIATION"

class ActionIntentRecord(BaseModel):
    intent_id: UUIDv7
    tenant_id: TenantId
    approval_id: UUIDv7
    idempotency_key: str                   # Strict tenant-scoped idempotency key
    action_type: str
    classification: ActionClassification
    target_set_count: int
    payload_digest: str
    max_retries: int = 3
    timeout_seconds: int = 30
    is_dry_run: bool = False
    created_at: UtcDateTime
```

### 3.3. Action Ledger Record (`ActionLedgerRecord`)
```python
class ActionLedgerRecord(BaseModel):
    ledger_id: UUIDv7
    tenant_id: TenantId
    intent_id: UUIDv7
    attempt_number: int
    idempotency_key: str
    provider_name: str                     # E.g. "mock_carrier_logistics_v1"
    request_digest: str                    # SHA-256 over outbound HTTP body
    response_digest: Optional[str] = None  # SHA-256 over inbound HTTP response
    http_status_code: Optional[int] = None
    provider_tx_id: Optional[str] = None
    execution_status: Literal["SUCCESS", "PROVIDER_ERROR", "TIMEOUT_UNKNOWN", "RECONCILED", "COMPENSATED"]
    error_code: Optional[str] = None
    started_at: UtcDateTime
    completed_at: Optional[UtcDateTime] = None
```

---

## 4. Saga, Compensation, and Unknown Reconciliation

### 4.1. The UNKNOWN Result Protocol (`NFR-REL-001`)
When an outbound provider request suffers a network timeout or connection reset after byte transmission:
1. The action status transitions immediately to `UNKNOWN` in `ActionLedgerRecord`.
2. **Zero Blind Retries**: Automatic HTTP retry is prohibited to prevent duplicate financial or physical side effects.
3. The Temporal workflow schedules a deterministic `QueryProviderStatusActivity` using the `provider_idempotency_key`.
4. If status inquiry succeeds:
   - If provider confirmed transaction: Ledger updates to `SUCCESS`.
   - If provider has no record: Workflow marks previous attempt `FAILED_NO_DISPATCH` and safely retries.
5. If status inquiry remains inconclusive after 3 attempts (exponential backoff up to 15 minutes):
   - Status updates to `RECONCILIATION_REQUIRED`.
   - Outbox event `action.reconciliation_required.v1` is emitted to human SRE / Operations queue.

### 4.2. Saga Compensation Contract
For multi-step compound actions (e.g. Reserve Inventory -> Charge Surcharge -> Book Priority Courier):
- Each step registers a forward activity and a compensating activity.
- If step $K$ fails, steps $K-1, \dots, 1$ execute compensation activities in reverse order.
- Irreversible actions (`IRREVERSIBLE`) cannot participate in automated rollback; they require financial credit compensation or operator ticket creation.

---

## 5. Blast Radius and Multi-Tier Safety Kill Switches

### 5.1. Multi-Tier Kill Switch Taxonomy
Kill switches are independent of AI model logic, persist in PostgreSQL with Redis distributed cache, and enforce fail-closed blocking:

| Kill Switch Scope | Enforcement Target | Propagation Latency | Impact |
|---|---|---|---|
| **Tier 1: Global Platform** | All tenants, all tools | $< 500\text{ms}$ | Entire system enters read-only emergency state |
| **Tier 2: Tenant Level** | Target `tenant_id` | $< 500\text{ms}$ | All write actions for tenant halted |
| **Tier 3: Capability / Tool**| Specific `action_type` | $< 500\text{ms}$ | Only matching tool disabled across platform |
| **Tier 4: Provider Level** | Specific third-party API | $< 500\text{ms}$ | Reroutes or halts actions targeting failing provider |
| **Tier 5: Investigation** | Specific `investigation_id`| $< 500\text{ms}$ | Pauses actions stemming from suspected hallucination |

### 5.2. Blast-Radius Ceilings and Approval Tiers (`NFR-COST-001`, `ADR-0012`, `IAM-SPEC §7.1`)
1. **Per-Action Spend Ceiling & Tiered Authority**:
   - **Tier 1 (Operational)**: $\le \$250.00$ USD (`approval:tier_1`). Low-risk actions that have received authenticated human approval from an Operations Manager or Dispatch Supervisor. “Automated” describes downstream Tool Gateway dispatch after human sign-off; agent, planner, evaluator, or service-account self-approval is strictly forbidden (`INV-ACT-003`).
   - **Tier 2 (Tactical)**: $\le \$1,000.00$ USD (`approval:tier_2`). Requires Operations Director or Regional Logistics Lead approval.
   - **Tier 3 (Executive)**: $\le \$10,000.00$ USD (`approval:tier_3`). Requires VP Operations or Chief Operating Officer approval.
   - **Over-Ceiling Exception Escalation**: Actions with estimated cost exceeding USD 10,000.00 cannot be approved under Tier 3; they require an explicit executive board exception signed by the Chief Executive Officer.
2. **Max Affected Entities per Run**: Max 500 accounts/orders per incident. Larger batches require phased cohort releases.
3. **Credential Broker Token Lifetime (`ADR-0009`, `TOOL-GATEWAY-SPEC §7.2`)**: Tool Gateway dispatches utilize ephemeral, downscoped tokens with maximum 15-minute TTL.

