# Evaluation Framework Specification

Status: Accepted Canonical Specification
Initiative: REVPILOT
Phase: Phase 01 — Canonical Data and Synthetic Benchmark
Owner: AI/ML Architecture + Evaluation Engineering
Traceability: `BR-001`, `BR-002`, `FR-ML-001..004`, `FR-RCA-001..002`, `INV-DATA-001`, `INV-AI-001..002`, `NFR-AI-001..007`, `AC-001`, `AC-002`, `AC-006`, `AC-014`

---

## 1. Principles and Measurement Discipline

1. **Anti-Fabrication Invariant (`AC-014`)**: Under no circumstances may design targets, assumptions, or acceptance thresholds be reported as measured benchmark results. A measured result exists ONLY when an automated evaluation run executes against a versioned dataset manifest and records machine output.
2. **Deterministic Reproducibility (`AC-001`)**: All benchmarks and evaluation suites execute against pinned generator seeds, immutable dataset manifests, and explicit code/model versions.
3. **Air-Gapped Ground-Truth Evaluation (`INV-DATA-001`, `NFR-AI-002`)**: Ground-truth labels are stored in the isolated `ground_truth` schema and are never exposed to the agent runtime, prompt contexts, or investigation traces. Evaluation harnesses compare agent conclusions against ground truth offline.
4. **Distinction of Evaluation Categories**:
   - **Acceptance Threshold**: The minimum binary pass/fail gate required for release.
   - **Design Target**: Long-term aspirational engineering goal.
   - **Expected Fixture Result**: The mathematical output of a deterministic synthetic scenario.
   - **Measured Benchmark Result**: The empirical score produced by a recorded evaluation run.

---

## 2. Evaluation Schema (`EvalRun`)

Every evaluation execution generates an immutable `EvalRun` record:

```json
{
  "eval_run_id": "evl_01h8abcde987654321",
  "eval_suite": "PHASE_01_SYNTHETIC_BENCHMARK",
  "evaluator_version": "1.0.0",
  "dataset_manifest_id": "mnf_01h8abc1234567890",
  "dataset_profile": "DEVELOPMENT",
  "dataset_seed": 42,
  "git_commit": "e05_closure_baseline",
  "executed_at_utc": "2026-09-03T18:30:00Z",
  "operator_id": "eval_runner_automated",
  "metrics": {
    "manifest_hash_match": 1.0,
    "runtime_ground_truth_leakage_rate": 0.0,
    "cross_tenant_isolation_violations": 0,
    "temporal_leakage_violations": 0
  },
  "verdict": "PASS",
  "measured_vs_target_disclosure": "All metrics are measured empirical values from run evl_01h8abcde987654321."
}
```

---

## 2.1. Canonical Benchmark Manifest (v1.0.0)

Under `AC-001`, `AC-014`, and `NFR-AI-001..007`, all evaluation suites consume the canonical benchmark parameter set defined below. No evaluation protocol may define conflicting incident identities, temporal partitions, or gating thresholds.

### 2.1.1. Incident Identity & Scope Manifest
| Parameter | Canonical Specification | Governing Reference |
|---|---|---|
| **Incident Scenario ID** | `INC-SYNTH-TRUCK-001` | `SYNTHETIC-DATASET-SPEC §6.1` |
| **Scenario Name** | Midwest Regional Carrier Fleet Capacity Disruption | `SYNTHETIC-DATASET-SPEC §6.1` |
| **Origin Facility** | `WH-MIDWEST-01` (Warehouse, Chicago, IL) | `SYNTHETIC-DATASET-SPEC §6.2` |
| **Logistics Carrier** | `CARRIER_REGIONAL_LOGISTICS` (Regional Ground) | `SYNTHETIC-DATASET-SPEC §6.2` |
| **Target Metric** | `order_cancellation_rate` (`METRIC-001`) | `METRIC-REGISTRY §2` |
| **Primary Tenant** | `ten_alpha` (Treatment population) | `SYNTHETIC-DATASET-SPEC §6.1` |
| **Control Tenant** | `ten_beta` (A/B cross-tenant isolation control) | `SYNTHETIC-DATASET-SPEC §6.1` |
| **Internal Controls** | Shipments via `CARRIER_AIR_EXPRESS` or `WH-WEST-01` (Reno, NV) | `SYNTHETIC-DATASET-SPEC §6.2` |
| **Deterministic Seeds** | Pinned `42` (`DEVELOPMENT`) and `1337` (`DEMO`) | `AC-001` |

### 2.1.2. Temporal Partitioning Timeline
| Partition | Relative Days | Canonical UTC Timestamp Range | Purpose |
|---|---|---|---|
| **Training (Fitting)** | Days 1–30 | `2026-01-01 00:00:00Z` to `2026-01-30 23:59:59Z` | Detector & baseline historical fitting |
| **Calibration** | Days 31–44 | `2026-01-31 00:00:00Z` to `2026-02-13 23:59:59Z` | Threshold tuning ($k=3.0, \text{FPR} \le 0.05$) |
| **Causal Disruption** | Days 45–52 | `2026-02-14 08:00:00Z` to `2026-02-21 23:59:59Z` | Injected disruption (184h / 7.66 days) |
| **As-Of Evaluation Time**| Day 53 onset | `2026-02-22 00:00:00Z` | Watermark for offline evaluation cut-off |
| **Post-Incident Recovery**| Days 53–60 | `2026-02-22 00:00:00Z` to `2026-03-01 23:59:59Z` | Normalization & recovery observation |

### 2.1.3. Mechanistic Ground Truth Parameters
- **True Root Cause**: Fleet capacity collapse at `CARRIER_REGIONAL_LOGISTICS` increasing outbound dispatch backlog latency from 12h to 84h at `WH-MIDWEST-01`, driving delivery SLA breaches from 2.1% to 38.4% and customer cancellations under 48-hour delivery guarantee.
- **True Estimand**: $\text{ATE}^* = \mathbb{E}[Y(T=1) - Y(T=0)] = +0.0660$ (+6.6% absolute cancellation spike).
- **True Affected Revenue**: $142,560.00 USD (482 affected orders).
- **True Confounders**: Regional storm $X_{\text{storm}}$ (Northeast shipping delay), Marketing campaign $X_{\text{promo}}$ (+25% volume).
- **Decoy Hypotheses**: Payment gateway outage (Refuted: payment success 99.4%), Product price hike (Refuted: price catalogue unchanged).

### 2.1.4. Unified Quality & Gating Thresholds Baseline
| Gate ID | Target Requirement | Evaluation SLI | Benchmark Pass Gate | Scope / Invariant |
|---|---|---|---|---|
| `GATE-COST-PER-INV` | `NFR-COST-001`, `INV-COST-001` | Cost per Investigation | $\le \$2.00$ target; $\le \$5.00$ hard stop | Bounded spend / 20 tools |
| `GATE-RCA-TOP1` | `NFR-AI-002` | Top-1 Root Cause Accuracy | $\ge 0.80$ | Injected cause ranked #1 |
| `GATE-RCA-TOP3` | `NFR-AI-002` | Top-3 Root Cause Accuracy | $\ge 0.95$ | Injected cause in top 3 |
| `GATE-UNSUPPORTED-CLAIMS`| `INV-AI-001` | Unsupported Claim Rate | Exactly $0.00\%$ | Zero ungrounded statements |
| `GATE-CITATION-PRECISION`| `NFR-AI-003` | Citation Precision | $\ge 0.95$ | Exact character-span match |
| `GATE-RETRIEVAL-RECALL` | `NFR-AI-003` | Recall@10 | $\ge 0.90$ | Top-10 relevant evidence |
| `GATE-RETRIEVAL-MRR` | Evaluation Baseline | MRR | $\ge 0.85$ | Mean Reciprocal Rank |
| `GATE-CAUSAL-ATE-ERR` | `NFR-AI-007` | Absolute ATE Error | $\le 0.0500$ | $|\widehat{\text{ATE}} - 0.0660| \le 0.0500$ |
| `GATE-DECOY-REFUTATION` | `FR-RCA-001` | Decoy Refutation Rate | $100\%$ | Both decoys refuted |
| `GATE-ANOMALY-F1` | `FR-DET-002` | Anomaly F1-Score | $\ge 0.82$ | Precision $\ge 0.80$, Recall $\ge 0.85$ |
| `GATE-ANOMALY-FPR` | `FR-DET-002` | Clean Window FPR | $\le 0.05$ | Days 1–44 false alarm rate |
| `GATE-ANOMALY-LEADTIME` | `FR-DET-002` | Detection Lead Time | $\le 48\text{ hours}$ | From disruption onset |
| `GATE-TIME-LEAKAGE` | `INV-DATA-001` | Lookahead Leakage Rate | Exactly $0.00\%$ | Zero records $> \text{as\_of\_time}$ |
| `GATE-AIRGAP-ISOLATION` | `INV-DATA-001`, `NFR-AI-002` | Ground-Truth Read Leak | Exactly $0.00\%$ | Zero runtime access |
| `GATE-TENANT-ISOLATION` | `INV-TEN-001`, `NFR-TEN-001` | Cross-Tenant Leakage | Exactly $0.00\%$ | Zero cross-tenant data |

---

## 3. Phase 01 Benchmark Evaluation Suites

### 3.1. Suite: `SUITE-P01-SEED-REPRODUCIBILITY`
- **Objective**: Verify that generating datasets using the same seed produces bit-for-bit identical outputs.
- **Input**: Generator seeds `42` (`DEVELOPMENT`) and `1337` (`DEMO`).
- **Metric**: SHA-256 artifact hash match percentage across all generated CSV/Parquet files.
- **Acceptance Threshold**: Exactly `1.000` (100% hash match).
- **Design Target**: 100% byte match in under 5 seconds for development profile.
- **Expected Fixture Result**: Hashes exactly equal to `manifest.json`.

### 3.2. Suite: `SUITE-P01-GROUND-TRUTH-AIRGAP`
- **Objective**: Verify that runtime database roles and agent prompt templates have zero access to hidden incident labels.
- **Input**: Simulated investigation query attempting `SELECT * FROM ground_truth.incidents`.
- **Metric**: Unauthorized ground-truth read rate.
- **Acceptance Threshold**: Exactly `0.000` (0% access, 100% permission denied / fail-closed).
- **Design Target**: 0 leaks across 10,000 adversarial prompt and SQL injection attempts.

### 3.3. Suite: `SUITE-P01-TIME-LEAKAGE`
- **Objective**: Verify that an investigation evaluated `as_of` a past date cannot see future records.
- **Input**: As-of watermark `Day 47 12:00:00Z`; queries requesting order, shipment, and ticket metrics.
- **Metric**: Future-record leakage count.
- **Acceptance Threshold**: Exactly `0` records returned where `event_time > :as_of_time`.

### 3.4. Suite: `SUITE-P01-TENANT-ISOLATION`
- **Objective**: Verify strict A/B tenant isolation between `ten_alpha` and `ten_beta`.
- **Input**: Cross-tenant injection queries and negative access fixtures.
- **Metric**: Cross-tenant leak count.
- **Acceptance Threshold**: Exactly `0` cross-tenant disclosures (`NFR-TEN-001`).

---

---

## 4. Phase 02 Anomaly Detection Benchmark Evaluation Suites

### 4.1. Suite: `SUITE-P02-ANOMALY-BENCHMARK`
- **Objective**: Benchmark candidate anomaly detectors against baseline on Midwest truck-capacity disruption (`INC-SYNTH-TRUCK-001`).
- **Input**: Synthetic Development profile (Seed `42`), Metric `METRIC-001` (`cancellation_rate`).
- **Baseline**: `BASE-SEASONAL-NAIVE-001` ($Y_t = Y_{t-7}$).
- **Detector**: `DET-STL-RESIDUAL-001`.
- **Metrics & Thresholds**:
  - Precision >= 0.80
  - Recall >= 0.85
  - F1-Score >= 0.82
  - False Positive Rate (FPR) <= 0.05 on clean control windows (Days 1–44)
  - Lead Time <= 48 hours from disruption onset (Day 45)
- **Reference**: `docs/20-evaluation/ANOMALY-BENCHMARK-PROTOCOL.md` §3.

### 4.2. Suite: `SUITE-P02-ROLLING-TIMESPLIT`
- **Objective**: Verify that simulated rolling daily inference has zero future-record lookahead leakage.
- **Input**: 60 daily rolling time-steps across the evaluation partition.
- **Metric**: Future-record leakage count.
- **Acceptance Threshold**: Exactly `0` records evaluated where `event_time > :as_of_time`.

### 4.3. Suite: `SUITE-P02-LOCALIZATION-ACCURACY`
- **Objective**: Verify dimensional localization correctly identifies primary contributing segment (`CARRIER_REGIONAL_LOGISTICS`) during Midwest incident.
- **Metric**: Top-1 Localization Accuracy.
- **Acceptance Threshold**: >= 0.85 across repeated incident evaluation runs.

---

## 5. Phase 03 Governed Evidence & Investigation Evaluation Suites

### 5.1. Suite: `SUITE-P03-RAG-EVIDENCE`
- **Objective**: Benchmark hybrid retrieval, effective-date filtering, and citation verification against enterprise documents and contracts.
- **Metrics & Acceptance Gates**:
  - Recall@10 >= 0.90 (`NFR-AI-003`)
  - Mean Reciprocal Rank (MRR) >= 0.85
  - Citation Precision >= 0.95 (`NFR-AI-003`)
  - Unauthorized Evidence Rate = 0.00% (`NFR-AI-003`)
  - Superseded Content Rejection = 100% (`INV-EVD-002`)
  - Effective-Date Correctness = 100% (`INV-EVD-002`)
- **Reference**: `docs/20-evaluation/INVESTIGATION-BENCHMARK-PROTOCOL.md` §3.

### 5.2. Suite: `SUITE-P03-SQL-CAPABILITY-CORRECTNESS`
- **Objective**: Verify semantic correctness, tenant predicate injection, and read-only enforcement of all 7 registered SQL capabilities.
- **Metrics & Acceptance Gates**:
  - SQL Semantic Correctness >= 0.95 (`NFR-AI-004`)
  - Unauthorized Query Rate = 0.00% (`NFR-AI-004`)
  - DML/DDL Rejection = 100% (`INV-ACT-001`)
  - Query Timeout Enforcement (<= 5,000 ms) = 100%
- **Reference**: `docs/06-agent-platform/SQL-CAPABILITY-CATALOG.md` §6.

### 5.3. Suite: `SUITE-P03-WORKFLOW-DURABILITY`
- **Objective**: Verify Temporal workflow execution, worker-loss recovery, acyclic DAG execution, and signal responsiveness.
- **Metrics & Acceptance Gates**:
  - State Loss = 0 (`NFR-DUR-001`)
  - Recovery Time after Worker Kill <= 5 min (`NFR-REL-001`)
  - Duplicate Activity Invocations = 0 (`NFR-DUR-001`)
  - Budget Hard Stop Enforcement ($5.00 USD / 20 tools) = 100% (`INV-COST-001`)
- **Reference**: `docs/12-workflow-engine/TEMPORAL-WORKFLOW-SPEC.md` §7.

### 5.4. Suite: `SUITE-P03-VERIFIER-UNSUPPORTED-CLAIMS`
- **Objective**: Verify that deterministic verifier rejects all ungrounded claims, catches contradictions, and falls back to `NEED_MORE_EVIDENCE`.
- **Metrics & Acceptance Gates**:
  - Unsupported Claim Acceptance Rate = 0.00% (`INV-AI-001`)
  - Contradiction Detection Sensitivity = 100%
  - `NEED_MORE_EVIDENCE` Accuracy = 100% (`FR-RCA-002`)
  - Hidden Chain-of-Thought Leakage Rate = 0.00% (`AC-013`)

---

## 6. Phase 04 Causal Inference and Root-Cause Analysis Evaluation Suites

### 6.1. Suite: `SUITE-P04-CAUSAL-ATE`
- **Objective**: Benchmark statistical causal estimators against the known synthetic ground truth for Midwest truck capacity disruption (`INC-SYNTH-TRUCK-001`).
- **Input**: Pinned Development Profile (Seed `42`), canonical order and shipment tables, estimated against registered estimand `ATE`.
- **True Ground Truth**: $\text{ATE}^* = +0.0660$.
- **Metrics & Acceptance Gates**:
  - Absolute ATE Error $\le 0.0500$ (`NFR-AI-007`)
  - Nominal 95% Confidence Interval Coverage $\ge 90.0\%$
  - Direction Correctness $= 100\%$ ($\widehat{\text{ATE}} > 0, p < 0.01$)
  - Overlap / Positivity Satisfaction $= 100\%$ ($0.05 \le e(X) \le 0.95$)
- **Reference**: `docs/20-evaluation/CAUSAL-BENCHMARK-PROTOCOL.md` §3.

### 6.2. Suite: `SUITE-P04-RCA-TOPK`
- **Objective**: Evaluate multi-hypothesis ranking and competing root-cause discrimination against hidden incident scenarios.
- **Metrics & Acceptance Gates**:
  - Top-1 RCA Accuracy $\ge 0.80$ (`NFR-AI-002`)
  - Top-3 RCA Accuracy $\ge 0.95$ (`NFR-AI-002`)
  - Decoy Refutation Rate $= 100\%$ (Payment outage and product defect decoys refuted)
  - `NEED_MORE_EVIDENCE` Accuracy $= 100\%$ (`FR-RCA-002`) on truncated samples
- **Reference**: `docs/11-decision-intelligence/HYPOTHESIS-VERIFIER-SPEC.md` §3.

### 6.3. Suite: `SUITE-P04-UNSUPPORTED-CLAIMS`
- **Objective**: Verify that 100% of ungrounded model statements, correlation-to-causation leaps, and lookahead leakage attempts are rejected.
- **Metrics & Acceptance Gates**:
  - Unsupported Claim Rate $= 0.00\%$ (`INV-AI-001`)
  - Correlation as Causation Rejection Rate $= 100\%$
  - Temporal Lookahead Leakage Rate $= 0.00\%$ (`INV-DATA-001`)
  - Ground-Truth Schema Access $= 0$ (100% permission denied / fail-closed)
- **Reference**: `docs/06-agent-platform/UNSUPPORTED-CLAIM-POLICY.md` §3.

---

## 7. Phase 05 Churn, Uplift, and Decision Optimization Evaluation Suites

### 7.1. Suite: `SUITE-P05-CHURN-ECE`
- **Objective**: Verify that churn probability predictions are well-calibrated and temporally sound against time-split holdout data.
- **Metrics & Acceptance Gates**:
  - Expected Calibration Error $\le 0.0500$ ($5.0\%$) (`NFR-AI-005`)
  - Precision-Recall AUC (PR-AUC) $\ge 0.7500$
  - Brier Score $\le 0.1500$
  - Lookahead / Feature Leakage Rate $= 0.00\%$ (`INV-DATA-001`)
- **Reference**: `docs/08-ml-platform/ML-SYSTEM-SPEC.md` §5.

### 7.2. Suite: `SUITE-P05-UPLIFT-QINI`
- **Objective**: Benchmark CATE uplift models against synthetic randomized trials with known heterogeneous treatment effects.
- **Metrics & Acceptance Gates**:
  - Normalized Qini Score $> 0.2000$ (`NFR-AI-006`)
  - Area Under Uplift Curve (AUUC) beats random targeting by $\ge 15.0\%$
  - Mean Absolute CATE Error $\le 0.0400$ against ground truth (`NFR-AI-007`)
  - Negative Uplift ("Sleeping Dog") Detection Sensitivity $\ge 95.0\%$
- **Reference**: `docs/08-ml-platform/UPLIFT-BENCHMARK-PROTOCOL.md` §4.

### 7.3. Suite: `SUITE-P05-DECISION-UTILITY`
- **Objective**: Property-based verification of the 12-step decision optimization engine.
- **Metrics & Acceptance Gates**:
  - Hard Constraints Precede Utility Ranking $= 100\%$ (`AC-007`)
  - Ineligible Candidate Selection Rate $= 0.00\%$
  - Budget Overdraft Violations $= 0$ (`INV-COST-001`, `NFR-COST-001`)
  - External Tool Mutation Invocations $= 0$ (`INV-ACT-001`)
  - Abstention on Negative Utility $= 100\%$
- **Reference**: `docs/11-decision-intelligence/DECISION-ENGINE-SPEC.md` §2, §3.

### 7.4. Suite: `SUITE-P05-FAIRNESS-DISPARITY`
- **Objective**: Measure operational slice performance and treatment allocation equity across qualified customer tiers.
- **Metrics & Acceptance Gates**:
  - Calibration Disparity by Tier $\Delta \text{ECE} \le 0.0300$
  - Allocation Parity Ratio $0.80 \le \text{Ratio} \le 1.25$ on comparable uplift cohorts
  - Small-sample ($N < 50$) Suppression Rate $= 100\%$
- **Reference**: `docs/11-decision-intelligence/FAIRNESS-SLICE-EVALUATION.md` §3.

---

## 8. Phase 06 Approval and Safe Action Loop Evaluation Suites

### 8.1. Suite: `SUITE-P06-APPROVAL-DIGEST`
- **Objective**: Verify that 100% of action dispatches are cryptographically bound to an unexpired, untampered human approval digest (`AC-008`).
- **Metrics & Acceptance Gates**:
  - Digest Verification Match $= 100.0\%$ (`INV-ACT-002`)
  - Agent Self-Approval Rejection Rate $= 100.0\%$ (`INV-ACT-003`)
  - Tampered Payload Rejection Rate $= 100.0\%$
  - Expired Approval Rejection Rate $= 100.0\%$
- **Reference**: `docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md` §3.1.

### 8.2. Suite: `SUITE-P06-GATEWAY-DRYRUN`
- **Objective**: Verify that dry-run mode validates identical policies and blast constraints with strictly zero external side effects (`AC-009`).
- **Metrics & Acceptance Gates**:
  - External Socket Connections $= 0$ (`INV-ACT-001`)
  - Policy Parity with Real Run $= 100.0\%$
  - Simulated Impact Estimation Error $\le 0.0001$
- **Reference**: `docs/16-tool-gateway/TOOL-GATEWAY-SPEC.md` §7.3.

### 8.3. Suite: `SUITE-P06-KILLSWITCH-HALT`
- **Objective**: Benchmark distributed kill-switch propagation and execution blocking latency.
- **Metrics & Acceptance Gates**:
  - Kill-Switch Propagation Latency $< 500\text{ms}$ (`INV-REL-001`)
  - Tool Invocation Halt Rate under Active Kill Switch $= 100.0\%$
  - Zero Agent Override Capability $= 100.0\%$
- **Reference**: `docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md` §5.

### 8.4. Suite: `SUITE-P06-UNKNOWN-RECONCILIATION`
- **Objective**: Verify that network timeouts and UNKNOWN outcomes never trigger blind retries, routing deterministically to reconciliation.
- **Metrics & Acceptance Gates**:
  - Blind Retry Rate on UNKNOWN $= 0.00\%$ (`NFR-REL-001`)
  - Idempotency Conflict Handling $= 100.0\%$
  - SRE Escalation Event Emission $= 100.0\%$
- **Reference**: `docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md` §4.1.

---

## 9. Phase 07 Evaluation Suites (Multi-Tenant Pilot, Connectors, Operations)

### 9.1. Suite: `SUITE-P07-TENANT-ISOLATION`
- **Objective**: Rigorous adversarial evaluation of cross-tenant boundaries across database, cache, vector index, and object storage under concurrent load.
- **Metrics & Acceptance Gates**:
  - Cross-Tenant Query Leakage $= 0.00\%$ (`INV-TEN-001`, `NFR-TEN-001`)
  - Server-Derived Context Enforcement $= 100.0\%$ (`INV-TEN-002`)
  - Post-Suspension Ingress Rejection $= 100.0\%$ (`AC-010`)
- **Reference**: `docs/13-multi-tenancy/MULTI-TENANCY-SPEC.md` §8.

### 9.2. Suite: `SUITE-P07-CONNECTOR-DRIFT`
- **Objective**: Benchmark schema drift classifier and quarantine isolation against synthetic malformed payloads.
- **Metrics & Acceptance Gates**:
  - Critical Drift Quarantine Rate $= 100.0\%$ (`INV-DATA-002`)
  - Silent Metric Coercion $= 0.00\%$ (Zero semantic alteration)
  - Quarantined Payload Digest Integrity $= 100.0\%$
- **Reference**: `docs/17-connectors/CONNECTOR-PLATFORM-SPEC.md` §5.

### 9.3. Suite: `SUITE-P07-QUOTA-RACE`
- **Objective**: Stress-test atomic spend reservations under 500 concurrent worker threads competing for bounded budget.
- **Metrics & Acceptance Gates**:
  - Over-Allocation Beyond Hard Limit $= \$0.00$ (`INV-COST-001`, `NFR-COST-001`)
  - Race Condition Deadlock $= 0$
  - Multi-Dimensional Attribution Completeness $= 100.0\%$ (`FR-CTL-002`)
- **Reference**: `docs/21-finops/FINOPS-SPEC.md` §2.

### 9.4. Suite: `SUITE-P07-DELETION-CASCADE`
- **Objective**: Validate complete, irreversible cascade purging across all 10 persistent and derived projections.
- **Metrics & Acceptance Gates**:
  - Residual Tenant Records across all stores $= 0$ (`FR-CTL-003`)
  - Legal Hold Blocking Efficacy $= 100.0\%$ (409 Conflict)
  - Deletion Certificate Digest Verification $= 100.0\%$
- **Reference**: `docs/18-data-governance/DATA-GOVERNANCE.md` §4.
