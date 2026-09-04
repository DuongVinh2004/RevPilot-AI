# Test Strategy Specification (Canonical Testing and Verification Contract)

Status: Accepted Canonical Specification
Initiative: REVPILOT
Scope: Verification Strategy, Gate Exit Criteria, and Negative Test Suites (Rails 3–5 Integration)
Owner: Quality Engineering + Security Architecture
Traceability: All `INV-*`, `NFR-*`, `ADR-0001`, `ADR-0004`, `ADR-0005`, `ADR-0009`

---

## 1. Testing Pyramid and Verification Hierarchy

RevPilot strictly mandates automated verification before any micro-task or rail is certified GREEN:

```text
       ▲
      / \     E2E & Chaos / Recovery Suites
     /   \    (Outage matrix, cross-store A/B negative matrix)
    /-----\
   /       \   Contract & Boundary Tests
  /         \  (OpenAPI, EventEnvelope, Outbox, Repository Ports)
 /-----------\
/             \ Module Integration Tests & Security Negative Suites
--------------- (Token verification, delegation limits, RLS enforcement)
Unit Tests (Pure domain invariants, Value Objects, State transitions)
```

---

## 2. Mandatory Negative Test Suites for Rails 3–5

Every rail in the Control Plane sequence requires an exhaustive negative test matrix covering attack vectors and boundary failure modes:

### 2.1. Rail 3 — Authentication Negative Suite (`tests/security/test_authentication_negative.py`)
- Missing Authorization header / missing token.
- Malformed token (non-base64, corrupted JSON, missing required fields).
- Forged signature (tampered payload or invalid verification key).
- Wrong issuer / wrong audience (`aud != 'revpilot-api'`).
- Expired token (`as_of >= exp + 60s`).
- Not yet active token (`as_of < nbf - 60s`).
- Revoked session / revoked token ID.
- Non-system user token lacking `tenant_id` association (`INV-TEN-003`).

### 2.2. Rail 4 — Authorization & Delegation Negative Suite (`tests/security/test_authorization_delegation_negative.py`)
- Cross-tenant resource access (Principal A accessing Tenant B).
- Privilege escalation (Role lacking required action permission).
- Expired AI agent delegation token.
- Revoked AI agent delegation token.
- Delegation attempting to grant permissions exceeding the human delegator.
- AI agent attempting to grant approval (`INV-ACT-003`).
- Unauthorized invocation of privileged platform / break-glass context (`INV-TEN-003`).
- Simulated policy engine timeout failing closed on write/action (`INV-REL-001`).

### 2.3. Rail 5 — Persistence Isolation Negative Suite (`tests/security/test_persistence_isolation_negative.py`)
- Database query executed without establishing tenant context (RLS fails closed, 0 rows).
- Cross-tenant SELECT: Querying Tenant B rows with Tenant A session setting.
- Cross-tenant INSERT: Attempting to insert a row with `tenant_id = 'ten_B'` when session is `ten_A`.
- Cross-tenant UPDATE / DELETE: Attempting to modify Tenant B records from Tenant A session.
- Connection pool reuse: Ensuring session settings do not leak across checked-out connections.
- Migration compatibility: Ensuring backward-compatible DDL changes during expand/contract phases.

---

## 3. Dependency Outage Matrix (`INV-REL-001`)

Tests must prove fail-closed behavior when critical dependencies fail:

| Outage Injected | Read Behavior | Write / Action Behavior | Error Code | Exit Gate Requirement |
|---|---|---|---|---|
| **Identity Service Down** | Denied (401) | Blocked (401) | `AUTHENTICATION_ERROR` | Rail 3 Exit Gate |
| **Policy Service Down** | Degraded read-only | Blocked (403) | `AUTHORIZATION_DENIED` | Rail 4 Exit Gate |
| **Database RLS Unset** | 0 rows returned | Blocked / exception | `RLS_VIOLATION` | Rail 5 Exit Gate |
| **Audit Persistence Down** | Read allowed with warning | High-risk writes blocked | `SERVICE_UNAVAILABLE` | Cross-cutting Gate |

---

## 4. Binary Acceptance Standards

1. **Zero TODOs or Skipped Tests**: Any `@pytest.mark.skip` or commented-out assertion fails CI.
2. **Deterministic Time**: Tests mocking timestamps must use `UtcDateTime` with frozen clocks.
3. **No Network / External IdP**: Test suites must run fully offline using in-memory adapters and local cryptographic fixtures.

---

## 5. Phase 01 Canonical Data and Synthetic Benchmark Test Suites

Phase 01 requires dedicated automated test suites across 18 explicit test categories:

| Category ID | Test Category Name | Target Spec & Rule | Test File Location | Binary Acceptance Standard |
|---|---|---|---|---|
| `TC-P01-001` | Deterministic Seed Reproducibility | `SYNTHETIC-DATASET-SPEC.md` §3 | `tests/benchmark/test_seed_reproducibility.py` | Repeated runs with same seed produce byte-for-byte identical output files. |
| `TC-P01-002` | Manifest Hash Verification | `SYNTHETIC-DATASET-SPEC.md` §3.2 | `tests/benchmark/test_manifest_hashes.py` | 100% of generated artifact SHA-256 hashes match `manifest.json`. |
| `TC-P01-003` | Schema Contract Validation | `CANONICAL-DATA-MODEL.md` §4 | `tests/contract/test_canonical_schema.py` | All canonical entities validate against Pydantic models with 0 validation errors. |
| `TC-P01-004` | Data Type and Range Bounds | `DATA-QUALITY-LINEAGE-SPEC.md` §3.3 | `tests/data_quality/test_range_checks.py` | Negative money, negative quantities, and out-of-bounds percentages fail closed. |
| `TC-P01-005` | Referential Integrity | `DATA-QUALITY-LINEAGE-SPEC.md` §3.4 | `tests/data_quality/test_referential_integrity.py` | Orphan orders/shipments/lines without valid parents are caught and quarantined. |
| `TC-P01-006` | Tenant A/B Negative Isolation | `SYNTHETIC-DATASET-SPEC.md` §4 | `tests/tenancy/test_synthetic_tenant_isolation.py` | Query in `ten_alpha` returns 0 rows for `ten_beta` records. |
| `TC-P01-007` | Hidden Ground-Truth Air-Gap | `SYNTHETIC-DATASET-SPEC.md` §7 | `tests/eval/test_ground_truth_airgap.py` | Runtime role `revpilot_app` has 0 read permission on `ground_truth.incidents`. |
| `TC-P01-008` | Anti-Time-Travel Isolation | `SYNTHETIC-DATASET-SPEC.md` §5 | `tests/benchmark/test_temporal_leakage.py` | Query `as_of` watermark returns 0 records with `event_time > as_of_time`. |
| `TC-P01-009` | No Future Feature Leakage | `INV-DATA-001` | `tests/benchmark/test_feature_leakage.py` | Derived feature matrices contain 0 future data relative to cut-off date. |
| `TC-P01-010` | Effective-Date Correctness | `CANONICAL-DATA-MODEL.md` §3 | `tests/contract/test_effective_date_contracts.py` | Contracts and clauses only resolve if `as_of_time BETWEEN effective_from AND effective_to`. |
| `TC-P01-011` | Late-Event Replay Consistency | `DATA-QUALITY-LINEAGE-SPEC.md` §3.7 | `tests/data_quality/test_late_arrival_replay.py` | Late events arriving within watermark window update state without ledger corruption. |
| `TC-P01-012` | Duplicate Idempotency Handling| `DATA-QUALITY-LINEAGE-SPEC.md` §3.6 | `tests/data_quality/test_duplicate_idempotency.py`| Ingesting identical events multiple times results in exactly 1 persisted canonical row. |
| `TC-P01-013` | Metric Semantic Correctness | `METRIC-REGISTRY.md` §2 | `tests/metrics/test_metric_semantics.py` | All 9 MVP metrics match mathematical definitions on deterministic test fixture. |
| `TC-P01-014` | Data Quality Quarantine | `DATA-QUALITY-LINEAGE-SPEC.md` §5 | `tests/data_quality/test_quarantine_pipeline.py` | Poisoned payloads route to `raw_quarantine` with precise rule error codes. |
| `TC-P01-015` | Lineage Completeness | `DATA-QUALITY-LINEAGE-SPEC.md` §4 | `tests/data_quality/test_lineage_traceability.py` | 100% of canonical records link to valid `lineage_trace_id` and raw payload hash. |
| `TC-P01-016` | Scenario Injection Correctness | `SYNTHETIC-DATASET-SPEC.md` §6 | `tests/benchmark/test_scenario_injection.py` | Midwest truck capacity incident injects expected dispatch delays and cancellation rise. |
| `TC-P01-017` | Control Population Invariant | `SYNTHETIC-DATASET-SPEC.md` §6.2 | `tests/benchmark/test_control_population.py` | Non-Midwest facilities and `ten_beta` remain unaffected at baseline rates. |
| `TC-P01-018` | Scale Profile Reproducibility | `SYNTHETIC-DATASET-SPEC.md` §2 | `tests/benchmark/test_profile_generation.py` | Generator produces correct entity counts for DEVELOPMENT, DEMO, and COMMERCIAL profiles. |

---

## 6. Target vs Measured Discipline

In accordance with `AC-014`:
- No test report, PR review, or documentation file may state "PASS" or report performance metrics unless backed by machine-executed test logs.
- All numbers in specifications are design targets or expected fixture values until an empirical `EvalRun` or pytest execution occurs.

---

## 7. Phase 02 Automated Test Categories (Detection & Analytics)

| Test Category ID | Purpose / Target | Owning Specification | Primary Test File | Acceptance Invariant |
|---|---|---|---|---|
| `TC-P02-001` | Metric Query Semantics | `METRIC-SERVICE-SPEC.md` §2 | `tests/metrics/test_metric_service_queries.py` | Queries return exact mathematical aggregations for registered metrics. |
| `TC-P02-002` | Metric Zero-Volume Handling | `METRIC-SERVICE-SPEC.md` §3 | `tests/metrics/test_metric_zero_volume.py` | 0-denominator returns `actual_value=0.0` and `is_zero_volume_sample=true`. |
| `TC-P02-003` | Metric Temporal As-Of Anti-Leakage| `METRIC-SERVICE-SPEC.md` §1 | `tests/metrics/test_metric_as_of_watermark.py` | Records with `event_time > as_of_time` are 100% invisible. |
| `TC-P02-004` | Metric Dimension Allowlists | `METRIC-SERVICE-SPEC.md` §4 | `tests/metrics/test_metric_dimension_filter.py` | Disallowed dimensions fail closed with `INVALID_DIMENSION_FILTER`. |
| `TC-P02-005` | Tenant Isolation in Metric Queries| `METRIC-SERVICE-SPEC.md` §1 | `tests/security/test_metric_tenant_isolation.py` | Tenant A cannot view or aggregate any records belonging to Tenant B. |
| `TC-P02-006` | Seasonal Naive Baseline | `ANOMALY-BENCHMARK-PROTOCOL.md` §2.1 | `tests/detectors/test_baseline_seasonal_naive.py` | Emits $\hat{Y}_t = Y_{t-7}$ for daily grain with prediction intervals. |
| `TC-P02-007` | Rolling Stats Baseline | `ANOMALY-BENCHMARK-PROTOCOL.md` §2.1 | `tests/detectors/test_baseline_rolling_stats.py` | Evaluates 14-day rolling median and IQR bounds without lookahead. |
| `TC-P02-008` | EWMA Baseline | `ANOMALY-BENCHMARK-PROTOCOL.md` §2.1 | `tests/detectors/test_baseline_ewma.py` | Exponential smoothing tracks baseline trend with $\alpha=0.2$. |
| `TC-P02-009` | Prediction Interval Calibration | `ANOMALY-BENCHMARK-PROTOCOL.md` §3 | `tests/detectors/test_interval_calibration.py` | Nominal 95% interval achieves 93–97% empirical coverage on baseline. |
| `TC-P02-010` | STL Residual Detector | `ANOMALY-BENCHMARK-PROTOCOL.md` §2.2 | `tests/detectors/test_detector_stl_residual.py` | Detects Midwest incident cancellation spike above 3-sigma threshold. |
| `TC-P02-011` | Change-Point PELT Detector | `ANOMALY-BENCHMARK-PROTOCOL.md` §2.2 | `tests/detectors/test_detector_pelt_changepoint.py`| Detects step-level mean shift on Day 45 within 24 hours. |
| `TC-P02-012` | Isolation Forest Detector | `ANOMALY-BENCHMARK-PROTOCOL.md` §2.2 | `tests/detectors/test_detector_isolation_forest.py`| Multi-variate isolation catches joint delay and cancellation anomalies. |
| `TC-P02-013` | Rolling Time-Split Backtest | `ANOMALY-BENCHMARK-PROTOCOL.md` §4 | `tests/eval/test_rolling_timesplit_backtest.py` | 60-day rolling step verifies zero future data leakage. |
| `TC-P02-014` | Detector Lead-Time Verification | `ANOMALY-BENCHMARK-PROTOCOL.md` §3 | `tests/eval/test_detection_lead_time.py` | First alarm triggers within <= 48 hours of Day 45 disruption onset. |
| `TC-P02-015` | False-Positive Rate Control | `ANOMALY-BENCHMARK-PROTOCOL.md` §3 | `tests/eval/test_false_positive_rate.py` | Clean control windows exhibit FPR <= 0.05. |
| `TC-P02-016` | Single-Dimension Localization | `ANOMALY-LOCALIZATION-SPEC.md` §2 | `tests/localization/test_dimension_drilldown.py`| Identifies `CARRIER_REGIONAL_LOGISTICS` as top-1 contributing carrier. |
| `TC-P02-017` | Hierarchical Drill-Down | `ANOMALY-LOCALIZATION-SPEC.md` §4 | `tests/localization/test_hierarchical_drilldown.py`| Pinpoints `WH-MIDWEST-01` within regional carrier slice. |
| `TC-P02-018` | Small-Sample Noise Suppression | `ANOMALY-LOCALIZATION-SPEC.md` §2.2 | `tests/localization/test_noise_suppression.py` | Slices with denominator < 30 are marked `INSUFFICIENT_SAMPLE_SIZE`. |
| `TC-P02-019` | Anomaly Lifecycle Transitions | `ANOMALY-DOMAIN-SPEC.md` §4 | `tests/domain/test_anomaly_lifecycle.py` | State transitions from `DETECTED` to `RESOLVED` follow state machine. |
| `TC-P02-020` | Lifecycle Invariant Enforcement | `ANOMALY-DOMAIN-SPEC.md` §4.1 | `tests/domain/test_anomaly_invariants.py` | Prohibited transitions raise `INVALID_STATE_TRANSITION`. |
| `TC-P02-021` | Late-Event Metric Reconciliation| `DATA-QUALITY-LINEAGE-SPEC.md` §7 | `tests/analytics/test_late_event_recomputation.py`| Recalculates metrics when late events arrive within 7-day buffer. |
| `TC-P02-022` | Anomaly Supersession Integrity | `DATA-QUALITY-LINEAGE-SPEC.md` §7.2 | `tests/analytics/test_anomaly_supersession.py` | Superseded anomalies transition to `SUPPRESSED` without deleting history. |
| `TC-P02-023` | Outbox Event Publishing | `EVENT-CONTRACTS.md` §4 | `tests/contract/test_anomaly_event_contracts.py` | Emits valid `anomaly.*.v1` outbox records on state mutations. |
| `TC-P02-024` | Phase 02 Exit-Gate Composite | `TEST-STRATEGY.md` §7 | `tests/contract/test_phase_02_exit_gate.py` | Composite automated test executing all Phase 02 acceptance criteria. |

---

## 8. Phase 03 Automated Test Categories (Governed Evidence and Investigation)

| Test Category ID | Purpose / Target | Owning Specification | Primary Test File | Acceptance Invariant |
|---|---|---|---|---|
| `TC-P03-001` | Investigation Domain Lifecycle | `TEMPORAL-WORKFLOW-SPEC.md` §4 | `tests/domain/test_investigation_domain.py` | Full state machine (`INITIALIZING` to `COMPLETED`/`NEED_MORE_EVIDENCE`). |
| `TC-P03-002` | Investigation Manifest & Budget | `MULTI-AGENT-SPEC.md` §2.4, §5 | `tests/domain/test_investigation_manifest_budget.py`| Enforces USD 2.00 target, USD 5.00 hard cap, token and tool limits. |
| `TC-P03-003` | Temporal Replay Compatibility | `TEMPORAL-WORKFLOW-SPEC.md` §8 | `tests/recovery/test_investigation_workflow_replay.py`| Historical workflow executions replay without non-deterministic errors. |
| `TC-P03-004` | Worker Crash Loss Prevention | `TEMPORAL-WORKFLOW-SPEC.md` §7 | `tests/recovery/test_recovery_worker_loss_zero_loss.py`| Worker kill mid-investigation resumes on new worker with zero state loss. |
| `TC-P03-005` | Signal & Query Responsiveness | `TEMPORAL-WORKFLOW-SPEC.md` §6 | `tests/workflow/test_investigation_signals_queries.py`| Pause, resume, and cancel signals transition state within 2 seconds. |
| `TC-P03-006` | SQL Capability Catalog Allowlist| `SQL-CAPABILITY-CATALOG.md` §2 | `tests/analytics/test_sql_capability_catalog_allowlist.py`| Only 7 registered capabilities allowed; uncatalogued queries rejected. |
| `TC-P03-007` | SQL Read-Only Hard Barrier | `SQL-CAPABILITY-CATALOG.md` §1 | `tests/security/test_sql_read_only_enforcement.py` | `INSERT`, `UPDATE`, `DELETE`, `DROP` attempts fail closed at DB role level. |
| `TC-P03-008` | SQL Tenant Isolation Negative | `SQL-CAPABILITY-CATALOG.md` §1 | `tests/security/test_sql_tenant_isolation_negative.py`| Queries never return rows belonging to another tenant (`INV-TEN-001`). |
| `TC-P03-009` | SQL As-Of Temporal Anti-Leakage| `SQL-CAPABILITY-CATALOG.md` §3 | `tests/analytics/test_sql_time_travel_anti_leakage.py`| Queries strictly exclude records timestamped after `:as_of_time`. |
| `TC-P03-010` | Evidence Record Schema & Digest | `EVIDENCE-PROVENANCE-SPEC.md` §2 | `tests/contract/test_evidence_record_schema.py` | Validates UUIDv7, SHA-256 digest, enums, timestamps, and citation spans. |
| `TC-P03-011` | Evidence Tenant & ACL Isolation | `EVIDENCE-PROVENANCE-SPEC.md` §1 | `tests/security/test_evidence_tenant_isolation.py` | Tenant A cannot view Tenant B evidence; unpermitted ACL tags fail closed. |
| `TC-P03-012` | Evidence Effective-Date Filter | `EVIDENCE-PROVENANCE-SPEC.md` §4 | `tests/analytics/test_evidence_effective_date.py` | Superseded, expired, or future-dated contract clauses rejected. |
| `TC-P03-013` | Hybrid Retrieval Fusion & Rank | `RAG-SPEC.md` §2 | `tests/ai-evals/test_rag_hybrid_retrieval.py` | RRF fusion merges lexical and dense ranks; Recall@10 >= 0.90. |
| `TC-P03-014` | Citation Exactness & Span Match | `RAG-SPEC.md` §2 | `tests/ai-evals/test_rag_citation_precision.py` | Citation spans match source byte offsets; precision >= 0.95. |
| `TC-P03-015` | Document Prompt Injection Def | `RAG-SPEC.md` §4 | `tests/security/test_rag_prompt_injection_defense.py`| Adversarial prompt injection text in documents fails to hijack agent. |
| `TC-P03-016` | Ticket Ingestion PII Redaction | `TICKET-INTELLIGENCE-SPEC.md` §3 | `tests/security/test_ticket_dlp_redaction.py` | Credit cards, tax IDs, secrets, and raw emails masked on ingest. |
| `TC-P03-017` | Ticket Untrusted Content Bound | `TICKET-INTELLIGENCE-SPEC.md` §1 | `tests/security/test_ticket_prompt_injection.py` | Injected support ticket text cannot grant authority or call tools. |
| `TC-P03-018` | Planner Acyclic DAG Validation | `MULTI-AGENT-SPEC.md` §4 | `tests/domain/test_planner_dag_validation.py` | Validates DAG acyclicity, max depth 4, max fan-out 8, max 20 tasks. |
| `TC-P03-019` | Verifier Unsupported Claim Rej | `MULTI-AGENT-SPEC.md` §6 | `tests/ai-evals/test_unsupported_claim_rejection.py`| Rejects claims lacking valid evidence; 0.00% unsupported claims allowed. |
| `TC-P03-020` | Verifier Contradiction Handling | `MULTI-AGENT-SPEC.md` §6 | `tests/ai-evals/test_contradiction_detection.py` | Hypotheses contradicted by evidence are marked `REFUTED`. |
| `TC-P03-021` | Verifier NEED_MORE_EVIDENCE Fall| `MULTI-AGENT-SPEC.md` §6 | `tests/ai-evals/test_need_more_evidence_fallback.py`| Evidence gaps cause deterministic fallback to `NEED_MORE_EVIDENCE`. |
| `TC-P03-022` | Phase 03 Mutation Barrier Gate | `TOOL-GATEWAY-SPEC.md` §4 | `tests/security/test_phase03_mutation_barrier.py` | Action/mutation capabilities fail closed with `ERR_MUTATION_BLOCKED`. |
| `TC-P03-023` | Chain-of-Thought Suppression | `MULTI-AGENT-SPEC.md` §1 | `tests/security/test_suppress_chain_of_thought.py` | API and UI traces expose evidence and decisions, zero hidden CoT (`AC-013`). |
| `TC-P03-024` | Phase 03 Exit-Gate Composite | `TEST-STRATEGY.md` §8 | `tests/contract/test_phase_03_exit_gate.py` | Composite automated test executing all Phase 03 acceptance criteria. |

---

## 9. Phase 04 Automated Test Categories (Hypothesis, Causal Analysis, and Verification)

| Test Category ID | Purpose / Target | Owning Specification | Primary Test File | Acceptance Invariant |
|---|---|---|---|---|
| `TC-P04-001` | Hypothesis Record & Taxonomy | `HYPOTHESIS-VERIFIER-SPEC.md` §2 | `tests/domain/test_hypothesis_domain.py` | Schema validation, epistemic categories, field invariants. |
| `TC-P04-002` | Dual Evidence Binding | `HYPOTHESIS-VERIFIER-SPEC.md` §2 | `tests/domain/test_hypothesis_evidence_binding.py` | Supporting and contradicting evidence explicitly linked. |
| `TC-P04-003` | Competing-Cause Ranking Engine | `HYPOTHESIS-VERIFIER-SPEC.md` §3 | `tests/ai-evals/test_competing_hypothesis_ranking.py` | Multi-hypothesis scoring, ordinal ranking, tie-breaking. |
| `TC-P04-004` | Contradiction Veto & Decoys | `HYPOTHESIS-VERIFIER-SPEC.md` §3 | `tests/ai-evals/test_decoy_hypothesis_refutation.py` | 100% refutation of payment outage and product defect decoys. |
| `TC-P04-005` | NEED_MORE_EVIDENCE Fallback | `HYPOTHESIS-VERIFIER-SPEC.md` §3 | `tests/ai-evals/test_need_more_evidence_fallback.py` | Coverage < 0.75 or ambiguous evidence yields `NEED_MORE_EVIDENCE`. |
| `TC-P04-006` | Hypothesis Tenant Isolation Neg | `HYPOTHESIS-VERIFIER-SPEC.md` §5 | `tests/security/test_hypothesis_tenant_isolation.py` | Tenant A cannot view or cite Tenant B hypotheses or evidence. |
| `TC-P04-007` | Claim Taxonomy Classification | `UNSUPPORTED-CLAIM-POLICY.md` §2 | `tests/domain/test_claim_taxonomy.py` | 6 formal claim categories classified deterministically. |
| `TC-P04-008` | Verifier Citation Span Match | `UNSUPPORTED-CLAIM-POLICY.md` §3 | `tests/ai-evals/test_claim_citation_match.py` | Verified claims match source text byte offsets exactly. |
| `TC-P04-009` | Unprovenanced Evidence Reject | `UNSUPPORTED-CLAIM-POLICY.md` §3 | `tests/ai-evals/test_unprovenanced_evidence_rejection.py` | Missing digest or superseded evidence rejected (`INV-EVD-001..002`). |
| `TC-P04-010` | Correlation as Causation Reject | `UNSUPPORTED-CLAIM-POLICY.md` §3 | `tests/ai-evals/test_correlation_causation_rejection.py` | Rejects causal assertions backed only by association ($r \ne 0$). |
| `TC-P04-011` | Churn Risk as Uplift Reject | `UNSUPPORTED-CLAIM-POLICY.md` §3 | `tests/ai-evals/test_churn_uplift_conflation_rejection.py`| Baseline churn risk cannot be claimed as treatment effect. |
| `TC-P04-012` | Claim Lookahead Leakage Reject | `UNSUPPORTED-CLAIM-POLICY.md` §3 | `tests/analytics/test_claim_temporal_leakage.py` | Records timestamped after `:as_of_time` rejected (`INV-DATA-001`). |
| `TC-P04-013` | Causal Study Data Contract | `CAUSAL-INFERENCE-SPEC.md` §2 | `tests/contract/test_causal_study_contract.py` | Estimand, treatment, outcome, unit, and population validation. |
| `TC-P04-014` | Collider & Post-Treatment Reject| `CAUSAL-INFERENCE-SPEC.md` §2 | `tests/analytics/test_causal_collider_rejection.py` | Post-treatment mediators barred from pre-treatment covariate set. |
| `TC-P04-015` | Positivity & Overlap Gate | `CAUSAL-INFERENCE-SPEC.md` §2 | `tests/analytics/test_causal_overlap_diagnostics.py` | Positivity failure ($e(X) < 0.05$) halts study fail-closed. |
| `TC-P04-016` | Doubly Robust AIPW Estimator | `CAUSAL-INFERENCE-SPEC.md` §4 | `tests/analytics/test_causal_aipw_estimator.py` | Mathematical precision of AIPW against known DGP formulation. |
| `TC-P04-017` | CI & Uncertainty Calibration | `CAUSAL-INFERENCE-SPEC.md` §3 | `tests/analytics/test_causal_interval_calibration.py` | 95% confidence interval coverage verified across synthetic runs. |
| `TC-P04-018` | Sensitivity Bounds (E-value) | `CAUSAL-INFERENCE-SPEC.md` §3 | `tests/ai-evals/test_causal_sensitivity_bounds.py` | E-value and Oster delta correctly identify robust vs fragile effects. |
| `TC-P04-019` | Synthetic Causal Benchmark ATE | `CAUSAL-BENCHMARK-PROTOCOL.md` §3 | `tests/ai-evals/test_causal_synthetic_ate_benchmark.py` | $|\widehat{\text{ATE}} - 0.0660| \le 0.0500$ on Midwest incident (`NFR-AI-007`). |
| `TC-P04-020` | Ground-Truth Schema Air-Gap | `SYNTHETIC-DATASET-SPEC.md` §7 | `tests/security/test_ground_truth_airgap_isolation.py` | `revpilot_app` denied access to `ground_truth` schema (`AC-014`). |
| `TC-P04-021` | Zero Action Escalation Barrier | `SECURITY-ARCHITECTURE.md` §6 | `tests/security/test_causal_action_barrier.py` | Causal outputs barred from issuing approvals or calling write tools. |
| `TC-P04-022` | Bitwise Study Replay Verification| `CAUSAL-INFERENCE-SPEC.md` §2 | `tests/analytics/test_causal_study_replay.py` | Study re-execution produces bitwise identical point estimate & digest. |
| `TC-P04-023` | CoT Suppression in Causal APIs | `UNSUPPORTED-CLAIM-POLICY.md` §1 | `tests/security/test_suppress_chain_of_thought.py` | Zero raw model CoT exposed in public responses (`AC-013`). |
| `TC-P04-024` | Phase 04 Exit-Gate Composite | `TEST-STRATEGY.md` §9 | `tests/contract/test_phase_04_exit_gate.py` | Composite execution of all Phase 04 automated exit criteria. |

---

## 10. Phase 05 Automated Test Categories (Churn, Uplift, and Decision Optimization)

| Test Category ID | Purpose / Target | Owning Specification | Primary Test File | Acceptance Invariant |
|---|---|---|---|---|
| `TC-P05-001` | Churn Model Training & Inference | `ML-SYSTEM-SPEC.md` §5.1 | `tests/ml/test_churn_model_contract.py` | Validates GBDT model inference, schema, and output bounds. |
| `TC-P05-002` | Probability Calibration Curve | `ML-SYSTEM-SPEC.md` §5.2 | `tests/ml/test_probability_calibration.py` | Platt / Isotonic scaling maps scores to monotonic probabilities. |
| `TC-P05-003` | ECE Calibration Standard | `ML-SYSTEM-SPEC.md` §5.2 | `tests/ai-evals/test_churn_ece_benchmark.py` | ECE <= 0.0500 on time-split holdout test set (`NFR-AI-005`). |
| `TC-P05-004` | Churn Censoring & Contamination | `ML-SYSTEM-SPEC.md` §5.1 | `tests/analytics/test_churn_censoring.py` | Treated accounts censored from unadjusted churn evaluations. |
| `TC-P05-005` | Churn Feature Lookahead Leakage | `ML-SYSTEM-SPEC.md` §5.1 | `tests/analytics/test_churn_temporal_leakage.py`| Zero features computed with data after `:as_of_time` (`INV-DATA-001`).|
| `TC-P05-006` | Local SHAP Value Computation | `ML-SYSTEM-SPEC.md` §6.1 | `tests/ml/test_shap_local_explanations.py` | SHAP attributions sum to marginal score; epistemic warning attached. |
| `TC-P05-007` | SHAP Causation Fallacy Rejection| `ML-SYSTEM-SPEC.md` §6.1 | `tests/ai-evals/test_shap_causation_rejection.py`| Barred from asserting SHAP factor caused churn (`INV-AI-001`). |
| `TC-P05-008` | SHAP PII Masking & Determinism | `ML-SYSTEM-SPEC.md` §6.2 | `tests/security/test_shap_pii_redaction.py` | Zero raw PII in attributions; feature-order ranking is deterministic.|
| `TC-P05-009` | Uplift Model CATE Contract | `UPLIFT-BENCHMARK-PROTOCOL.md` §2 | `tests/contract/test_uplift_score_contract.py` | Schema validation, persuadability segments, CATE intervals. |
| `TC-P05-010` | Uplift Overlap Diagnostics | `UPLIFT-BENCHMARK-PROTOCOL.md` §4 | `tests/analytics/test_uplift_overlap_diagnostics.py`| Halts with `ERR_OVERLAP_VIOLATION` on unrepresented cohorts. |
| `TC-P05-011` | Uplift Qini Metric Benchmark | `UPLIFT-BENCHMARK-PROTOCOL.md` §4 | `tests/ai-evals/test_uplift_qini_benchmark.py` | Normalized Qini > 0.2000; beats random targeting (`NFR-AI-006`). |
| `TC-P05-012` | Sleeping Dog Detection Sensitivity| `UPLIFT-BENCHMARK-PROTOCOL.md` §3 | `tests/ai-evals/test_uplift_negative_effect_detection.py`| Identifies negative-uplift cohort ($\ge 95\%$) and blocks treatment. |
| `TC-P05-013` | Budget Ledger Atomic Reservation | `BUDGET-CONSTRAINT-SPEC.md` §4 | `tests/domain/test_budget_ledger_concurrency.py` | Optimistic concurrency control prevents concurrent budget overdrafts.|
| `TC-P05-014` | Hard Budget Ceiling Enforcement | `BUDGET-CONSTRAINT-SPEC.md` §2 | `tests/domain/test_budget_constraint_evaluation.py`| Excluded immediately if cost > remaining balance (`INV-COST-001`).|
| `TC-P05-015` | Customer Cooldown & Frequency | `BUDGET-CONSTRAINT-SPEC.md` §2 | `tests/domain/test_cooldown_frequency_caps.py` | Contact within 14d or frequency cap breach filters candidate. |
| `TC-P05-016` | Customer Consent & Opt-Out | `BUDGET-CONSTRAINT-SPEC.md` §2 | `tests/security/test_customer_opt_out_enforcement.py`| Opted-out accounts filtered before expected utility ranking. |
| `TC-P05-017` | Fail-Closed on Unknown Policy | `BUDGET-CONSTRAINT-SPEC.md` §1.1 | `tests/domain/test_constraint_fail_closed.py` | Missing policy data returns `ERR_POLICY_UNKNOWN` and abstains. |
| `TC-P05-018` | 12-Step Pipeline Ordering | `DECISION-ENGINE-SPEC.md` §2 | `tests/domain/test_decision_pipeline_ordering.py`| Invariants guarantee hard constraints run before utility ranking. |
| `TC-P05-019` | Expected Utility Mathematical Acc| `DECISION-ENGINE-SPEC.md` §3 | `tests/domain/test_expected_utility_optimizer.py`| Net benefit, costs, risk penalties, and uncertainty evaluated exactly.|
| `TC-P05-020` | Negative Utility Abstention | `DECISION-ENGINE-SPEC.md` §3 | `tests/domain/test_negative_utility_abstention.py`| Negative expected utility yields status `ABSTAINED`. |
| `TC-P05-021` | Zero External Action Barrier | `DECISION-ENGINE-SPEC.md` §1.1 | `tests/security/test_decision_action_barrier.py` | Output is recommendation artifact; write tool execution physically barred.|
| `TC-P05-022` | Slice Disparity & Noise Suppress| `FAIRNESS-SLICE-EVALUATION.md` §3 | `tests/ai-evals/test_fairness_slice_evaluation.py` | Slices with $N < 50$ marked `INSUFFICIENT_SAMPLE` and suppressed. |
| `TC-P05-023` | Decision Digest Bitwise Replay | `DECISION-ENGINE-SPEC.md` §4 | `tests/domain/test_decision_digest_replay.py` | Re-running decision against frozen snapshot reproduces digest. |
| `TC-P05-024` | Phase 05 Exit-Gate Composite | `TEST-STRATEGY.md` §10 | `tests/contract/test_phase_05_exit_gate.py` | Composite execution of all Phase 05 automated acceptance criteria. |

---

## 11. Phase 06 Automated Test Categories (Approval and Safe Action Loop)

| Test Category ID | Purpose / Target | Owning Specification | Primary Test File | Acceptance Invariant |
|---|---|---|---|---|
| `TC-P06-001` | Approval Creation & Digest | `APPROVAL-ACTION-LOOP-SPEC.md` §3.1 | `tests/domain/test_approval_request_creation.py` | Validates schema, pending status, and SHA-256 payload digest. |
| `TC-P06-002` | Tampered Payload Rejection | `APPROVAL-ACTION-LOOP-SPEC.md` §1.1 | `tests/security/test_approval_tamper_payload.py` | Altered payload fails verification with `ERR_APPROVAL_DIGEST_MISMATCH`. |
| `TC-P06-003` | Tampered Target Set Rejection | `APPROVAL-ACTION-LOOP-SPEC.md` §1.1 | `tests/security/test_approval_tamper_targets.py` | Changing target accounts invalidates digest and blocks approval. |
| `TC-P06-004` | Expired Approval Rejection | `APPROVAL-ACTION-LOOP-SPEC.md` §1.1 | `tests/domain/test_approval_expiration.py` | Requests past 24h TTL transition to `EXPIRED` and fail closed. |
| `TC-P06-005` | Revoked Approval Rejection | `APPROVAL-ACTION-LOOP-SPEC.md` §1.1 | `tests/domain/test_approval_revocation.py` | Revoked approval request rejects subsequent action intents. |
| `TC-P06-006` | Replayed Approval Rejection | `APPROVAL-ACTION-LOOP-SPEC.md` §1.1 | `tests/security/test_approval_replay_protection.py`| Reusing an already-executed approval ID fails closed (`ERR_ALREADY_USED`).|
| `TC-P06-007` | Unauthorized Tier Rejection | `IAM-SPEC.md` §7.1 | `tests/security/test_approval_tier_authority.py` | Tier-1 approver attempting to approve $500 action rejected (403). |
| `TC-P06-008` | Cross-Tenant Approval Rejection| `APPROVAL-ACTION-LOOP-SPEC.md` §1.1 | `tests/security/test_approval_tenant_isolation.py` | Tenant A principal cannot view or approve Tenant B requests (`INV-TEN-001`).|
| `TC-P06-009` | Agent Self-Approval Strict Rej | `IAM-SPEC.md` §7.2 | `tests/security/test_agent_self_approval_block.py` | AI agent principal calling approve endpoint fails closed (403). |
| `TC-P06-010` | Amendment Invalidation | `APPROVAL-ACTION-LOOP-SPEC.md` §1.1 | `tests/domain/test_approval_amendment_lifecycle.py`| Amending parameters supersedes old approval and requires re-signing. |
| `TC-P06-011` | Six-Point Policy Revalidation | `APPROVAL-ACTION-LOOP-SPEC.md` §1.1 | `tests/domain/test_policy_revalidation_pipeline.py`| Policy re-checked at all 6 lifecycle checkpoints before dispatch. |
| `TC-P06-012` | Dry-Run Logic Parity | `TOOL-GATEWAY-SPEC.md` §7.3 | `tests/contract/test_dry_run_parity.py` | Dry-run and real execution run identical validation rules. |
| `TC-P06-013` | Dry-Run Zero Socket Mutation | `TOOL-GATEWAY-SPEC.md` §7.3 | `tests/security/test_dry_run_zero_side_effect.py` | Verifies zero outbound external socket connections during dry run. |
| `TC-P06-014` | Action Intent Idempotency | `APPROVAL-ACTION-LOOP-SPEC.md` §3.2 | `tests/domain/test_action_intent_idempotency.py` | Re-submitting identical idempotency key returns existing record. |
| `TC-P06-015` | Action Ledger State Progression | `APPROVAL-ACTION-LOOP-SPEC.md` §3.3 | `tests/domain/test_action_ledger_progression.py` | Transitions cleanly from `STARTED` to `SUCCESS` or `UNKNOWN`. |
| `TC-P06-016` | Credential Broker Token Scoping| `TOOL-GATEWAY-SPEC.md` §7.2 | `tests/security/test_credential_broker_scoping.py` | Ephemeral tokens have <= 15m TTL and strict tenant/action scope. |
| `TC-P06-017` | Zero Secret in Payload / Logs | `TOOL-GATEWAY-SPEC.md` §7.2 | `tests/security/test_scrub_secrets_from_ledger.py`| 100% of tokens/secrets scrubbed from ledgers and audit logs. |
| `TC-P06-018` | No Direct Agent Network Egress | `TOOL-GATEWAY-SPEC.md` §7.2 | `tests/security/test_agent_egress_containment.py` | Agent sandbox environment cannot initiate outbound connections. |
| `TC-P06-019` | Kill Switch Rapid Halting | `APPROVAL-ACTION-LOOP-SPEC.md` §5.1 | `tests/security/test_kill_switch_propagation.py` | Active kill switch halts execution across cluster in < 500ms. |
| `TC-P06-020` | Blast Radius Spend & Entity Lim | `APPROVAL-ACTION-LOOP-SPEC.md` §5.2 | `tests/domain/test_blast_radius_enforcement.py` | Exceeding 500 entities or $250 tier limit blocks automated dispatch. |
| `TC-P06-021` | Saga Forward & Compensating | `TEMPORAL-WORKFLOW-SPEC.md` §10.1 | `tests/workflow/test_saga_compensation_flow.py` | Multi-step failure rolls back prior steps in reverse order. |
| `TC-P06-022` | Irreversible Action Guard | `APPROVAL-ACTION-LOOP-SPEC.md` §4.2 | `tests/domain/test_irreversible_action_guard.py` | Irreversible actions barred from automated rollback; alerts SRE. |
| `TC-P06-023` | UNKNOWN Blind Retry Prohibit | `APPROVAL-ACTION-LOOP-SPEC.md` §4.1 | `tests/recovery/test_unknown_blind_retry_prohibit.py`| Network timeout stops blind retries and flags `UNKNOWN` (`NFR-REL-001`).|
| `TC-P06-024` | UNKNOWN Status Reconciliation | `APPROVAL-ACTION-LOOP-SPEC.md` §4.1 | `tests/recovery/test_unknown_provider_reconciliation.py`| Queries provider status by transaction ID before taking further step. |
| `TC-P06-025` | Action Completed Outbox Event | `EVENT-CONTRACTS.md` §8 | `tests/contract/test_action_event_contracts.py` | Publishes schema-valid `action.completed.v1` upon provider success. |
| `TC-P06-026` | Action Outcome Revenue Capture | `APPROVAL-ACTION-LOOP-SPEC.md` §2 | `tests/domain/test_action_outcome_measurement.py`| Records actual observed GMV/retention and computes net ROI. |
| `TC-P06-027` | Temporal Crash Recovery Dispatch| `TEMPORAL-WORKFLOW-SPEC.md` §10.1 | `tests/recovery/test_action_workflow_crash_recovery.py`| Worker death mid-action recovers gracefully via Temporal history. |
| `TC-P06-028` | Phase 06 Exit-Gate Composite | `TEST-STRATEGY.md` §11 | `tests/contract/test_phase_06_exit_gate.py` | Composite execution of all Phase 06 automated acceptance criteria. |

---

## 12. Phase 07 Automated Test Categories (Multi-Tenant Pilot, Connectors, Operations)

| Test Category ID | Purpose / Target | Owning Specification | Primary Test File | Acceptance Invariant |
|---|---|---|---|---|
| `TC-P07-001` | Tenant Provisioning Idempotency | `TENANT-OPERATIONS-SPEC.md` §3.1 | `tests/tenancy/test_tenant_provisioning_idempotency.py` | Repeated provisioning calls yield consistent state without duplicates. |
| `TC-P07-002` | Partial Provisioning Rejection | `TENANT-OPERATIONS-SPEC.md` §3.2 | `tests/tenancy/test_partial_provisioning_blocked.py` | Failure at any resource allocation step rolls back and blocks activation. |
| `TC-P07-003` | Activation Precondition Check | `TENANT-OPERATIONS-SPEC.md` §3.3 | `tests/tenancy/test_tenant_activation_preconditions.py` | Tenant cannot activate without 100% passing isolation probes. |
| `TC-P07-004` | Suspension Ingress Halting | `TENANT-OPERATIONS-SPEC.md` §3.4 | `tests/tenancy/test_tenant_suspension_enforcement.py` | Suspended tenant receives 403 on all ingress and tool actions. |
| `TC-P07-005` | Reactivation Verification | `TENANT-OPERATIONS-SPEC.md` §3.5 | `tests/tenancy/test_tenant_reactivation_flow.py` | Resolving suspension cause restores active state with full audit proof. |
| `TC-P07-006` | Cross-Tenant Negative Matrix | `MULTI-TENANCY-SPEC.md` §8 | `tests/tenancy/test_cross_tenant_isolation_matrix.py` | 100% pass rate across all 11 cross-tenant negative isolation vectors (`TEST-TEN-001..011`). |
| `TC-P07-007` | Tenant Export Isolation | `DATA-GOVERNANCE.md` §3 | `tests/governance/test_tenant_export_isolation.py` | Export bundle contains zero records or metadata of other tenants. |
| `TC-P07-008` | Cascade Deletion Propagation | `DATA-GOVERNANCE.md` §4 | `tests/governance/test_cascade_deletion_propagation.py` | Deletion purges across SQL, vector, cache, S3, and Temporal. |
| `TC-P07-009` | Legal Hold Deletion Block | `TENANT-OPERATIONS-SPEC.md` §3.6 | `tests/governance/test_legal_hold_deletion_block.py` | Deletion requests on tenants under legal hold fail closed (409). |
| `TC-P07-010` | OIDC Token Expiry and Skew | `ENTERPRISE-IDENTITY-INTEGRATION-SPEC.md` §2.2 | `tests/security/test_oidc_token_expiration.py` | Expired tokens (>60s skew) fail validation with 401. |
| `TC-P07-011` | OIDC JWKS Key Rotation | `ENTERPRISE-IDENTITY-INTEGRATION-SPEC.md` §2.2 | `tests/security/test_oidc_jwks_rotation.py` | Dynamic fetch of new JWKS key succeeds without system downtime. |
| `TC-P07-012` | OIDC Invalid Issuer / Audience | `ENTERPRISE-IDENTITY-INTEGRATION-SPEC.md` §2.2 | `tests/security/test_oidc_issuer_audience_mismatch.py` | Mismatched issuer or audience fails closed immediately. |
| `TC-P07-013` | OIDC Token Replay Protection | `ENTERPRISE-IDENTITY-INTEGRATION-SPEC.md` §2.2 | `tests/security/test_oidc_token_replay.py` | Duplicate JTI submission within token lifetime is blocked (401). |
| `TC-P07-014` | SAML Signature & XSW Mitigation | `ENTERPRISE-IDENTITY-INTEGRATION-SPEC.md` §3.1 | `tests/security/test_saml_signature_verification.py` | Forged signatures or XML wrapping attacks are rejected. |
| `TC-P07-015` | SCIM Rapid Deprovisioning | `ENTERPRISE-IDENTITY-INTEGRATION-SPEC.md` §4.2 | `tests/security/test_scim_deprovisioning_revocation.py` | SCIM deactivation terminates user sessions within 1000ms. |
| `TC-P07-016` | Connector Secret Zero Exposure | `CONNECTOR-PLATFORM-SPEC.md` §1.1 | `tests/security/test_connector_secret_scrubbing.py` | Secret references never resolve to raw values in logs or payloads. |
| `TC-P07-017` | Connector Auth Expiry Transition | `CONNECTOR-PLATFORM-SPEC.md` §3.1 | `tests/connectors/test_connector_auth_expiry_handling.py` | 401 from provider transitions connector to `AUTH_EXPIRED`. |
| `TC-P07-018` | Webhook Signature Verification | `CONNECTOR-PLATFORM-SPEC.md` §4.1 | `tests/connectors/test_webhook_signature_verification.py` | HMAC-SHA256 signature verification blocks forged webhooks. |
| `TC-P07-019` | Webhook Replay Deduplication | `CONNECTOR-PLATFORM-SPEC.md` §4.1 | `tests/connectors/test_webhook_replay_deduplication.py` | Duplicate external event IDs return 200 without reprocessing. |
| `TC-P07-020` | Webhook Out-of-Order Handling | `CONNECTOR-PLATFORM-SPEC.md` §4.1 | `tests/connectors/test_webhook_out_of_order_resolution.py` | Older timestamped updates do not overwrite newer canonical state. |
| `TC-P07-021` | Schema Drift Quarantine | `CONNECTOR-PLATFORM-SPEC.md` §5 | `tests/connectors/test_schema_drift_quarantine.py` | Incompatible payloads diverted to `connector_quarantine` table. |
| `TC-P07-022` | Quota Race Atomic Reservation | `FINOPS-SPEC.md` §2.2 | `tests/finops/test_quota_atomic_reservation_race.py` | Concurrent threads competing for final quota serialize cleanly. |
| `TC-P07-023` | Multi-Dimensional Attribution | `FINOPS-SPEC.md` §1.1 | `tests/finops/test_usage_attribution_integrity.py` | 100% of usage attributed to tenant, principal, and investigation. |
| `TC-P07-024` | Cost Reconciliation Matching | `FINOPS-SPEC.md` §4 | `tests/finops/test_cost_reconciliation_protocol.py` | Reconciles usage against synthetic provider bills within 2% variance. |
| `TC-P07-025` | Audit Hash Chain Integrity | `AUDIT-LOG-SPEC.md` §3 | `tests/security/test_audit_hash_chain_integrity.py` | SHA-256 tamper detection alerts on any modified audit record. |
| `TC-P07-026` | Dependency Outage Fail-Closed | `SRE-SPEC.md` §1 | `tests/recovery/test_dependency_outage_fail_closed.py` | Tenancy service timeout blocks all sensitive write actions. |
| `TC-P07-027` | Pilot Disaster Recovery Restore | `DR-PLAN.md` §2 | `tests/recovery/test_pilot_disaster_recovery_restore.py` | Database PITR and secondary projection rebuild passes in < 30min. |
| `TC-P07-028` | Phase 07 Exit-Gate Composite | `TEST-STRATEGY.md` §12 | `tests/contract/test_phase_07_exit_gate.py` | Composite execution of all Phase 07 acceptance criteria. |

### 12.1 Phase 07 Exit Criteria
Phase 07 satisfies its exit gate only when:
1. `TC-P07-001..028` automated test suite executes with 100% passing status.
2. Cross-tenant isolation matrix (`TEST-TEN-001..011`) reports 0 cross-tenant leaks.
3. Live pilot rehearsals `REH-P07-01..07` are executed and signed off in staging.
4. Zero P0/P1 security findings remain open in the risk register.
5. Production action adapters remain disabled until explicitly approved in Phase 08.

---

## 13. Phase 08 Production Readiness, Load, Stress, and Chaos Strategy

> [!CAUTION]
> Destructive chaos testing, resource blackholing, and high-intensity stress tests are strictly restricted to isolated staging environments. Running destructive chaos experiments against live production clusters is prohibited.

### 13.1 Specialized Non-Functional Test Suites

| Category | Workload Profile | Target Environment | Dataset & Topology | Pass Criteria | Safety Guardrail | Evidence Artifact | Owner | Status |
|---|---|---|---|---|---|---|---|---|
| **Load** | 1,000 req/s sustained for 2 hours | Staging Isolated | 50 Synthetic Tenants | P95 latency $\le 800$ms, Error rate $\le 0.1\%$ | Rate-limiter enabled | `evidence/load-test-report.html` | SRE Lead | PLANNED |
| **Spike** | 0 to 5,000 req/s over 30 seconds | Staging Isolated | 100 Synthetic Tenants | Auto-scaling boots pods; 0 crash | Max 20 pod ceiling | `evidence/spike-test-report.json` | SRE Lead | PLANNED |
| **Soak** | 500 req/s continuous for 72 hours | Staging Isolated | 20 Synthetic Tenants | Heap memory slope flat ($\le 5\%$ drift); 0 leaks | OOM killer active | `evidence/soak-test-72h.log` | SRE Lead | NOT EXECUTED |
| **Stress** | Connection pool saturation (500 conns) | Staging Isolated | 10 Synthetic Tenants | Graceful queuing; zero zombie locks | Max connection 600 | `evidence/db-stress-pool.log` | DB Admin | PLANNED |
| **Failover** | Forced primary DB node termination | Staging Multi-AZ | 10 Synthetic Tenants | Replica promoted $\le 60$s; RPO $= 0$ | Multi-AZ replica synced| `evidence/db-failover-run.log` | SRE Lead | PLANNED |
| **Chaos** | 300ms network jitter + 20% packet drop| Staging Isolated | 5 Synthetic Tenants | Workflows tolerate retry; 0 data loss | Isolated VPC only | `evidence/chaos-network-test.json`| SRE Lead | PLANNED |
| **Blackhole**| Secret Broker socket blackholed | Staging Isolated | 5 Synthetic Tenants | 100% External actions fail closed | Tool Gateway mock only| `evidence/secret-blackhole.log` | SecOps Lead | PLANNED |

### 13.2 Phase 08 Automated Test Matrix (`TC-P08-001..028`)

| Test ID | Test Name | Target Requirement | Primary Test File | Acceptance Criteria |
|---|---|---|---|---|
| `TC-P08-001` | High-Concurrency RLS Under Load | `INV-TEN-001`, `NFR-TEN-002` | `tests/load/test_rls_concurrency_isolation.py` | 0 leaked rows under 500 concurrent threads. |
| `TC-P08-002` | Token Expiry Active Invalidation | `INV-IAM-001`, `NFR-SEC-001` | `tests/security/test_session_active_invalidation.py`| Revocation invalidates sessions globally $< 1000$ms. |
| `TC-P08-003` | Secret Rotation Zero Downtime | `ADR-0009`, `NFR-SEC-002` | `tests/security/test_secret_zero_downtime_rotation.py`| Rotation of KMS keys causes 0 failed API calls. |
| `TC-P08-004` | Outbound Mutation Gateway Wall | `INV-SEC-003`, `FR-ACT-001` | `tests/security/test_connector_egress_wall.py` | Direct outbound internet requests blocked by policy. |
| `TC-P08-005` | Temporal Worker SIGKILL Resilience | `INV-WF-001`, `NFR-DUR-001` | `tests/recovery/test_temporal_sigkill_recovery.py` | Worker death mid-step resumes cleanly from event log. |
| `TC-P08-006` | Saga Reverse Order Compensation | `INV-WF-002`, `AC-013` | `tests/recovery/test_saga_reverse_compensation.py` | Multi-step failure rolls back executed steps in reverse. |
| `TC-P08-007` | Digest Tampering Rejection | `INV-ACT-002`, `AC-008` | `tests/security/test_approval_digest_tampering.py` | 1-bit payload modification rejects approval token. |
| `TC-P08-008` | Agent Privilege Escalation Block | `INV-ACT-003`, `INV-IAM-002` | `tests/security/test_agent_privilege_escalation.py`| Agent token barred from self-approving actions. |
| `TC-P08-009` | Immutable Ledger Append Enforce | `INV-ACT-004`, `AC-012` | `tests/domain/test_ledger_immutability_enforcement.py`| Database trigger blocks `UPDATE` or `DELETE` on ledger. |
| `TC-P08-010` | 100% Unsampled Audit Stream | `INV-AUD-001`, `NFR-AUD-001` | `tests/security/test_audit_stream_zero_drop.py` | Zero audit events dropped during high ingestion load. |
| `TC-P08-011` | Automated PII Redaction Audit | `INV-AUD-002`, `INV-PRV-001` | `tests/privacy/test_audit_pii_redaction.py` | Regex DLP confirms 0 PII in 10,000 sample records. |
| `TC-P08-012` | Citation Provenance Verification | `INV-EVD-001`, `AC-005` | `tests/eval/test_citation_provenance_integrity.py` | 100% claims link back to valid data rows or spans. |
| `TC-P08-013` | Future-Dated Query Temporal Block | `INV-DATA-001` | `tests/data/test_future_dated_record_block.py` | Queries with `:as_of_time` reject newer records. |
| `TC-P08-014` | Post-Deletion 10-Store Scrub | `FR-CTL-003`, `INV-TEN-001` | `tests/governance/test_post_deletion_scrub.py` | Post-deletion multi-store query returns 0 rows. |
| `TC-P08-015` | Legal Hold 409 Conflict Enforce | `FR-CTL-003` | `tests/governance/test_legal_hold_rejection.py` | Deletion request on hold-locked tenant fails (409). |
| `TC-P08-016` | W3C Distributed Trace Linkage | `NFR-OBS-001` | `tests/observability/test_trace_correlation_linkage.py`| Span context propagated across HTTP, queue, worker. |
| `TC-P08-017` | Zero Telemetry Drop Under Load | `NFR-OBS-002` | `tests/observability/test_telemetry_pipeline_load.py` | High-priority security traces experience 0 drop. |
| `TC-P08-018` | Kill-Switch Halt Latency $< 500$ms | `INV-REL-001`, `AC-008` | `tests/recovery/test_kill_switch_propagation.py` | All workers halt tool invocations within 500ms. |
| `TC-P08-019` | Cold Restore PITR RTO/RPO | `NFR-REC-001` | `tests/recovery/test_cold_restore_rehearsal.py` | Restore achieves measured RPO $\le 5$m, RTO $\le 30$m. |
| `TC-P08-020` | Concurrent Spend Atomic Boundary | `INV-COST-001`, `NFR-COST-001` | `tests/finops/test_spend_atomic_race_condition.py`| 500 threads cannot breach hard spend quota. |
| `TC-P08-021` | Multi-Dimensional Attribution | `NFR-COST-002`, `FR-CTL-002` | `tests/finops/test_multidim_attribution_reconcile.py`| Usage matches synthetic provider bill $< 0.5\%$ gap. |
| `TC-P08-022` | Registry Pinned Prompt Digest | `NFR-AI-001`, `AC-011` | `tests/ai/test_prompt_registry_digest_pinning.py` | Modified prompt string without registry entry rejected. |
| `TC-P08-023` | Golden Set Regression Benchmark | `NFR-AI-002..007` | `tests/ai/test_golden_set_regression.py` | All 8 AI release gates evaluated and verified. |
| `TC-P08-024` | Automated Canary Rollback Trigger| `ADR-0008`, `INV-REL-001` | `tests/deployment/test_canary_rollback_trigger.py` | Error spike reverts traffic to baseline in $< 60$s. |
| `TC-P08-025` | Mock P0 Paging Drill Verification | `INV-REL-002` | `tests/sre/test_mock_incident_paging_drill.py` | Alert fires and routes to primary on-call in $< 15$m. |
| `TC-P08-026` | Webhook Replay Deduplication | `INV-DATA-002`, `FR-ACT-003` | `tests/connectors/test_webhook_replay_deduplication.py`| 1,000 replayed webhooks return 200 without side effects.|
| `TC-P08-027` | Schema Drift Isolation Quarantine| `INV-DATA-002`, `AC-011` | `tests/connectors/test_schema_drift_quarantine.py` | Breaking schema mutation isolated to quarantine table. |
| `TC-P08-028` | Phase 08 Composite Exit Gate | `TEST-STRATEGY.md` §13 | `tests/contract/test_phase_08_exit_gate.py` | Master composite verification for production readiness. |
