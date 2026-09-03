# Program Acceptance Criteria

Status: Proposed v0.1

| ID | Criterion | Evidence |
|---|---|---|
| `AC-001` | Seeded benchmark reproduces canonical data and hidden incident ground truth. | Hash manifest and generator tests |
| `AC-002` | Detector reports interval, score, baseline/version, scope, and event/as-of time. | Backtest report |
| `AC-003` | Investigation DAG is typed, budgeted, dependency-aware, replayable, and cancellable. | Workflow/eval report |
| `AC-004` | Every hypothesis links supporting/contradicting evidence and limitations. | RCA evaluation |
| `AC-005` | Retrieved evidence satisfies tenant, ACL, version, and effective-date policies. | Retrieval authorization suite |
| `AC-006` | Causal result states estimand, assumptions, overlap, interval, sensitivity, and limits. | Causal benchmark |
| `AC-007` | Decision filters hard constraints before expected-utility ranking. | Optimizer property tests |
| `AC-008` | Approval cannot authorize a modified/expired/replayed action. | Tamper/replay suite |
| `AC-009` | Crash/timeout/retry cannot duplicate a side effect; unknown outcomes reconcile. | Failure-injection report |
| `AC-010` | Cross-tenant leakage tests pass across every store, event, cache, log, export, and tool. | Isolation matrix |
| `AC-011` | AI/model/prompt/policy/index releases are versioned, evaluated, and reversible. | Release manifest |
| `AC-012` | Cost and latency are attributable to tenant, investigation, agent, model, and tool. | Meter reconciliation |
| `AC-013` | UI exposes evidence/decisions/tool outcomes/confidence without hidden chain-of-thought. | UX/security review |
| `AC-014` | Targets and actual benchmark values are distinct; no result is fabricated. | Benchmark report review |

