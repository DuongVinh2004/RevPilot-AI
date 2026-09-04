# Multi-Agent Platform and Typed Investigation DAG Specification

Status: Accepted Canonical Specification
Initiative: REVPILOT
Scope: Phase 03 — Governed Evidence and Investigation (Rails 6, 11)
Owner: AI Platform Architecture / Multi-Agent Systems
Traceability: `INV-AI-001`, `INV-AI-002`, `INV-SEC-001`, `INV-SEC-002`, `INV-IAM-002`, `INV-COST-001`, `INV-PRV-001`, `NFR-AI-001`, `NFR-COST-001`, `NFR-OBS-001`, `FR-INV-001..004`, `FR-RCA-001..002`, `AC-003`, `AC-004`, `AC-013`, `ADR-0003`, `ADR-0011`

---

## 1. Architectural Role and Operational Boundaries

The Agent Platform provides bounded, structured cognitive reasoning for RevPilot AI investigations. Agents execute strictly as stateless compute nodes orchestrated by Temporal activities.

### 1.1 Non-Negotiable Boundaries
1. **No Ambient Authority (`INV-SEC-001`, `SEC-002`)**: Agents never possess long-lived credentials, API keys, or direct database handles.
2. **Server-Side Authorization (`INV-IAM-002`, `SEC-003`)**: Model outputs are treated as untrusted proposals. All tool/capability calls pass through server-side policy enforcement.
3. **No External Side Effects in Phase 03 (`INV-ACT-001`)**: All agent actions in Phase 03 are strictly read-only or internal hypothesis synthesis.
4. **No Hidden Chain-of-Thought Exposure (`AC-013`)**: Internal model scratchpads are suppressed. Only structured, typed outputs (`Plan`, `Hypothesis`, `VerificationResult`, citations) are exposed to clients.
5. **No Hallucinated Factuality (`INV-AI-001`, `FR-RCA-002`)**: LLM assertions are hypotheses, not facts. A claim requires cited evidence; missing evidence results in `NEED_MORE_EVIDENCE`.

### 1.2 Non-Goals (MVP / v1 Scope)
- **Autonomous Credential Generation**: Agents cannot provision, generate, or rotate their own credentials or security tokens.
- **Arbitrary Web Browsing or Unconstrained Network Access**: Agents operate strictly offline against governed catalog endpoints; external web scraping or internet access is prohibited.
- **Self-Directed Action Execution**: Agents cannot directly trigger external write mutations or approve their own proposals without explicit human sign-off (`INV-ACT-003`).

---

## 2. Typed Schemas and Data Contracts

All agent interactions use strictly-typed Pydantic schemas. Schema validation is enforced at every boundary.

### 2.1 Investigation Plan and Task DAG
```python
class TaskType(str, Enum):
    SQL_DRILLDOWN = "SQL_DRILLDOWN"
    GOVERNED_RETRIEVAL = "GOVERNED_RETRIEVAL"
    TICKET_INTELLIGENCE = "TICKET_INTELLIGENCE"
    SYNTHESIZE_HYPOTHESES = "SYNTHESIZE_HYPOTHESES"
    VERIFY_EVIDENCE = "VERIFY_EVIDENCE"

class AgentTask(BaseModel):
    task_id: str                      # Canonical ID e.g. "task_01"
    task_type: TaskType
    capability_id: str                # E.g. "CAP-SQL-DRILLDOWN-DIMENSION"
    parameters: Dict[str, Any]        # Validated against capability input schema
    depends_on: List[str] = Field(default_factory=list) # List of prerequisite task_ids
    estimated_cost_usd: Decimal = Decimal("0.05")
    timeout_seconds: int = Field(default=30, le=60)
    retry_limit: int = Field(default=1, le=1)

class Plan(BaseModel):
    plan_id: UUIDv7
    investigation_id: UUIDv7
    tenant_id: TenantId
    anomaly_id: Optional[AnomalyId]
    metric_name: str
    target_dimensions: List[str]
    tasks: List[AgentTask]
    max_concurrency: int = Field(default=4, le=8)
    estimated_total_cost_usd: Decimal
    created_at: UtcDateTime
    version: str = "v1.0"
```

### 2.2 Capability Execution Contracts
```python
class CapabilityRequest(BaseModel):
    capability_id: str
    tenant_context: TenantContext
    principal_context: PrincipalContext
    investigation_id: UUIDv7
    as_of_time: UtcDateTime
    parameters: Dict[str, Any]
    budget_remaining_usd: Decimal

class CapabilityResult(BaseModel):
    capability_id: str
    status: Literal["SUCCESS", "FAILED", "DEGRADED", "POLICY_REJECTED"]
    data: Optional[Dict[str, Any]] = None
    evidence_references: List[UUIDv7] = Field(default_factory=list)
    execution_time_ms: int
    cost_usd: Decimal
    error_code: Optional[str] = None
    error_message: Optional[str] = None
```

### 2.3 Hypothesis and Verification Contracts
```python
class Hypothesis(BaseModel):
    hypothesis_id: str                # E.g. "hypo_01"
    title: str
    description: str
    likelihood_score: float = Field(ge=0.0, le=1.0) # Relative heuristic score
    supporting_evidence_ids: List[UUIDv7]
    contradicting_evidence_ids: List[UUIDv7]
    unverified_claims: List[str] = Field(default_factory=list)
    limitations: List[str]

class VerificationStatus(str, Enum):
    VERIFIED = "VERIFIED"             # Supported by evidence, no severe contradictions
    REFUTED = "REFUTED"               # Directly contradicted by authoritative evidence
    NEED_MORE_EVIDENCE = "NEED_MORE_EVIDENCE" # Insufficient evidence or unresolved gaps

class VerificationResult(BaseModel):
    investigation_id: UUIDv7
    tenant_id: TenantId
    status: VerificationStatus
    ranked_hypotheses: List[Hypothesis]
    top_hypothesis_id: Optional[str]
    evidence_coverage_ratio: float = Field(ge=0.0, le=1.0)
    unsupported_claim_count: int
    contradiction_count: int
    missing_evidence_descriptors: List[str]
    verifier_version: str = "v1.0"
    verified_at: UtcDateTime
```

### 2.4 Investigation and Budget State
```python
class BudgetState(BaseModel):
    allocated_usd: Decimal = Decimal("2.00")
    spent_usd: Decimal = Decimal("0.00")
    hard_stop_usd: Decimal = Decimal("5.00")
    allocated_tokens: int = 100_000
    spent_tokens: int = 0
    allocated_tool_calls: int = 20
    spent_tool_calls: int = 0

class InvestigationState(BaseModel):
    investigation_id: UUIDv7
    tenant_id: TenantId
    status: str
    active_plan_id: Optional[UUIDv7]
    completed_tasks: List[str] = Field(default_factory=list)
    failed_tasks: List[str] = Field(default_factory=list)
    gathered_evidence_count: int = 0
    budget: BudgetState
    updated_at: UtcDateTime
```

---

## 3. Agent Roles and Division of Responsibilities

| Role | Enforcing Module | Primary Responsibility | Input Schema | Output Schema | Prohibited Behaviors |
|---|---|---|---|---|---|
| **Planner** | `revpilot.modules.agent.planner` | Decomposes anomaly into acyclic task DAG | Investigation scope, metric metadata | `Plan` | Unregistered tools, cycles, fan-out > 8, ad-hoc SQL |
| **Worker (Retriever)** | `revpilot.modules.agent.retriever` | Gathers document and contract snippets | `CapabilityRequest` | `EvidenceBundle` | Unfiltered searches, ignoring effective dates |
| **Worker (Analyst)** | `revpilot.modules.agent.analyst` | Executes structured metric drill-downs | `CapabilityRequest` | `CapabilityResult` | DDL, DML, arbitrary joins, tenant overrides |
| **Worker (Ticket Reader)** | `revpilot.modules.agent.tickets` | Gathers customer ticket context | `CapabilityRequest` | `TicketEvidenceBatch` | Treating ticket text as prompt instructions |
| **Hypothesis Synthesizer**| `revpilot.modules.agent.synthesizer` | Generates candidate root causes | Gathered evidence bundles | `List[Hypothesis]` | Asserting certainty without citations |
| **Verifier** | `revpilot.modules.agent.verifier` | Deterministically validates citations & checks contradictions | `List[Hypothesis]`, Evidence | `VerificationResult` | Accepting claims without evidence citations |

---

## 4. DAG Constraints and Validation Engine

Before scheduling tasks, the workflow orchestrator validates the proposed `Plan`:
1. **Acyclicity Check**: Verifies task dependency graph is a strict Directed Acyclic Graph using Kahn's algorithm or DFS.
2. **Depth Limit**: Maximum DAG depth is 4 levels.
3. **Fan-Out Limit**: Maximum concurrency fan-out is 8 tasks.
4. **Total Task Limit**: Maximum total tasks in one investigation is 20.
5. **Capability Registration**: Every task's `capability_id` must exist in the registered capability catalog.
6. **Cost Check**: `estimated_total_cost_usd` must not exceed `allocated_usd`.

Validation failure immediately rejects the plan and transitions investigation to `FAILED` with code `ERR_INVALID_PLAN_DAG`.

---

## 5. Execution Budgets and FinOps Controls

Under `INV-COST-001` and `NFR-COST-001`:
1. **Per-Investigation Standard Ceiling**: USD 2.00 target COGS.
2. **Hard Kill-Switch Ceiling**: USD 5.00 maximum expenditure.
3. **Token Limit**: 100,000 cumulative tokens across all model calls.
4. **Tool-Call Limit**: 20 cumulative capability invocations.
5. **Time Limit**: 300 seconds maximum total duration.

If any threshold is exceeded during execution:
- Active activities finish current step.
- Pending activities are canceled.
- Verifier is invoked with currently gathered evidence only.
- If evidence is insufficient, return `NEED_MORE_EVIDENCE` with reason `BUDGET_EXHAUSTED`.

---

## 6. Verifier Engine and Unsupported Claim Policy

Under `INV-AI-001` and `AC-004`:
1. **Citation Completeness**: Every claim in a `Hypothesis` must link to at least one valid `EvidenceReference` with active status and matching tenant.
2. **Deterministic Citation Verification**: Verifier inspects cited text spans. If cited span does not exist in evidence content digest, claim is rejected.
3. **Contradiction Detection**: If evidence A supports hypothesis H1 and authoritative evidence B contradicts H1, H1 status is marked `REFUTED` or downgraded with explicit contradiction record.
4. **Zero Hallucination Acceptance**: If no hypothesis achieves >= 0.80 likelihood with complete evidence backing, or if evidence gaps exist on key dimensions, status MUST be `NEED_MORE_EVIDENCE` (`FR-RCA-002`).

---

## 7. Traceability Matrix

| Requirement / Invariant | Enforcement Point | Verification Test Suite |
|---|---|---|
| `FR-INV-001` (Typed DAG) | Planner output validator | `test_planner_dag_validation.py` |
| `FR-INV-002` (Parallel Nodes) | Temporal Activity Dispatcher | `test_dag_parallel_dispatch.py` |
| `FR-RCA-001` (Ranked Hypotheses) | Verifier Module | `test_hypothesis_ranking.py` |
| `FR-RCA-002` (NEED_MORE_EVIDENCE) | Verifier Policy Engine | `test_need_more_evidence_fallback.py` |
| `INV-AI-001` (Typed Evidence Facts)| Verifier Engine | `test_unsupported_claim_rejection.py` |
| `INV-AI-002` (Artifact Versions) | Manifest Sealer | `test_investigation_manifest_versioning.py` |
| `INV-COST-001` (Budget Enforcement) | Orchestrator Pre-Dispatch Gate | `test_investigation_budget_caps.py` |
| `AC-013` (No Hidden Chain-of-Thought)| API Serialization Layer | `test_suppress_chain_of_thought.py` |
