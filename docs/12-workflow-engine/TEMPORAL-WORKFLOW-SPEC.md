# Temporal Investigation Workflow Specification

Status: Accepted Canonical Specification
Initiative: REVPILOT
Scope: Phase 03 — Governed Evidence and Investigation (Rails 6–7)
Owner: Workflow Engine Architecture / Platform Engineering
Traceability: `INV-WF-001`, `INV-WF-002`, `INV-TEN-001..003`, `INV-IAM-001..002`, `INV-REL-001..002`, `INV-COST-001`, `INV-AUD-001`, `INV-PRV-001`, `NFR-DUR-001`, `NFR-REL-001..002`, `NFR-OBS-001`, `FR-INV-001..003`, `AC-003`, `ADR-0002`, `ADR-0003`

---

## 1. Executive Summary and Architectural Principles

Temporal owns durable business sequencing, timers, retries, cancellation, compensation, and state history for RevPilot AI investigations. The Agent Runtime owns bounded, typed reasoning exclusively inside Activities.

### Core Invariants
1. **Durable Workflow State (`INV-WF-001`)**: Business workflow state lives in Temporal history and PostgreSQL projection tables; ephemeral agent memory is discarded after activity execution.
2. **Deterministic Workflow Logic (`INV-WF-002`)**: Workflow definitions are strictly deterministic. All network I/O, database access, model inference, clock reads, and UUID generation occur strictly inside Activities.
3. **No Phase 03 External Side Effects (`INV-ACT-001`)**: Phase 03 workflow execution is strictly read-only regarding external enterprise systems. Only internal evidence collection, read-only analytics, and verification transitions are permitted. Write paths to external systems are disabled.
4. **Server-Derived Tenant & Identity Context (`INV-TEN-002`, `INV-IAM-001`)**: Workflows receive trusted `TenantContext` and `PrincipalContext` at initiation. Workflows fail closed immediately upon missing, malformed, or mismatched context.
5. **Bounded Budgets (`INV-COST-001`, `NFR-COST-001`)**: Every investigation enforces time, token, and monetary cost ceilings before scheduling downstream activities.

### 1.1 Non-Goals (MVP / v1 Scope)
- **Arbitrary Long-Running Process State in Web API Memory**: In-memory async tasks or uncoordinated background threads within HTTP server process memory are prohibited; all orchestration must run through Temporal.
- **Direct Agent Mutating Side Effects inside Workflow Context**: LLM agents cannot directly perform external database or API mutations from workflow code; all mutations require audited activity execution and human approval.
- **Unconstrained Dynamic Sub-Workflow Spawning**: Spawning unmetered or unbounded recursive sub-workflows without budget reservation is strictly prohibited (`INV-COST-001`).

---

## 2. Workflow Identity and Isolation

### 2.1 Workflow ID Structure
Temporal workflow IDs follow an immutable, tenant-prefixed canonical format:
```text
tenant/{tenant_id}/investigation/{investigation_id}
```
- `tenant_id`: Canonical UUIDv7 string of the tenant.
- `investigation_id`: Canonical UUIDv7 string of the investigation.

Cross-tenant workflow execution is physically impossible: the workflow task queue and activity task queues are scoped per environment, and activity inputs require matching `tenant_id` validation before execution.

### 2.2 Task Queue Partitioning
- Main Investigation Workflow Queue: `investigation-workflow-queue`
- Read-Only Analytics Activity Queue: `investigation-analytics-activity-queue`
- Governed Retrieval Activity Queue: `investigation-retrieval-activity-queue`
- Agent Inference Activity Queue: `investigation-agent-activity-queue`

---

## 3. Workflow Input Contract

`InvestigationWorkflowInput` is immutable upon workflow initiation:

```python
class InvestigationWorkflowInput:
    investigation_id: UUIDv7
    tenant_id: TenantId
    principal_id: PrincipalId
    correlation_id: CorrelationId
    causation_id: CausationId
    trigger_type: Literal["SCHEDULED_DETECTOR", "ANOMALY_ALERT", "ANALYST_REQUEST"]
    anomaly_id: Optional[AnomalyId]          # Present if triggered by detector
    metric_name: str                         # Must match registered metric
    investigation_scope: Dict[str, Any]      # E.g. {"region": "US-EAST", "tier": "ENTERPRISE"}
    window_start: UtcDateTime
    window_end: UtcDateTime
    as_of_time: UtcDateTime                  # Time-travel baseline for queries
    time_budget_seconds: int = 300           # Default 5 minutes
    cost_budget_usd: Decimal = Decimal("2.00") # Hard ceiling USD 5.00
    tool_call_budget: int = 20
    workflow_version: str = "v1.0"
```

Validation rules:
- `tenant_id` must match authenticated session claim;
- `window_start < window_end <= as_of_time`;
- `cost_budget_usd <= Decimal("5.00")`;
- Missing fields cause workflow to reject before first activity schedule (`TERMINAL_INVALID_INPUT`).

---

## 4. State Machine and Lifecycle

```text
       [INITIALIZING]
             │
             ▼
        [PLANNING] ──(Validation Failed / Budget Exceeded)──► [FAILED]
             │
             ▼
    [GATHERING_EVIDENCE] ◄───┐
             │               │ (Need More Evidence / Loop <= 2)
             ▼               │
        [VERIFYING] ─────────┘
             │
             ├──(Evidence Confirmed)──► [COMPLETED]
             ├──(Evidence Gap)────────► [NEED_MORE_EVIDENCE]
             └──(Budget / Timeout)───► [FAILED]

    At any active state:
       ──(PauseSignal)───────────────► [PAUSED] ──(ResumeSignal)──► [Prior State]
       ──(CancelSignal / Timeout)────► [CANCELLED]
```

### State Definitions
| State | Owning Component | Precondition | Permitted Next States | Failure Behavior |
|---|---|---|---|---|
| `INITIALIZING` | Workflow Orchestrator | Input validated | `PLANNING`, `FAILED` | Emit audit event; transition to `FAILED` |
| `PLANNING` | Planner Agent Activity | State `INITIALIZING` | `GATHERING_EVIDENCE`, `FAILED`, `CANCELLED` | If planner fails/times out, return `FAILED` |
| `GATHERING_EVIDENCE` | Parallel Activity Dispatcher | Valid typed DAG | `VERIFYING`, `PAUSED`, `CANCELLED`, `FAILED` | Failed activity logged; if critical, fail closed |
| `VERIFYING` | Verifier Activity | Evidence gathered | `COMPLETED`, `NEED_MORE_EVIDENCE`, `GATHERING_EVIDENCE`, `FAILED` | Contradiction or lack of support -> `NEED_MORE_EVIDENCE` |
| `NEED_MORE_EVIDENCE` | Terminal / Human Escalate | Hypotheses incomplete | None (Terminal in Phase 03) | Preserves partial evidence and explicit gap report |
| `COMPLETED` | Workflow Orchestrator | Verifier PASS | None (Terminal) | Manifest sealed; audit event emitted |
| `PAUSED` | Signal Handler | Active signal | Prior active state, `CANCELLED` | Timers pause; activities in flight complete |
| `CANCELLED` | Signal Handler / Timeout | Cancel request | None (Terminal) | Cancel activity tokens; record partial findings |
| `FAILED` | Workflow Orchestrator | Unrecoverable error | None (Terminal) | Fail closed; record failure state in audit |

---

## 5. Activity Classes and Interfaces

All activities are registered under strongly-typed interfaces.

### 5.1 `ValidateInvestigationScopeActivity`
- **Purpose**: Validates metric name against `METRIC-REGISTRY.md` and verifies tenant subscription entitlements.
- **Queue**: `investigation-workflow-queue`
- **Schedule-To-Close**: 10 seconds.
- **Retry**: 2 attempts, exponential backoff (initial 1s, backoff coefficient 2.0).
- **Failure**: Terminal on `METRIC_NOT_FOUND` or `TENANT_INACTIVE`.

### 5.2 `GenerateInvestigationPlanActivity`
- **Purpose**: Invokes Planner LLM to produce a typed `Plan` containing an acyclic `AgentTask` DAG.
- **Queue**: `investigation-agent-activity-queue`
- **Schedule-To-Close**: 30 seconds.
- **Retry**: 1 attempt (transient failures only; schema validation failures are NOT retried).
- **Output**: Typed `Plan` schema.

### 5.3 `ExecuteReadOnlySqlCapabilityActivity`
- **Purpose**: Executes pre-registered, parameterized SQL from `SQL-CAPABILITY-CATALOG.md`.
- **Queue**: `investigation-analytics-activity-queue`
- **Schedule-To-Close**: 15 seconds.
- **Heartbeat**: 3 seconds.
- **Retry**: 1 attempt for database connection drops; 0 retries for query timeouts or policy violations.
- **Output**: Typed `CapabilityResult` with row digest and evidence record.

### 5.4 `ExecuteGovernedRetrievalActivity`
- **Purpose**: Executes hybrid search (lexical + dense) across authorized tenant documents and contracts.
- **Queue**: `investigation-retrieval-activity-queue`
- **Schedule-To-Close**: 20 seconds.
- **Retry**: 1 attempt for transient vector store drops.
- **Output**: Bounded `EvidenceBundle` with citation spans and effective-date filters applied.

### 5.5 `IngestTicketIntelligenceActivity`
- **Purpose**: Fetches and normalizes support ticket records within investigation scope.
- **Queue**: `investigation-retrieval-activity-queue`
- **Schedule-To-Close**: 15 seconds.
- **Retry**: 1 attempt.
- **Output**: Sanitized, PII-redacted `TicketEvidenceBatch`.

### 5.6 `SynthesizeHypothesesActivity`
- **Purpose**: Takes gathered evidence bundles and drafts competing root-cause hypotheses.
- **Queue**: `investigation-agent-activity-queue`
- **Schedule-To-Close**: 45 seconds.
- **Retry**: 1 attempt.
- **Output**: `List[Hypothesis]`.

### 5.7 `VerifyEvidenceAndHypothesesActivity`
- **Purpose**: Deterministic verifier checks claims against evidence citations, tests for contradictions, and computes evidence coverage.
- **Queue**: `investigation-agent-activity-queue`
- **Schedule-To-Close**: 30 seconds.
- **Retry**: 0 retries (deterministic).
- **Output**: `VerificationResult` (`VERIFIED`, `REFUTED`, or `NEED_MORE_EVIDENCE`).

### 5.8 `PackageEvidenceBundleActivity`
- **Purpose**: Computes SHA-256 digests over all cited evidence and seals investigation manifest.
- **Queue**: `investigation-workflow-queue`
- **Schedule-To-Close**: 10 seconds.
- **Retry**: 2 attempts.
- **Output**: Sealed `InvestigationManifest`.

---

## 6. Signals and Queries

### 6.1 Signals (Authenticated at Application Boundary)
1. `PauseInvestigationSignal`:
   - Payload: `{"reason": str, "paused_by": PrincipalId}`
   - Behavior: Suspends scheduling of subsequent DAG nodes; running activities complete.
2. `ResumeInvestigationSignal`:
   - Payload: `{"resumed_by": PrincipalId}`
   - Behavior: Resumes DAG scheduling.
3. `CancelInvestigationSignal`:
   - Payload: `{"reason": str, "cancelled_by": PrincipalId}`
   - Behavior: Immediately cancels all in-flight activities via cancellation tokens, marks status `CANCELLED`.

### 6.2 Queries (Sanitized Read-Only Projections)
1. `GetInvestigationStateQuery`:
   - Returns: Current lifecycle state, budget usage (time, token, USD), error details if any.
2. `GetInvestigationProgressQuery`:
   - Returns: Total DAG tasks, completed tasks, running tasks, pending tasks.
3. `GetEvidenceSummaryQuery`:
   - Returns: Number of evidence items gathered, sources, classification breakdown. (Omits raw content).

---

## 7. Retry, Timeout, and Fail-Closed Policies

### 7.1 Timeout Categories
- `WorkflowRunTimeout`: 600 seconds (10 minutes hard stop).
- `WorkflowExecutionTimeout`: 1800 seconds (allows for human pauses up to 30 min).
- `ActivityScheduleToCloseTimeout`: Defined per activity (10s to 45s).
- `ActivityHeartbeatTimeout`: 5 seconds for activities running > 10 seconds.

### 7.2 Retry Policy Classes
```python
TRANSIENT_ACTIVITY_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=1),
    backoff_coefficient=2.0,
    maximum_interval=timedelta(seconds=10),
    maximum_attempts=2,
    non_retryable_error_types=[
        "TenantViolationError",
        "AuthorizationDeniedError",
        "SchemaValidationError",
        "BudgetExceededError",
        "PromptInjectionDetectedError"
    ]
)
```

### 7.3 Fail-Closed Principle
If any security, authorization, tenant validation, or prompt injection check fails during any activity:
1. Activity immediately throws a `NonRetryableApplicationError`.
2. Workflow catches the terminal exception.
3. State transitions to `FAILED` with specific error code (e.g. `ERR_TENANT_VIOLATION`).
4. An immutable security audit event is appended (`INV-AUD-001`).
5. Partial evidence is marked untrusted and NOT exposed to external callers.

---

## 8. Workflow Versioning and Replay Compatibility

All changes to workflow definitions must use Temporal workflow versioning APIs:
```python
version = workflow.patched("p03-dag-fanout-v2")
if version == 1:
    # Legacy sequencing
    execute_sequential_plan()
else:
    # Modern parallel DAG
    execute_parallel_dag()
```
- Continuous replay testing is enforced against stored execution histories in `tests/recovery/test_investigation_workflow_replay.py`.
- Breaking changes without version gates are strictly prohibited (`INV-WF-002`).

---

## 9. Telemetry and Traceability Matrix

| Requirement / Invariant | Workflow Mechanism | Test / Verification Point |
|---|---|---|
| `INV-WF-001` (Durable State) | Temporal event history + DB projection | `test_workflow_worker_kill_recovery.py` |
| `INV-WF-002` (Determinism) | Strict activity boundary + replay tests | `test_workflow_replay_compatibility.py` |
| `INV-TEN-001..003` (Tenancy) | Workflow ID format + Activity context check | `test_workflow_cross_tenant_rejection.py` |
| `INV-IAM-001..002` (Identity) | PrincipalContext propagation | `test_workflow_unauthorized_signal.py` |
| `INV-COST-001` (Budgets) | Workflow state tracker + pre-activity gate | `test_workflow_budget_exhaustion.py` |
| `NFR-DUR-001` (No State Loss) | Worker crash injection mid-investigation | `test_recovery_worker_loss_zero_loss.py` |
| `AC-003` (Typed DAG & Replay) | Schema-validated DAG + pause/resume/cancel | `test_investigation_workflow_dag_e2e.py` |

---

## 10. Phase 06 Saga Action Execution Workflow and Reconciliation Protocol

### 10.1. Workflow Orchestration Structure
In Phase 06, the `SafeActionExecutionWorkflow` manages the multi-step forward execution and compensation lifecycle (`ADR-0002`):

```python
@workflow.defn
class SafeActionExecutionWorkflow:
    @workflow.run
    async def run(self, request: ActionIntentRecord) -> ActionLedgerRecord:
        # 1. Revalidate Policy, Tenant, and Approval Digest
        await workflow.execute_activity(revalidate_approval_activity, ...)

        # 2. Check Safety Kill Switches
        await workflow.execute_activity(check_kill_switches_activity, ...)

        # 3. Perform Dry-Run Validation
        dry_run_res = await workflow.execute_activity(dry_run_simulation_activity, ...)

        # 4. Dispatch via Tool Gateway with Idempotency Key
        try:
            return await workflow.execute_activity(dispatch_tool_gateway_activity, ...)
        except ActivityError as err:
            if err.cause == "TIMEOUT_UNKNOWN":
                # Halt blind retries; enter reconciliation protocol
                return await self.reconcile_unknown_state(request)
            else:
                # Trigger backward Saga compensation
                await self.compensate_prior_steps()
                raise
```

### 10.2. Reconciliation Activities for UNKNOWN State
1. `QueryProviderTransactionActivity`: Queries provider status using `provider_idempotency_key`.
2. `ReconciliationBackoffTimer`: Exponential timer up to 15 minutes.
3. `OperatorEscalationActivity`: If provider status remains indeterminate, emits `action.reconciliation_required.v1` and parks workflow pending human manual resolution.
