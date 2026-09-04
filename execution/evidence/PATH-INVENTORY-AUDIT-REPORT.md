# Traceability Path Inventory — EXISTS vs PROSPECTIVE Classification

Date: 2026-09-04  
Scope: `execution/TRACEABILITY-CLOSURE-MATRIX.md` (Invariants & NFRs)  
Audit: FINAL-TASK-012 Path Integrity and Prospective Marker Verification  

| Requirement ID | Artifact Type | Path Expression | Classification | Disk Status | Notes |
|---|---|---|---|---|---|
| INV-TEN-001 | Implementation | `packages/backend/src/revpilot/modules/tenancy/` | EXISTS | RESOLVED | Invariant implementation |
| INV-TEN-001 | Test Suite | ``tests/tenancy/test_tenant_isolation_negative.py`; planned `tests/load/test_rls_concurrency_isolation.py`` | PROSPECTIVE | PLANNED | Verification test |
| INV-TEN-001 | Evidence Artifact | `execution/evidence/TENANT-ISOLATION-VALIDATION.md` | EXISTS | RESOLVED | Empirical evidence doc |
| INV-TEN-002 | Implementation | `packages/backend/src/revpilot/shared/context.py` | EXISTS | RESOLVED | Invariant implementation |
| INV-TEN-002 | Test Suite | `packages/backend/tests/shared/test_context.py` | EXISTS | RESOLVED | Verification test |
| INV-TEN-002 | Evidence Artifact | `execution/evidence/TENANT-ISOLATION-VALIDATION.md` | EXISTS | RESOLVED | Empirical evidence doc |
| INV-TEN-003 | Implementation | `packages/backend/src/revpilot/modules/tenancy/ports/policy.py` | EXISTS | RESOLVED | Invariant implementation |
| INV-TEN-003 | Test Suite | `packages/backend/tests/modules/tenancy/test_ports_and_policy.py` | EXISTS | RESOLVED | Verification test |
| INV-TEN-003 | Evidence Artifact | `execution/evidence/ACCESS-REVIEW-AUDIT-PACK.md` | EXISTS | RESOLVED | Empirical evidence doc |
| INV-IAM-001 | Implementation | `tasks/RAIL-03/TASK-R03-001.md (admitted; implementation `[PROSPECTIVE] packages/backend/src/revpilot/modules/iam/`)` | PROSPECTIVE | PLANNED | Invariant implementation |
| INV-IAM-001 | Test Suite | ``[PROSPECTIVE] tests/security/test_session_active_invalidation.py`` | PROSPECTIVE | PLANNED | Verification test |
| INV-IAM-001 | Evidence Artifact | `execution/evidence/SECURITY-PRIVACY-VALIDATION.md` | EXISTS | RESOLVED | Empirical evidence doc |
| INV-IAM-002 | Implementation | ``[PROSPECTIVE] packages/backend/src/revpilot/modules/iam/`` | PROSPECTIVE | PLANNED | Invariant implementation |
| INV-IAM-002 | Test Suite | ``[PROSPECTIVE] tests/security/test_agent_privilege_escalation.py`` | PROSPECTIVE | PLANNED | Verification test |
| INV-IAM-002 | Evidence Artifact | `execution/evidence/ACCESS-REVIEW-AUDIT-PACK.md` | EXISTS | RESOLVED | Empirical evidence doc |
| INV-SEC-001 | Implementation | ``packages/backend/src/revpilot/shared/errors.py` (KMS `[PROSPECTIVE]`)` | PROSPECTIVE | PLANNED | Invariant implementation |
| INV-SEC-001 | Test Suite | ``tests/privacy/test_audit_pii_redaction.py`` | EXISTS | RESOLVED | Verification test |
| INV-SEC-001 | Evidence Artifact | `execution/evidence/SECURITY-PRIVACY-VALIDATION.md` | EXISTS | RESOLVED | Empirical evidence doc |
| INV-SEC-002 | Implementation | ``[PROSPECTIVE] packages/backend/src/revpilot/modules/ai_gateway/`` | PROSPECTIVE | PLANNED | Invariant implementation |
| INV-SEC-002 | Test Suite | ``[PROSPECTIVE] tests/ai/test_adversarial_injection_harness.py`` | PROSPECTIVE | PLANNED | Verification test |
| INV-SEC-002 | Evidence Artifact | `execution/evidence/AI-EVALUATION-REPORT.md` | EXISTS | RESOLVED | Empirical evidence doc |
| INV-SEC-003 | Implementation | ``[PROSPECTIVE] packages/backend/src/revpilot/modules/connectors/`` | PROSPECTIVE | PLANNED | Invariant implementation |
| INV-SEC-003 | Test Suite | ``[PROSPECTIVE] tests/security/test_connector_egress_wall.py`` | PROSPECTIVE | PLANNED | Verification test |
| INV-SEC-003 | Evidence Artifact | `execution/evidence/SECURITY-PRIVACY-VALIDATION.md` | EXISTS | RESOLVED | Empirical evidence doc |
| INV-ACT-001 | Implementation | ``[PROSPECTIVE] packages/backend/src/revpilot/modules/tool_gateway/`` | PROSPECTIVE | PLANNED | Invariant implementation |
| INV-ACT-001 | Test Suite | ``[PROSPECTIVE] tests/security/test_connector_egress_wall.py`` | PROSPECTIVE | PLANNED | Verification test |
| INV-ACT-001 | Evidence Artifact | `execution/evidence/CANARY-ROLLBACK-VALIDATION.md` | EXISTS | RESOLVED | Empirical evidence doc |
| INV-ACT-002 | Implementation | ``[PROSPECTIVE] packages/backend/src/revpilot/modules/approvals/`` | PROSPECTIVE | PLANNED | Invariant implementation |
| INV-ACT-002 | Test Suite | ``[PROSPECTIVE] tests/security/test_approval_digest_tampering.py`` | PROSPECTIVE | PLANNED | Verification test |
| INV-ACT-002 | Evidence Artifact | `execution/evidence/CANARY-ROLLBACK-VALIDATION.md` | EXISTS | RESOLVED | Empirical evidence doc |
| INV-ACT-003 | Implementation | ``[PROSPECTIVE] packages/backend/src/revpilot/modules/approvals/`` | PROSPECTIVE | PLANNED | Invariant implementation |
| INV-ACT-003 | Test Suite | ``[PROSPECTIVE] tests/security/test_agent_privilege_escalation.py`` | PROSPECTIVE | PLANNED | Verification test |
| INV-ACT-003 | Evidence Artifact | `execution/evidence/ACCESS-REVIEW-AUDIT-PACK.md` | EXISTS | RESOLVED | Empirical evidence doc |
| INV-ACT-004 | Implementation | ``[PROSPECTIVE] packages/backend/src/revpilot/modules/ledger/`` | PROSPECTIVE | PLANNED | Invariant implementation |
| INV-ACT-004 | Test Suite | ``[PROSPECTIVE] tests/security/test_ledger_immutability.py`` | PROSPECTIVE | PLANNED | Verification test |
| INV-ACT-004 | Evidence Artifact | `execution/evidence/BILLING-RECONCILIATION.md` | EXISTS | RESOLVED | Empirical evidence doc |
| INV-WF-001 | Implementation | ``packages/backend/src/revpilot/shared/temporal.py` (cluster `[PROSPECTIVE]`)` | PROSPECTIVE | PLANNED | Invariant implementation |
| INV-WF-001 | Test Suite | ``tests/recovery/test_temporal_sigkill_recovery.py`` | EXISTS | RESOLVED | Verification test |
| INV-WF-001 | Evidence Artifact | `execution/evidence/DR-EXERCISE-REPORT.md` | EXISTS | RESOLVED | Empirical evidence doc |
| INV-WF-002 | Implementation | ``[PROSPECTIVE] packages/backend/src/revpilot/modules/workflows/sagas/`` | PROSPECTIVE | PLANNED | Invariant implementation |
| INV-WF-002 | Test Suite | ``[PROSPECTIVE] tests/recovery/test_saga_reverse_compensation.py`` | PROSPECTIVE | PLANNED | Verification test |
| INV-WF-002 | Evidence Artifact | `execution/evidence/DR-EXERCISE-REPORT.md` | EXISTS | RESOLVED | Empirical evidence doc |
| INV-AI-001 | Implementation | ``[PROSPECTIVE] packages/backend/src/revpilot/modules/ai_governance/`` | PROSPECTIVE | PLANNED | Invariant implementation |
| INV-AI-001 | Test Suite | ``[PROSPECTIVE] tests/ai/test_prompt_registry_pinning.py`` | PROSPECTIVE | PLANNED | Verification test |
| INV-AI-001 | Evidence Artifact | `execution/evidence/AI-EVALUATION-REPORT.md` | EXISTS | RESOLVED | Empirical evidence doc |
| INV-AI-002 | Implementation | ``[PROSPECTIVE] packages/backend/src/revpilot/modules/agents/verifier/`` | PROSPECTIVE | PLANNED | Invariant implementation |
| INV-AI-002 | Test Suite | ``[PROSPECTIVE] tests/ai/test_citation_provenance.py`` | PROSPECTIVE | PLANNED | Verification test |
| INV-AI-002 | Evidence Artifact | `execution/evidence/AI-EVALUATION-REPORT.md` | EXISTS | RESOLVED | Empirical evidence doc |
| INV-EVD-001 | Implementation | ``[PROSPECTIVE] packages/backend/src/revpilot/modules/evidence/`` | PROSPECTIVE | PLANNED | Invariant implementation |
| INV-EVD-001 | Test Suite | ``[PROSPECTIVE] tests/ai/test_citation_provenance.py`` | PROSPECTIVE | PLANNED | Verification test |
| INV-EVD-001 | Evidence Artifact | `execution/evidence/AI-EVALUATION-REPORT.md` | EXISTS | RESOLVED | Empirical evidence doc |
| INV-EVD-002 | Implementation | ``[PROSPECTIVE] packages/backend/src/revpilot/modules/investigations/`` | PROSPECTIVE | PLANNED | Invariant implementation |
| INV-EVD-002 | Test Suite | ``[PROSPECTIVE] tests/security/test_ledger_immutability.py`` | PROSPECTIVE | PLANNED | Verification test |
| INV-EVD-002 | Evidence Artifact | `execution/evidence/DR-EXERCISE-REPORT.md` | EXISTS | RESOLVED | Empirical evidence doc |
| INV-DATA-001 | Implementation | ``packages/backend/src/revpilot/shared/temporal.py` (store `[PROSPECTIVE]`)` | PROSPECTIVE | PLANNED | Invariant implementation |
| INV-DATA-001 | Test Suite | ``[PROSPECTIVE] tests/data/test_future_dated_record_block.py`` | PROSPECTIVE | PLANNED | Verification test |
| INV-DATA-001 | Evidence Artifact | `execution/evidence/LOAD-STRESS-SOAK-VALIDATION.md` | EXISTS | RESOLVED | Empirical evidence doc |
| INV-DATA-002 | Implementation | ``[PROSPECTIVE] packages/backend/src/revpilot/modules/data_platform/`` | PROSPECTIVE | PLANNED | Invariant implementation |
| INV-DATA-002 | Test Suite | ``[PROSPECTIVE] tests/data/test_schema_drift_quarantine.py`` | PROSPECTIVE | PLANNED | Verification test |
| INV-DATA-002 | Evidence Artifact | `execution/evidence/LOAD-STRESS-SOAK-VALIDATION.md` | EXISTS | RESOLVED | Empirical evidence doc |
| INV-AUD-001 | Implementation | ``[PROSPECTIVE] packages/backend/src/revpilot/modules/audit/`` | PROSPECTIVE | PLANNED | Invariant implementation |
| INV-AUD-001 | Test Suite | ``tests/security/test_audit_stream_zero_drop.py`` | EXISTS | RESOLVED | Verification test |
| INV-AUD-001 | Evidence Artifact | `execution/evidence/ACCESS-REVIEW-AUDIT-PACK.md` | EXISTS | RESOLVED | Empirical evidence doc |
| INV-AUD-002 | Implementation | ``packages/backend/src/revpilot/shared/errors.py` (stream `[PROSPECTIVE]`)` | PROSPECTIVE | PLANNED | Invariant implementation |
| INV-AUD-002 | Test Suite | ``tests/privacy/test_audit_pii_redaction.py`` | EXISTS | RESOLVED | Verification test |
| INV-AUD-002 | Evidence Artifact | `execution/evidence/SECURITY-PRIVACY-VALIDATION.md` | EXISTS | RESOLVED | Empirical evidence doc |
| INV-COST-001 | Implementation | ``packages/backend/src/revpilot/shared/monetary.py` (quota `[PROSPECTIVE]`)` | PROSPECTIVE | PLANNED | Invariant implementation |
| INV-COST-001 | Test Suite | ``[PROSPECTIVE] tests/finops/test_spend_atomic_race.py`` | PROSPECTIVE | PLANNED | Verification test |
| INV-COST-001 | Evidence Artifact | `execution/evidence/BILLING-RECONCILIATION.md` | EXISTS | RESOLVED | Empirical evidence doc |
| INV-PRV-001 | Implementation | ``[PROSPECTIVE] packages/backend/src/revpilot/modules/governance/`` | PROSPECTIVE | PLANNED | Invariant implementation |
| INV-PRV-001 | Test Suite | ``tests/privacy/test_audit_pii_redaction.py`` | EXISTS | RESOLVED | Verification test |
| INV-PRV-001 | Evidence Artifact | `execution/evidence/SECURITY-PRIVACY-VALIDATION.md` | EXISTS | RESOLVED | Empirical evidence doc |
| INV-REL-001 | Implementation | ``packages/backend/src/revpilot/shared/results.py` (kill-switch `[PROSPECTIVE]`)` | PROSPECTIVE | PLANNED | Invariant implementation |
| INV-REL-001 | Test Suite | ``tests/recovery/test_kill_switch_propagation.py`` | EXISTS | RESOLVED | Verification test |
| INV-REL-001 | Evidence Artifact | `execution/evidence/CANARY-ROLLBACK-VALIDATION.md` | EXISTS | RESOLVED | Empirical evidence doc |
| INV-REL-002 | Implementation | `docs/24-sre/PRODUCTION-READINESS-GATE.md` | EXISTS | RESOLVED | Invariant implementation |
| INV-REL-002 | Test Suite | ``[PROSPECTIVE] tests/e2e/test_phase_08_exit_gate.py`` | PROSPECTIVE | PLANNED | Verification test |
| INV-REL-002 | Evidence Artifact | `execution/evidence/SLO-BASELINE-REPORT.md` | EXISTS | RESOLVED | Empirical evidence doc |
| NFR-SEC-001 | Test Suite | ``[PROSPECTIVE] tests/security/test_session_active_invalidation.py`` | PROSPECTIVE | PLANNED | Verification test |
| NFR-SEC-001 | Evidence Artifact | `execution/evidence/SECURITY-PRIVACY-VALIDATION.md` | EXISTS | RESOLVED | Empirical evidence doc |
| NFR-SEC-002 | Test Suite | ``tests/security/test_connector_secret_scrubbing.py`` | EXISTS | RESOLVED | Verification test |
| NFR-SEC-002 | Evidence Artifact | `execution/evidence/SECURITY-PRIVACY-VALIDATION.md` | EXISTS | RESOLVED | Empirical evidence doc |
| NFR-AVL-001 | Test Suite | ``[PROSPECTIVE] tests/load/test_soak_72h.py`` | PROSPECTIVE | PLANNED | Verification test |
| NFR-AVL-001 | Evidence Artifact | `execution/evidence/SLO-BASELINE-REPORT.md` | EXISTS | RESOLVED | Empirical evidence doc |
| NFR-AVL-002 | Test Suite | ``[PROSPECTIVE] tests/load/test_service_availability.py`` | PROSPECTIVE | PLANNED | Verification test |
| NFR-AVL-002 | Evidence Artifact | `execution/evidence/SLO-BASELINE-REPORT.md` | EXISTS | RESOLVED | Empirical evidence doc |
| NFR-LAT-001 | Test Suite | ``[PROSPECTIVE] tests/load/test_api_latency_budget.py`` | PROSPECTIVE | PLANNED | Verification test |
| NFR-LAT-001 | Evidence Artifact | `execution/evidence/SLO-BASELINE-REPORT.md` | EXISTS | RESOLVED | Empirical evidence doc |
| NFR-LAT-002 | Test Suite | ``[PROSPECTIVE] tests/observability/test_event_propagation_latency.py`` | PROSPECTIVE | PLANNED | Verification test |
| NFR-LAT-002 | Evidence Artifact | `execution/evidence/SLO-BASELINE-REPORT.md` | EXISTS | RESOLVED | Empirical evidence doc |
| NFR-THR-001 | Test Suite | ``[PROSPECTIVE] tests/load/test_initial_capacity.py`` | PROSPECTIVE | PLANNED | Verification test |
| NFR-THR-001 | Evidence Artifact | `execution/evidence/LOAD-STRESS-SOAK-VALIDATION.md` | EXISTS | RESOLVED | Empirical evidence doc |
| NFR-THR-002 | Test Suite | ``[PROSPECTIVE] tests/load/test_growth_capacity.py`` | PROSPECTIVE | PLANNED | Verification test |
| NFR-THR-002 | Evidence Artifact | `execution/evidence/LOAD-STRESS-SOAK-VALIDATION.md` | EXISTS | RESOLVED | Empirical evidence doc |
| NFR-DUR-001 | Test Suite | ``tests/recovery/test_temporal_sigkill_recovery.py`` | EXISTS | RESOLVED | Verification test |
| NFR-DUR-001 | Evidence Artifact | `execution/evidence/DR-EXERCISE-REPORT.md` | EXISTS | RESOLVED | Empirical evidence doc |
| NFR-REL-001 | Test Suite | ``tests/recovery/test_temporal_sigkill_recovery.py`` | EXISTS | RESOLVED | Verification test |
| NFR-REL-001 | Evidence Artifact | `execution/evidence/DR-EXERCISE-REPORT.md` | EXISTS | RESOLVED | Empirical evidence doc |
| NFR-REL-002 | Test Suite | ``[PROSPECTIVE] tests/security/test_dependency_outage_matrix.py`` | PROSPECTIVE | PLANNED | Verification test |
| NFR-REL-002 | Evidence Artifact | `execution/evidence/SECURITY-PRIVACY-VALIDATION.md` | EXISTS | RESOLVED | Empirical evidence doc |
| NFR-REC-001 | Test Suite | ``tests/recovery/test_cold_restore_rehearsal.py`` | EXISTS | RESOLVED | Verification test |
| NFR-REC-001 | Evidence Artifact | `execution/evidence/DR-EXERCISE-REPORT.md` | EXISTS | RESOLVED | Empirical evidence doc |
| NFR-TEN-001 | Test Suite | ``tests/tenancy/test_tenant_isolation_negative.py`` | EXISTS | RESOLVED | Verification test |
| NFR-TEN-001 | Evidence Artifact | `execution/evidence/TENANT-ISOLATION-VALIDATION.md` | EXISTS | RESOLVED | Empirical evidence doc |
| NFR-TEN-002 | Test Suite | ``tests/load/test_rls_concurrency_isolation.py`` | EXISTS | RESOLVED | Verification test |
| NFR-TEN-002 | Evidence Artifact | `execution/evidence/TENANT-ISOLATION-VALIDATION.md` | EXISTS | RESOLVED | Empirical evidence doc |
| NFR-AUD-001 | Test Suite | ``tests/security/test_audit_stream_zero_drop.py`` | EXISTS | RESOLVED | Verification test |
| NFR-AUD-001 | Evidence Artifact | `execution/evidence/ACCESS-REVIEW-AUDIT-PACK.md` | EXISTS | RESOLVED | Empirical evidence doc |
| NFR-COST-001 | Test Suite | ``[PROSPECTIVE] tests/finops/test_spend_atomic_race.py`` | PROSPECTIVE | PLANNED | Verification test |
| NFR-COST-001 | Evidence Artifact | `execution/evidence/BILLING-RECONCILIATION.md` | EXISTS | RESOLVED | Empirical evidence doc |
| NFR-COST-002 | Test Suite | ``[PROSPECTIVE] tests/finops/test_multidim_attribution.py`` | PROSPECTIVE | PLANNED | Verification test |
| NFR-COST-002 | Evidence Artifact | `execution/evidence/BILLING-RECONCILIATION.md` | EXISTS | RESOLVED | Empirical evidence doc |
| NFR-PRV-001 | Test Suite | ``tests/privacy/test_audit_pii_redaction.py`` | EXISTS | RESOLVED | Verification test |
| NFR-PRV-001 | Evidence Artifact | `execution/evidence/SECURITY-PRIVACY-VALIDATION.md` | EXISTS | RESOLVED | Empirical evidence doc |
| NFR-PRV-002 | Test Suite | ``[PROSPECTIVE] tests/privacy/test_legal_hold_rejection.py`` | PROSPECTIVE | PLANNED | Verification test |
| NFR-PRV-002 | Evidence Artifact | `execution/evidence/SECURITY-PRIVACY-VALIDATION.md` | EXISTS | RESOLVED | Empirical evidence doc |
| NFR-OBS-001 | Test Suite | ``tests/observability/test_trace_correlation_linkage.py`` | EXISTS | RESOLVED | Verification test |
| NFR-OBS-001 | Evidence Artifact | `execution/evidence/SLO-BASELINE-REPORT.md` | EXISTS | RESOLVED | Empirical evidence doc |
| NFR-OBS-002 | Test Suite | ``[PROSPECTIVE] tests/observability/test_telemetry_pipeline_load.py`` | PROSPECTIVE | PLANNED | Verification test |
| NFR-OBS-002 | Evidence Artifact | `execution/evidence/SLO-BASELINE-REPORT.md` | EXISTS | RESOLVED | Empirical evidence doc |
| NFR-AI-001 | Test Suite | ``tests/ai/test_prompt_registry_digest_pinning.py`` | EXISTS | RESOLVED | Verification test |
| NFR-AI-001 | Evidence Artifact | `execution/evidence/AI-EVALUATION-REPORT.md` | EXISTS | RESOLVED | Empirical evidence doc |
| NFR-AI-002 | Test Suite | ``[PROSPECTIVE] tests/eval/test_rca_benchmark.py`` | PROSPECTIVE | PLANNED | Verification test |
| NFR-AI-002 | Evidence Artifact | `execution/evidence/AI-EVALUATION-REPORT.md` | EXISTS | RESOLVED | Empirical evidence doc |
| NFR-AI-003 | Test Suite | ``[PROSPECTIVE] tests/eval/test_rag_benchmark.py`` | PROSPECTIVE | PLANNED | Verification test |
| NFR-AI-003 | Evidence Artifact | `execution/evidence/AI-EVALUATION-REPORT.md` | EXISTS | RESOLVED | Empirical evidence doc |
| NFR-AI-004 | Test Suite | ``[PROSPECTIVE] tests/eval/test_sql_semantic_suite.py`` | PROSPECTIVE | PLANNED | Verification test |
| NFR-AI-004 | Evidence Artifact | `execution/evidence/AI-EVALUATION-REPORT.md` | EXISTS | RESOLVED | Empirical evidence doc |
| NFR-AI-005 | Test Suite | ``[PROSPECTIVE] tests/eval/test_calibration_holdout.py`` | PROSPECTIVE | PLANNED | Verification test |
| NFR-AI-005 | Evidence Artifact | `execution/evidence/AI-EVALUATION-REPORT.md` | EXISTS | RESOLVED | Empirical evidence doc |
| NFR-AI-006 | Test Suite | ``[PROSPECTIVE] tests/eval/test_uplift_qini_benchmark.py`` | PROSPECTIVE | PLANNED | Verification test |
| NFR-AI-006 | Evidence Artifact | `execution/evidence/AI-EVALUATION-REPORT.md` | EXISTS | RESOLVED | Empirical evidence doc |
| NFR-AI-007 | Test Suite | ``[PROSPECTIVE] tests/eval/test_causal_benchmark.py`` | PROSPECTIVE | PLANNED | Verification test |
| NFR-AI-007 | Evidence Artifact | `execution/evidence/AI-EVALUATION-REPORT.md` | EXISTS | RESOLVED | Empirical evidence doc |
