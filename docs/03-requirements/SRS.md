# Software Requirements Specification

Status: Accepted Canonical Specification  
Owner: Principal System Architect  
Approver: Dương Vinh  
Version: v1.0  
Date: 2026-09-04  

## Revision History

| Version | Date | Author | Reviewer | Approval | Summary of Changes |
|---|---|---|---|---|---|
| v0.1 | 2026-09-04 | Systems Architecture | Principal Architect | Dương Vinh | Baseline software requirements specification |


## Requirement taxonomy

Requirements use RFC 2119 meanings for MUST, SHOULD, and MAY. Priorities are P0 foundation, P1 production-critical, P2 AI differentiation, and P3 scale optimization.

### Business and functional requirements

> [!IMPORTANT]
> The base requirements below are supplemented by [`FR-CLOSURE-CATALOG.md`](FR-CLOSURE-CATALOG.md), which supplies the 66 PRD-planned IDs that were previously absent from this SRS. All verification references are planned until implemented and executed; this SRS makes no test-pass claim.

| ID | Priority | Requirement | Verification |
|---|---|---|---|
| `FR-DET-001` | P0 | Register versioned metric definitions and dimensions. | Contract + metric fixture test |
| `FR-DET-002` | P0 | Detect anomalies with prediction/baseline interval and score. | Seeded backtest |
| `FR-DET-003` | P0 | Deduplicate repeated detections for the same metric/scope/window. | Idempotency test |
| `FR-INV-001` | P0 | Create a typed, budgeted investigation DAG; linear hard-coded plans are invalid. | Planner schema/eval |
| `FR-INV-002` | P0 | Execute independent read-only nodes in parallel and honor dependencies. | Workflow integration test |
| `FR-INV-003` | P0 | Checkpoint, retry, cancel, pause, resume, and fail safely. | Worker-kill recovery test |
| `FR-INV-004` | P0 | Drill down registered dimensions without unrestricted SQL generation. | Analytics fixtures |
| `FR-EVD-001` | P0 | Attach tenant, access policy, provenance, effective date, and version to evidence. | Retrieval authorization test |
| `FR-EVD-002` | P0 | Perform hybrid retrieval, reranking, and citation verification. | Retrieval benchmark |
| `FR-EVD-003` | P0 | Reject superseded or out-of-scope policy clauses. | Effective-date fixture |
| `FR-ML-001` | P0 | Benchmark anomaly models against statistical baselines. | Time-split evaluation |
| `FR-ML-002` | P1 | Produce calibrated churn probabilities and local explanations. | Calibration + SHAP tests |
| `FR-ML-003` | P2 | Estimate heterogeneous treatment effects separately from churn risk. | Qini/uplift benchmark |
| `FR-ML-004` | P2 | State causal estimand, assumptions, interval, overlap, and sensitivity. | Causal benchmark review |
| `FR-RCA-001` | P0 | Rank multiple hypotheses with supporting and contradicting evidence. | Ground-truth RCA suite |
| `FR-RCA-002` | P0 | Return `NEED_MORE_EVIDENCE` instead of unsupported certainty. | Adversarial eval |
| `FR-DEC-001` | P0 | Optimize expected utility under hard policy/budget constraints. | Deterministic optimizer test |
| `FR-ACT-001` | P0 | Route every side effect through the Tool Gateway. | Architecture/contract test |
| `FR-ACT-002` | P0 | Bind approval to immutable action and target digests. | Tamper test |
| `FR-ACT-003` | P0 | Enforce idempotency, dry-run, blast radius, and kill switches. | Failure-injection suite |
| `FR-ACT-004` | P1 | Use Saga compensations; never claim universal rollback. | Adapter contract test |
| `FR-LRN-001` | P1 | Capture treatment assignment and outcomes at configured horizons. | Outcome pipeline test |
| `FR-LRN-002` | P1 | Require evaluation/release gates before learned artifacts affect production. | Release-policy test |
| `FR-CTL-001` | P0 | Propagate trusted tenant context through every data and tool boundary. | Cross-tenant suite |
| `FR-CTL-002` | P0 | Attribute cost by tenant/user/investigation/agent/model/tool. | Meter reconciliation |
| `FR-CTL-003` | P1 | Support tenant lifecycle without orphaned data or credentials. | Provision/export/delete tests |

### Requirement ownership and lifecycle

The owner and lifecycle status for the existing base rows are inherited from the table below; individual expanded rows are owned directly in `FR-CLOSURE-CATALOG.md`.

| Requirement family | Owner | Lifecycle status | Design traceability | Evidence state |
|---|---|---|---|---|
| `FR-DET-*` | Analytics/Data Lead | Proposed / implementation pending | ANOMALY-DOMAIN-SPEC, METRIC-REGISTRY | Planned tests only |
| `FR-INV-*`, `FR-RCA-*` | Workflow/Agent Platform Lead | Proposed / implementation pending | MULTI-AGENT-SPEC, TEMPORAL-WORKFLOW-SPEC | Planned tests only |
| `FR-EVD-*` | Evidence/RAG/Security Lead | Proposed / implementation pending | EVIDENCE-PROVENANCE-SPEC, RAG-SPEC | Planned tests only |
| `FR-ML-*` | ML/Causal/AI Governance Lead | Proposed / implementation pending | ML-SYSTEM-SPEC, CAUSAL-INFERENCE-SPEC | Planned benchmarks only |
| `FR-DEC-*`, `FR-ACT-*` | Decision/Actions/IAM Lead | Proposed / implementation pending | DECISION-ENGINE-SPEC, APPROVAL-ACTION-LOOP-SPEC | Planned tests only |
| `FR-LRN-*` | ML/Product/Data Lead | Proposed / implementation pending | AI-GOVERNANCE, DATA-GOVERNANCE | Planned tests only |
| `FR-CTL-*` | IAM/Tenancy/Security/Compliance Lead | Proposed / implementation pending | IAM-SPEC, MULTI-TENANCY-SPEC, DATABASE-SCHEMA | Planned tests only |

### Security and quality requirements

| ID | Target/invariant | Failure behavior |
|---|---|---|
| `SEC-001` | Cross-tenant data disclosure or write: zero tolerance. | Deny, alert, preserve audit evidence |
| `SEC-002` | Agent never receives reusable external credentials. | Broker failure denies tool call |
| `SEC-003` | Tool authorization is enforced server-side from trusted identity context. | Default deny |
| `SEC-004` | Untrusted documents/tool output cannot grant authority or change policy. | Mark untrusted; filter and isolate |
| `SEC-005` | Approval cannot be replayed for a changed payload, target, or expired window. | Deny and require new approval |
| `NFR-REL-001` | Durable workflow resumes after worker/process loss without duplicate action. | Reconcile from history/action ledger |
| `NFR-REL-002` | Policy/IAM/audit unavailability blocks writes; read analysis may degrade explicitly. | Fail closed for action |
| `NFR-OBS-001` | Every investigation has end-to-end trace/correlation IDs. | Reject missing IDs at boundaries |
| `NFR-COST-001` | Per-investigation and tenant cost/time/tool-call budgets are enforced. | Throttle, fallback, pause, or approve |
| `NFR-AI-001` | Every production artifact is versioned and reproducible from recorded references. | Mark investigation non-reproducible |
| `NFR-PRV-001` | Sensitive payload is minimized; immutable audit stores hashes/metadata, not raw prompt dumps. | Redact/quarantine event |

### Canonical foundation references

- Detailed workload tiers, capacity values, confidence, and revisit triggers: [`WORKLOAD-ASSUMPTIONS.md`](WORKLOAD-ASSUMPTIONS.md). These are design assumptions/targets, not measured results.
- Test-oriented quality requirements: [`NFR-BASELINE.md`](NFR-BASELINE.md).
- Cross-cutting enforcement obligations: [`INVARIANT-REGISTRY.md`](INVARIANT-REGISTRY.md).

If an inline example conflicts with one of these artifacts, work stops under the specification-precedence procedure. Measured results belong in dated benchmark/SLO evidence and never silently replace design targets.

## Acceptance policy

A requirement is complete only when linked to an architecture component, implementation task, automated test/eval, acceptance criterion, operational signal, and owner. Requirements with unresolved privacy, authority, or causality assumptions cannot enter implementation.
