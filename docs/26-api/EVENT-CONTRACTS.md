# Event Contract Standards (Canonical Event Outbox & Messaging Contract)

Status: Accepted Canonical Specification
Initiative: REVPILOT
Scope: Domain Events, Outbox Architecture, and Tenancy Binding (Rails 3–5 Integration)
Owner: Platform Architecture + Data Platform
Traceability: `INV-DATA-002`, `INV-TEN-001`, `INV-SEC-001`, `INV-ACT-002`, `ADR-0004`, `ADR-0007`

---

## 1. Event Architecture: Transactional Outbox Pattern

To preserve strict consistency and avoid distributed two-phase commit overhead, RevPilot mandates the Transactional Outbox Pattern (`ADR-0004`, `ADR-0007`):
- Any state-mutating domain operation writes the aggregate state change AND the domain event outbox record within the **same atomic database transaction**.
- A reliable asynchronous background dispatcher polls the outbox table and publishes events to consumers.

---

## 2. Standard Event Envelope Schema

Every published event adheres to a standard, versioned envelope:

```python
@dataclass(frozen=True, slots=True)
class EventEnvelope:
    event_id: str                      # Unique event UUID (evt_...)
    event_type: str                    # Dot-delimited canonical type (e.g. tenant.activated.v1)
    event_version: int                 # Event schema version (monotonically increasing)
    occurred_at: UtcDateTime           # UTC creation timestamp
    producer: str                      # Owning module (e.g. revpilot.modules.tenancy)
    aggregate_id: str                  # Target aggregate identifier
    aggregate_version: int             # Aggregate revision number
    tenant_id: TenantId | None         # Mandatory tenant context (None for system events)
    correlation_id: CorrelationId      # Request correlation UUID
    causation_id: str | None           # Upstream event ID causing this action
    idempotency_key: str | None        # Optional client idempotency reference
    payload: dict[str, Any]            # Versioned, schema-validated event payload
```

---

## 3. Mandatory Security and Tenancy Rules

1. **Mandatory Tenant Context (`INV-TEN-001`)**:
   - Every tenant-scoped event MUST carry `tenant_id` in the top-level envelope.
   - Consumers unpack the envelope, extract `tenant_id`, and instantiate a validated `TenantContext` before dispatching to application event handlers.
2. **Zero Credentials or Raw Secrets (`INV-SEC-001`)**:
   - Event payloads must NEVER contain passwords, tokens, API keys, or raw secrets.
   - Only non-sensitive identifiers and references (`CredentialRef`) may be transmitted.
3. **At-Least-Once Delivery and Consumer Deduplication (`INV-ACT-002`)**:
   - Consumers maintain an inbox/deduplication ledger keyed by `(consumer_name, event_id)`.
   - Repeated events within the deduplication window are safely acknowledged and skipped.
4. **Ordering Guarantees**:
   - Strict ordering is guaranteed only within the same aggregate key (`aggregate_id`).
   - Cross-aggregate ordering is not guaranteed and must not be assumed by consumers.

---

## 4. Phase 02 Anomaly Lifecycle Domain Events

The following versioned domain events govern the anomaly detection and analytical lifecycle:

| Event Type | Version | Producer | Aggregate | Key Payload Fields |
|---|---:|---|---|---|
| `anomaly.detected.v1` | 1 | `revpilot.modules.analytics` | `Anomaly` | `anomaly_id`, `metric_id`, `actual_value`, `expected_interval`, `score`, `as_of_time` |
| `anomaly.validated.v1` | 1 | `revpilot.modules.analytics` | `Anomaly` | `anomaly_id`, `data_quality_state`, `freshness_state`, `validated_at` |
| `anomaly.localized.v1` | 1 | `revpilot.modules.analytics` | `Anomaly` | `anomaly_id`, `top_contributing_segments`, `primary_dimension`, `data_coverage_pct` |
| `anomaly.acknowledged.v1` | 1 | `revpilot.modules.investigations`| `Anomaly` | `anomaly_id`, `acknowledged_by_principal`, `investigation_id`, `acknowledged_at` |
| `anomaly.suppressed.v1` | 1 | `revpilot.modules.analytics` | `Anomaly` | `anomaly_id`, `suppression_reason`, `suppression_rule_id`, `suppressed_at` |
| `anomaly.resolved.v1` | 1 | `revpilot.modules.analytics` | `Anomaly` | `anomaly_id`, `resolution_type`, `resolved_at`, `final_metric_value` |
| `anomaly.reopened.v1` | 1 | `revpilot.modules.analytics` | `Anomaly` | `anomaly_id`, `reopened_at`, `new_actual_value`, `trigger_score` |

### Sample Outbox Event Payload (`anomaly.detected.v1`)
```json
{
  "event_id": "evt_01h8cba1234567890",
  "event_type": "anomaly.detected.v1",
  "event_version": 1,
  "occurred_at": "2026-02-15T00:00:00Z",
  "producer": "revpilot.modules.analytics",
  "aggregate_id": "anm_01h8abc1234567890",
  "aggregate_version": 1,
  "tenant_id": "ten_01h7abcde123456789",
  "correlation_id": "cor_01h8abcde123456789",
  "causation_id": "job_detector_hourly_001",
  "idempotency_key": "anm_detect_METRIC-001_2026021500",
  "payload": {
    "anomaly_id": "anm_01h8abc1234567890",
    "metric_id": "METRIC-001",
    "metric_version": "1.0.0",
    "detector_id": "DET-STL-RESIDUAL-001",
    "actual_value": 0.0842,
    "expected_value": 0.0181,
    "expected_interval": [0.0112, 0.0250],
    "anomaly_score": 0.8842,
    "severity": "CRITICAL",
    "observation_window": {
      "start_time": "2026-02-14T00:00:00Z",
      "end_time": "2026-02-15T00:00:00Z"
    },
    "as_of_time": "2026-02-15T00:00:00Z"
  }
}
```

---

## 5. Investigation Domain Events (Phase 03)

Investigation events are emitted to the transactional outbox and published to the event broker under strict tenant partitioning.

| Event Type | Producer | Aggregate | Partition Key | Retention | Description |
|---|---|---|---|---|---|
| `investigation.created.v1` | `revpilot.modules.investigation` | Investigation | `tenant_id` | 7 years | Emitted when investigation workflow is initialized. |
| `investigation.plan_generated.v1`| `revpilot.modules.investigation` | Investigation | `tenant_id` | 1 year | Emitted when planner creates validated acyclic DAG. |
| `investigation.task_completed.v1`| `revpilot.modules.investigation` | InvestigationTask | `tenant_id` | 30 days | Emitted when a DAG worker activity completes. |
| `investigation.task_failed.v1` | `revpilot.modules.investigation` | InvestigationTask | `tenant_id` | 1 year | Emitted when a DAG activity fails terminal. |
| `investigation.evidence_gathered.v1`| `revpilot.modules.evidence` | EvidenceBundle | `tenant_id` | 1 year | Emitted when evidence chunk or query is sealed. |
| `investigation.hypothesis_evaluated.v1`| `revpilot.modules.investigation`| Hypothesis | `tenant_id` | 1 year | Emitted when verifier scores a candidate hypothesis. |
| `investigation.paused.v1` | `revpilot.modules.investigation` | Investigation | `tenant_id` | 1 year | Emitted when workflow pauses via signal. |
| `investigation.resumed.v1` | `revpilot.modules.investigation` | Investigation | `tenant_id` | 1 year | Emitted when workflow resumes via signal. |
| `investigation.cancelled.v1` | `revpilot.modules.investigation` | Investigation | `tenant_id` | 1 year | Emitted when workflow cancels via signal/timeout. |
| `investigation.completed.v1` | `revpilot.modules.investigation` | Investigation | `tenant_id` | 7 years | Emitted when investigation successfully concludes with verified hypotheses. |
| `investigation.need_more_evidence.v1`| `revpilot.modules.investigation`| Investigation | `tenant_id` | 7 years | Emitted when verifier determines evidence gaps require escalation. |

### 5.1. Example `investigation.completed.v1` Event Payload
```json
{
  "event_id": "evt_01h8abcd999888777666",
  "event_type": "investigation.completed.v1",
  "occurred_at": "2026-09-03T18:35:00Z",
  "producer": "revpilot.modules.investigation",
  "aggregate_id": "inv_01h8abcde12345",
  "aggregate_version": 12,
  "tenant_id": "ten_01h7abcde123456789",
  "correlation_id": "cor_01h8abcde123456789",
  "causation_id": "act_verify_evidence_001",
  "idempotency_key": "inv_complete_inv_01h8abcde12345",
  "payload": {
    "investigation_id": "inv_01h8abcde12345",
    "top_hypothesis_id": "hypo_01",
    "top_hypothesis_title": "Truck Capacity Shortage at Midwest Distribution Center",
    "likelihood_score": 0.88,
    "status": "VERIFIED",
    "evidence_count": 8,
    "bundle_digest": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "cogs_usd": 1.45,
    "duration_seconds": 142
  }
}
```

---

## 6. Phase 04 Causal Study and Hypothesis Verifier Events

| Event Type | Producer Module | Aggregate | Partition Key | Retention | Description |
|---|---|---|---|---|---|
| `causal.study_created.v1` | `revpilot.modules.causal` | CausalStudy | `tenant_id` | 1 year | Emitted when a causal study is registered with treatment/outcome/estimand. |
| `causal.study_estimated.v1`| `revpilot.modules.causal` | CausalStudy | `tenant_id` | 7 years | Emitted when statistical estimation and sensitivity bounds complete. |
| `causal.study_rejected.v1` | `revpilot.modules.causal` | CausalStudy | `tenant_id` | 1 year | Emitted when study fails overlap, collider check, or time leakage audit. |
| `hypothesis.ranked.v1` | `revpilot.modules.hypothesis` | HypothesisSet | `tenant_id` | 1 year | Emitted when multi-hypothesis ranking is finalized against evidence. |
| `claim.verified.v1` | `revpilot.modules.verifier` | VerifiedClaim | `tenant_id` | 1 year | Emitted when a claim is formally verified against evidence citations. |
| `claim.rejected.v1` | `revpilot.modules.verifier` | VerifiedClaim | `tenant_id` | 1 year | Emitted when a claim is rejected (unsupported, contradicted, or leakage). |

### 6.1. Example `causal.study_estimated.v1` Event Payload
```json
{
  "event_id": "evt_01h8causal999888777666",
  "event_type": "causal.study_estimated.v1",
  "occurred_at": "2026-09-03T19:00:00Z",
  "producer": "revpilot.modules.causal",
  "aggregate_id": "cs_01h8abcde99999",
  "aggregate_version": 2,
  "tenant_id": "ten_01h7abcde123456789",
  "correlation_id": "cor_01h8abcde123456789",
  "causation_id": "act_estimate_causal_001",
  "idempotency_key": "causal_est_cs_01h8abcde99999",
  "payload": {
    "study_id": "cs_01h8abcde99999",
    "treatment_variable": "carrier_truck_shortage",
    "outcome_variable": "order_cancelled",
    "estimand_type": "ATE",
    "point_estimate": 0.0645,
    "ci_lower": 0.0310,
    "ci_upper": 0.0980,
    "p_value": 0.0002,
    "positivity_satisfied": true,
    "e_value": 2.15,
    "study_digest": "a1b2c3d4e5f67890abcdef1234567890abcdef1234567890abcdef1234567890"
  }
}
```

---

## 7. Phase 05 Churn, Uplift, and Decision Events

| Event Type | Producer Module | Aggregate | Partition Key | Retention | Description |
|---|---|---|---|---|---|
| `ml.churn_scored.v1` | `revpilot.modules.ml.churn` | ChurnPrediction | `tenant_id` | 1 year | Emitted when calibrated churn risk is evaluated for an account. |
| `ml.uplift_estimated.v1` | `revpilot.modules.ml.uplift` | UpliftScore | `tenant_id` | 1 year | Emitted when incremental CATE uplift is scored for an intervention. |
| `decision.optimized.v1` | `revpilot.modules.decision` | DecisionRecord | `tenant_id` | 7 years | Emitted when expected utility optimizer selects a recommended intervention. |
| `decision.abstained.v1` | `revpilot.modules.decision` | DecisionRecord | `tenant_id` | 1 year | Emitted when optimizer abstains due to negative utility or constraint failure. |
| `budget.reserved.v1` | `revpilot.modules.finops` | BudgetLedger | `tenant_id` | 7 years | Emitted when funds are reserved against tenant decision budget. |
| `budget.exhausted.v1` | `revpilot.modules.finops` | BudgetLedger | `tenant_id` | 1 year | Emitted when daily budget limit is hit, blocking further paid recommendations. |

### 7.1. Example `decision.optimized.v1` Event Payload
```json
{
  "event_id": "evt_01h8dec999888777666",
  "event_type": "decision.optimized.v1",
  "occurred_at": "2026-09-03T19:30:00Z",
  "producer": "revpilot.modules.decision",
  "aggregate_id": "dec_01h8abcde88888",
  "aggregate_version": 1,
  "tenant_id": "ten_01h7abcde123456789",
  "correlation_id": "cor_01h8abcde123456789",
  "causation_id": "req_dec_optimize_001",
  "idempotency_key": "dec_opt_dec_01h8abcde88888",
  "payload": {
    "decision_id": "dec_01h8abcde88888",
    "customer_id": "cust_12345",
    "selected_candidate_id": "int_priority_reship_01",
    "expected_utility_usd": 125.40,
    "direct_cost_usd": 45.00,
    "expected_retention_uplift": 0.185,
    "status": "RECOMMENDED",
    "decision_digest": "f0e1d2c3b4a596877869504132231405a1b2c3d4e5f67890abcdef1234567890"
  }
}
```

---

## 8. Phase 06 Approval, Action Safety, and Reconciliation Events

| Event Type | Producer Module | Aggregate | Partition Key | Retention | Description |
|---|---|---|---|---|---|
| `approval.requested.v1` | `revpilot.modules.approval` | ApprovalRequest | `tenant_id` | 7 years | Emitted when decision engine requests human authorization for an action. |
| `approval.granted.v1` | `revpilot.modules.approval` | ApprovalRequest | `tenant_id` | 7 years | Emitted when human principal signs and approves the action digest. |
| `approval.rejected.v1` | `revpilot.modules.approval` | ApprovalRequest | `tenant_id` | 7 years | Emitted when approver rejects action or request expires. |
| `action.dispatched.v1` | `revpilot.modules.tool_gateway` | ActionIntent | `tenant_id` | 7 years | Emitted when approved action is dispatched via Tool Gateway. |
| `action.completed.v1` | `revpilot.modules.tool_gateway` | ActionLedger | `tenant_id` | 7 years | Emitted when provider confirms successful side effect execution. |
| `action.reconciliation_required.v1` | `revpilot.modules.tool_gateway` | ActionLedger | `tenant_id` | 7 years | Emitted when provider call returns UNKNOWN after retries, alerting SRE. |
| `action.compensated.v1` | `revpilot.modules.workflow` | CompensationRecord | `tenant_id` | 7 years | Emitted when Saga compensation activity undoes partial side effects. |
| `safety.kill_switch_activated.v1` | `revpilot.modules.security` | KillSwitch | `tenant_id` | 7 years | Emitted when safety kill switch halts operational tool execution. |

### 8.1. Example `action.completed.v1` Event Payload
```json
{
  "event_id": "evt_01h8act999888777666",
  "event_type": "action.completed.v1",
  "occurred_at": "2026-09-03T20:00:00Z",
  "producer": "revpilot.modules.tool_gateway",
  "aggregate_id": "led_01h8abcde77777",
  "aggregate_version": 2,
  "tenant_id": "ten_01h7abcde123456789",
  "correlation_id": "cor_01h8abcde123456789",
  "causation_id": "int_01h8abcde66666",
  "idempotency_key": "act_reship_01h8abcde77777",
  "payload": {
    "intent_id": "int_01h8abcde66666",
    "approval_id": "app_01h8abcde55555",
    "provider_name": "mock_carrier_logistics_v1",
    "provider_tx_id": "prov_tx_998822",
    "execution_status": "SUCCESS",
    "http_status_code": 200,
    "actual_cost_usd": 45.00
  }
}
```

---

## 9. Phase 07 Tenancy, Identity, Connector, and FinOps Domain Events

### 9.1. Phase 07 Event Catalog

| Event Type | Producer Module | Aggregate Entity | Partition Key | Retention | Description |
|---|---|---|---|---|---|
| `tenancy.provisioned.v1` | `revpilot.modules.tenancy` | Tenant | `tenant_id` | Permanent | Emitted when tenant resources and isolation boundaries are provisioned. |
| `tenancy.activated.v1` | `revpilot.modules.tenancy` | Tenant | `tenant_id` | Permanent | Emitted when pre-activation isolation and health probes pass. |
| `tenancy.suspended.v1` | `revpilot.modules.tenancy` | Tenant | `tenant_id` | Permanent | Emitted when tenant access is halted due to quota or security breach. |
| `tenancy.export_ready.v1` | `revpilot.modules.tenancy` | TenantExport | `tenant_id` | 7 years | Emitted when export package and cryptographic manifest are generated. |
| `tenancy.deletion_completed.v1`| `revpilot.modules.tenancy` | DeletionCertificate | `tenant_id`| Permanent | Emitted when cascade deletion across all datastores is completed. |
| `identity.user_synced.v1` | `revpilot.modules.iam` | Principal | `tenant_id` | 7 years | Emitted when SCIM pushes a user or group membership change. |
| `connector.synced.v1` | `revpilot.modules.connectors` | ConnectorInstance | `tenant_id` | 7 years | Emitted when incremental or batch sync completes successfully. |
| `connector.schema_drifted.v1` | `revpilot.modules.connectors` | QuarantinedPayload | `tenant_id` | 7 years | Emitted when breaking schema drift is detected and quarantined. |
| `finops.quota_exhausted.v1` | `revpilot.modules.finops` | TenantQuota | `tenant_id` | 7 years | Emitted when hard quota is reached and requests are throttled. |
| `finops.reconciled.v1` | `revpilot.modules.finops` | UsageCycle | `tenant_id` | 7 years | Emitted when provider invoice reconciliation completes. |

### 9.2. Example `connector.schema_drifted.v1` Event Payload
```json
{
  "event_id": "evt_01h8drift111222333",
  "event_type": "connector.schema_drifted.v1",
  "occurred_at": "2026-09-03T21:00:00Z",
  "producer": "revpilot.modules.connectors",
  "aggregate_id": "con_01h8abcde33333",
  "aggregate_version": 1,
  "tenant_id": "ten_01h7abcde123456789",
  "correlation_id": "cor_01h8drift123456789",
  "causation_id": "evt_webhook_inbound_9988",
  "idempotency_key": "drift_con_01h8abcde33333_v2",
  "payload": {
    "connector_id": "con_01h8abcde33333",
    "provider_name": "hubspot",
    "quarantine_id": "quar_01h8abcde44444",
    "drift_classification": "BREAKING_TYPE_MISMATCH",
    "field_name": "contract_arr_cents",
    "expected_type": "INTEGER",
    "received_type": "STRING",
    "quarantined_record_count": 1
  }
}
```
