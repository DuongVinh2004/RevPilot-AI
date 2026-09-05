# Foundational Non-Functional Requirement Baseline

Status: Accepted v1.0
Owner: Principal Architecture + SRE + Security + AI/ML  
Approver: Duong Vinh (Repository Owner)
Version: v1.0
Date: 2026-09-04
Measurement state: All numeric values are `DESIGN TARGET` or `DESIGN ASSUMPTION`; there are zero measured product results.

## Requirement schema

Each row defines priority, applicable tier, classification, SLI/measurement, target, window, failure behavior, owner, evidence, and revisit trigger. Initial Commercial targets are the architecture baseline unless a row states otherwise.

| ID | P | Tier/type | SLI and target | Window | Failure behavior | Owner | Future test/evidence | Revisit trigger |
|---|---:|---|---|---|---|---|---|---|
| `NFR-SEC-001` | P0 | All / DESIGN TARGET | Unauthorized external actions = 0 | Every release/runtime | Block action, alert, preserve audit | Security/Actions | Authorization/adversarial E2E | Any nonzero occurrence is incident/gate failure |
| `NFR-SEC-002` | P0 | All / DESIGN TARGET | Reusable secrets in prompts/logs/task/workflow payloads = 0 | Every build/runtime scan | Reject/redact/quarantine | Security | Secret/DLP scan | Any detection |
| `NFR-AVL-001` | P1 | Initial / DESIGN TARGET | Product API availability >=99.9% | Calendar month | Error budget consumed; halt risky releases | SRE/API | Synthetic probes and SLI | Business impact/SLO review |
| `NFR-AVL-002` | P1 | Growth / DESIGN TARGET | Product API and required workflow service >=99.95% | Calendar month | Load shed/degrade reads; writes fail safe | SRE | Multi-AZ/load/chaos evidence | Contract or cost review |
| `NFR-LAT-001` | P1 | Initial+ / DESIGN TARGET | Synchronous product API p95 <500 ms, excluding async investigation | Rolling 15 min and 30 days | Queue async work; reject overload | API/SRE | Load test + production SLI | 3 consecutive breach windows |
| `NFR-LAT-002` | P1 | Initial+ / DESIGN TARGET | User-visible workflow event propagation p95 <5 s | Rolling 15 min | Display stale/degraded marker | Experience/Execution | Event propagation load test | 3 consecutive breach windows |
| `NFR-THR-001` | P1 | Initial / DESIGN ASSUMPTION | 100 API rps and 100 events/s sustained, 500 events/s burst | 15 min sustained / 1 min burst | Backpressure/rate limit; no Tenant bleed | Platform | 120% load test | Observed peak reaches 80% twice |
| `NFR-THR-002` | P3 | Growth / DESIGN ASSUMPTION | 2,000 API rps and 2,000 events/s sustained | 15 min | Partition/load shed according to policy | Platform | Growth capacity test before claim | Growth planning approval |
| `NFR-DUR-001` | P0 | All / DESIGN TARGET | Confirmed workflow state loss = 0; duplicate side effect after recovery = 0 | Every failure test | Pause/reconcile/fail safe | Execution | Worker/process kill and replay suite | Any violation |
| `NFR-REL-001` | P0 | All / DESIGN TARGET | Workflow resumes after eligible worker/process failure within 5 min | Per injected failure | Retry/reassign; no duplicate action | Execution/SRE | Recovery test | Recovery p95 >5 min in 3 runs |
| `NFR-REL-002` | P0 | All / DESIGN TARGET | Policy/IAM/Audit unavailable: 100% writes blocked | Every injected outage | Fail closed; explicitly degraded reads only | Security/SRE | Dependency outage matrix | Any unsafe write |
| `NFR-REC-001` | P1 | Initial+ / DESIGN TARGET | Transactional RPO <=5 min, RTO <=30 min | DR exercise at least twice/year | Invoke DR, reconcile workflows/providers | SRE/Data | Restore/DR report | Business impact analysis changes |
| `NFR-TEN-001` | P0 | All / DESIGN TARGET | Cross-tenant read/write/result/cache/event/export leakage = 0 | Every build and release | Fail release, incident response | Security/Tenancy | Cross-store A/B negative matrix | Any nonzero result |
| `NFR-TEN-002` | P0 | Initial+ / DESIGN TARGET | Isolation controls hold at 120% accepted peak load | Release load test | Reject/load shed, never disable control | SRE/Tenancy | Concurrent isolation/load test | Any control bypass/degradation |
| `NFR-AUD-001` | P0 | All / DESIGN TARGET | Required policy/approval/action/privileged events captured =100% with integrity check | Every release/runtime reconciliation | Block high-risk writes if integrity unavailable | Audit/Security | Event completeness/hash-chain test | Missing or invalid event |
| `NFR-COST-001` | P0 | Initial / DESIGN TARGET | Standard Investigation model COGS <=USD2 target; USD5 hard default stop | Per Investigation | Fallback/pause/require approval/stop | FinOps/AI | Budget boundary and ledger reconciliation | Price/quality changes >=20% |
| `NFR-COST-002` | P1 | Initial+ / DESIGN TARGET | >=99.5% metered cost reconciled to tenant/investigation/agent/model/tool | Daily/monthly | Mark bill provisional; investigate gap | FinOps | Provider invoice reconciliation | Gap >0.5% |
| `NFR-PRV-001` | P0 | All / DESIGN TARGET | Secret fields in operational telemetry =0; PII fields outside allowlist =0 | Every schema/build and continuous scan | Reject/redact/quarantine | Privacy/Security | Log schema + DLP tests | Any detection |
| `NFR-PRV-002` | P1 | Commercial / UNKNOWN | Retention/deletion/legal-hold completion target | Per legal/customer policy | Block onboarding or affected deletion workflow | Privacy/Product | Deletion propagation exercise | Before first commercial contract |
| `NFR-OBS-001` | P0 | All / DESIGN TARGET | 100% Investigations carry trace/correlation/causation and artifact version references | Every run | Mark non-reproducible; block action if required refs absent | SRE/AI | Trace contract test | Any missing required span/reference |
| `NFR-OBS-002` | P0 | All / DESIGN TARGET | Security/policy/approval/action events sampled at 100% | Continuous | Buffer bounded or block high-risk write | Security/SRE | Sampling policy test | Any sampled-away required event |
| `NFR-AI-001` | P0 | All / DESIGN TARGET | 100% production AI artifacts versioned/release-gated | Every release | Reject artifact/deployment | AI Governance | Manifest/gate test | Any unversioned artifact |
| `NFR-AI-002` | P0 | Demo+ / DESIGN TARGET | RCA Top-1 >=0.80 and Top-3 >=0.95 on hidden synthetic incident suite | Release benchmark | No release; `NEED_MORE_EVIDENCE` permitted | AI/ML | RCA benchmark | Dataset/model/schema change |
| `NFR-AI-003` | P0 | Demo+ / DESIGN TARGET | Retrieval Recall@10 >=0.90; citation precision >=0.95; unauthorized evidence rate =0 | Release benchmark | No release/evidence-dependent action | RAG/Security | Retrieval evaluation | Corpus/index/policy change |
| `NFR-AI-004` | P0 | Demo+ / DESIGN TARGET | SQL execution correctness >=0.95 and unauthorized query rate =0 | Release benchmark | Reject query/result; no action | Analytics/Security | SQL semantic suite | Metric/schema/agent change |
| `NFR-AI-005` | P1 | Commercial / DESIGN TARGET | Churn Expected Calibration Error <=0.05 and PR-AUC beats declared baseline | Time-based holdout | Do not use score for decision | ML | Calibration/holdout report | Population drift/gate failure |
| `NFR-AI-006` | P2 | Commercial / DESIGN TARGET | Uplift Qini positive and better than no-target/random baseline with stable slices | Holdout/experiment | Fall back to policy-approved non-uplift strategy | ML/Product | Uplift benchmark | Overlap/drift/experiment change |
| `NFR-AI-007` | P2 | Synthetic causal / DESIGN TARGET | Absolute treatment-effect error <=0.05 on identified synthetic estimands and assumptions disclosed 100% | Release benchmark | Label association/insufficient evidence | Causal/ML | Ground-truth causal suite | DGP/estimand/model change |

## Interpretation rules

- Passing a synthetic target is not evidence of real-world business performance.
- Zero-tolerance security/tenant/action requirements are release blockers, not averages.
- Targets may be revised only through the owning specification/ADR with traceability and rationale; measured reports never silently redefine them.
- `UNKNOWN` blocks any implementation or onboarding that needs the missing value.

