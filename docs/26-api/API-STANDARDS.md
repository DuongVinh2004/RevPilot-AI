# API Standards Specification (Canonical API Contract)

Status: Accepted Canonical Specification
Initiative: REVPILOT
Scope: HTTP/REST Endpoints, Error Contracts, and Tenancy Binding (Rails 3–5 Integration)
Owner: API Platform Architecture
Traceability: `INV-TEN-002`, `INV-IAM-001`, `INV-AUD-001`, `INV-REL-001`, `NFR-SEC-001`, `NFR-TEN-001`
Approver: Duong Vinh (Repository Owner)
Version: v1.0
Last Reviewed Date: 2026-09-04

---

## 1. Core API Principles and Request Flow

Every inbound HTTP request to RevPilot AI undergoes deterministic validation and context resolution before reaching any application service or domain model:

```text
Inbound HTTP Request
  │
  ├─ 1. Rate Limiting & TLS Termination
  ├─ 2. Correlation Extraction (Extracts or generates X-Correlation-ID)
  ├─ 3. Authentication Verification (Validates Bearer token via AuthenticationPort)
  ├─ 4. Server-Derived Context Resolution (Instantiates TenantContext & PrincipalContext)
  ├─ 5. Authorization Enforcement (Evaluates RBAC/ABAC permissions via AuthorizationPort)
  ├─ 6. Application Use Case Execution (Passes typed context)
  └─ 7. Standard Response Serialization / Uniform Error Handling
```

---

## 2. Server-Derived Context and Untrusted Client Headers (`INV-TEN-002`)

1. **Authorization Header**: Requests authenticate via `Authorization: Bearer <token>`.
2. **Untrusted Headers Discarded**:
   - Headers such as `X-Tenant-ID`, `X-User-ID`, `X-Roles` supplied by the client are strictly ignored for authorization purposes.
   - Any mismatch between a client-claimed tenant header and the cryptographically verified token claim raises HTTP 403 `TENANCY_VIOLATION`.
3. **Correlation ID**: Clients may provide `X-Correlation-ID` for client-side tracing; if missing, the API gateway generates a new UUID v4.

---

## 3. Canonical Error Response Envelope

All API errors return a uniform, machine-readable JSON structure conforming to the standard schema:

```json
{
  "code": "AUTHENTICATION_ERROR",
  "message": "Authentication token invalid or expired",
  "correlation_id": "cor_01h7abcde123456789",
  "details": [
    {
      "field": "exp",
      "issue": "Token has expired"
    }
  ]
}
```

### Stable Error Code Mapping

| HTTP Status | Error Code | Trigger Condition | Retryable | Audit Emitted |
|---|---|---|---:|---|
| 400 Bad Request | `VALIDATION_ERROR` | Schema failure, malformed claim structure, missing fields | no | yes |
| 401 Unauthorized | `AUTHENTICATION_ERROR` | Missing token, invalid signature, expired token | no | yes |
| 401 Unauthorized | `TOKEN_EXPIRED` | Token past expiration timestamp | no | yes |
| 401 Unauthorized | `TOKEN_REVOKED` | Session or token explicitly revoked | no | yes |
| 403 Forbidden | `AUTHORIZATION_DENIED` | Insufficient role, permission, or scope | no | yes |
| 403 Forbidden | `TENANCY_VIOLATION` | Non-member tenant access attempt, cross-tenant call | no | yes |
| 403 Forbidden | `DELEGATION_EXPIRED` | AI Agent delegation token expired | no | yes |
| 404 Not Found | `RESOURCE_NOT_FOUND` | Resource does not exist within tenant boundary | no | no |
| 409 Conflict | `IDEMPOTENCY_CONFLICT` | Replay with mismatched payload or concurrent mutation | no | yes |
| 429 Too Many Requests | `RATE_LIMIT_EXCEEDED` | Request rate exceeds quota | yes | no |
| 503 Service Unavailable | `SERVICE_UNAVAILABLE` | Dependency outage / fail-closed write protection | yes | yes |

---

## 4. Idempotency and Mutations (`INV-ACT-002`)

- All state-mutating endpoints (`POST`, `PUT`, `PATCH`, `DELETE`) require an `Idempotency-Key` header.
- Idempotency keys are scoped by composite key: `(tenant_id, principal_id, route, idempotency_key)`.
- Replays with identical request payload return the cached previous response.
- Replays with altered payloads raise HTTP 409 `IDEMPOTENCY_CONFLICT`.

---

## 5. Phase 02 Detection & Analytics API Endpoints

The following REST endpoints govern Phase 02 metric querying, anomaly detection, dimensional localization, and lifecycle management:

### 5.1. Metric Query API
- **Endpoint**: `POST /api/v1/analytics/metrics/query`
- **Auth**: `Authorization: Bearer <token>` (Scope: `analytics:read`)
- **Headers**: `X-Correlation-ID: <uuid>`
- **Request Body**: `MetricQueryRequest` (`docs/07-data-platform/METRIC-SERVICE-SPEC.md` §2.1)
- **Response 200**: `MetricQueryResponse` (`docs/07-data-platform/METRIC-SERVICE-SPEC.md` §2.2)
- **Errors**: 400 `INVALID_DIMENSION_FILTER`, 404 `METRIC_NOT_REGISTERED`, 422 `TEMPORAL_LEAKAGE_REJECTED`

### 5.2. Anomaly Detection Execution API
- **Endpoint**: `POST /api/v1/analytics/anomalies/detect`
- **Auth**: `Authorization: Bearer <token>` (Scope: `analytics:write`)
- **Headers**: `Idempotency-Key: <key>`, `X-Correlation-ID: <uuid>`
- **Request Body**:
  ```json
  {
    "metric_id": "METRIC-001",
    "observation_window": {"start_time": "2026-02-14T00:00:00Z", "end_time": "2026-02-15T00:00:00Z"},
    "detector_id": "DET-STL-RESIDUAL-001",
    "as_of_time": "2026-02-15T00:00:00Z"
  }
  ```
- **Response 200 / 201**: Anomaly detection result record with `is_anomaly`, `anomaly_id` (if detected), and score.

### 5.3. Anomaly Listing and Filtering API
- **Endpoint**: `GET /api/v1/analytics/anomalies`
- **Auth**: `Authorization: Bearer <token>` (Scope: `analytics:read`)
- **Query Parameters**:
  - `status`: Filter by lifecycle state (`DETECTED`, `VALIDATED`, `LOCALIZED`, `ACKNOWLEDGED`, `RESOLVED`)
  - `metric_id`: Filter by metric (e.g., `METRIC-001`)
  - `severity`: Filter by severity (`CRITICAL`, `MAJOR`, `MINOR`, `INFORMATIONAL`)
  - `from_time`, `to_time`: Temporal observation filter
  - `limit`: Default 50, Max 200
  - `cursor`: Opaque pagination token
- **Response 200**: Paginated list of `Anomaly` records.

### 5.4. Anomaly Detail API
- **Endpoint**: `GET /api/v1/analytics/anomalies/{anomaly_id}`
- **Auth**: `Authorization: Bearer <token>` (Scope: `analytics:read`)
- **Response 200**: Complete `Anomaly` record adhering to `docs/02-domain/ANOMALY-DOMAIN-SPEC.md` §2.1.
- **Errors**: 404 `RESOURCE_NOT_FOUND` if anomaly does not exist within caller's tenant boundary.

### 5.5. Dimensional Localization Drill-Down API
- **Endpoint**: `POST /api/v1/analytics/anomalies/{anomaly_id}/localize`
- **Auth**: `Authorization: Bearer <token>` (Scope: `analytics:write`)
- **Headers**: `Idempotency-Key: <key>`, `X-Correlation-ID: <uuid>`
- **Request Body**:
  ```json
  {
    "dimension": "carrier_id",
    "secondary_dimension": "warehouse_id"
  }
  ```
- **Response 200**: `AnomalyLocalization` object (`docs/02-domain/ANOMALY-LOCALIZATION-SPEC.md` §3).

### 5.6. Anomaly Lifecycle State Transition API
- **Endpoint**: `POST /api/v1/analytics/anomalies/{anomaly_id}/transition`
- **Auth**: `Authorization: Bearer <token>` (Scope: `analytics:write` or `operator:admin`)
- **Headers**: `Idempotency-Key: <key>`, `X-Correlation-ID: <uuid>`
- **Request Body**:
  ```json
  {
    "target_state": "ACKNOWLEDGED",
    "reason": "Investigation workflow wf_01h8abc launched by analyst",
    "metadata": {"investigation_id": "inv_01h8abcde12345"}
  }
  ```
- **Response 200**: Updated anomaly record with new status and transition audit ID.
- **Errors**: 409 `INVALID_STATE_TRANSITION` if precondition not met.

---

## 6. Investigation & Governed Evidence API Contracts (Phase 03)

### 6.1. Create Investigation API
- **Endpoint**: `POST /api/v1/investigations`
- **Auth**: `Authorization: Bearer <token>` (Scope: `investigation:write`)
- **Headers**: `Idempotency-Key: <key>`, `X-Correlation-ID: <uuid>`, `X-Causation-ID: <uuid>`
- **Request Body**:
  ```json
  {
    "anomaly_id": "anom_01h8abc12345",
    "metric_name": "order_cancellation_rate",
    "investigation_scope": {"region": "US-EAST", "warehouse_id": "WH-01"},
    "window_start": "2026-05-10T00:00:00Z",
    "window_end": "2026-05-17T00:00:00Z",
    "as_of_time": "2026-05-18T00:00:00Z",
    "time_budget_seconds": 300,
    "cost_budget_usd": 2.00
  }
  ```
- **Response 202 (Accepted)**:
  ```json
  {
    "investigation_id": "inv_01h8abcde12345",
    "workflow_id": "tenant/ten_01h8abc/investigation/inv_01h8abcde12345",
    "status": "INITIALIZING",
    "created_at": "2026-09-03T18:30:00Z"
  }
  ```
- **Errors**: 400 `INVALID_INPUT`, 403 `TENANCY_VIOLATION`, 429 `BUDGET_RATE_LIMITED`.

### 6.2. Get Investigation Detail API
- **Endpoint**: `GET /api/v1/investigations/{investigation_id}`
- **Auth**: `Authorization: Bearer <token>` (Scope: `investigation:read`)
- **Response 200**: Full `InvestigationState` object including lifecycle status, budget usage, task progress, and sealed manifest if completed.
- **Errors**: 404 `RESOURCE_NOT_FOUND` if outside tenant.

### 6.3. List Investigations API
- **Endpoint**: `GET /api/v1/investigations`
- **Auth**: `Authorization: Bearer <token>` (Scope: `investigation:read`)
- **Query Params**: `status`, `metric_name`, `limit` (max 50), `cursor`.
- **Response 200**: Paginated list of investigations for the authenticated tenant.

### 6.4. Investigation Plan Validation API
- **Endpoint**: `POST /api/v1/investigations/{investigation_id}/validate-plan`
- **Auth**: `Authorization: Bearer <token>` (Scope: `investigation:write`)
- **Request Body**: `Plan` schema with DAG tasks.
- **Response 200**: `{"is_valid": true, "depth": 3, "fan_out": 4, "total_tasks": 8}`.
- **Errors**: 422 `INVALID_DAG` if cycles, depth > 4, or fan-out > 8 detected.

### 6.5. Get Investigation Evidence API
- **Endpoint**: `GET /api/v1/investigations/{investigation_id}/evidence`
- **Auth**: `Authorization: Bearer <token>` (Scope: `investigation:read`)
- **Query Params**: `classification`, `source_system`, `limit`, `cursor`.
- **Response 200**: List of `EvidenceRecord` objects with provenance, content digest, and verified citation spans.

### 6.6. Get Hypotheses and Verification Results API
- **Endpoint**: `GET /api/v1/investigations/{investigation_id}/hypotheses`
- **Auth**: `Authorization: Bearer <token>` (Scope: `investigation:read`)
- **Response 200**: `VerificationResult` containing ranked hypotheses, supporting/contradicting evidence links, and `status` (`VERIFIED`, `REFUTED`, `NEED_MORE_EVIDENCE`).

### 6.7. Investigation Signal Control APIs (Pause / Resume / Cancel)
- **Endpoints**:
  - `POST /api/v1/investigations/{investigation_id}/pause`
  - `POST /api/v1/investigations/{investigation_id}/resume`
  - `POST /api/v1/investigations/{investigation_id}/cancel`
- **Auth**: `Authorization: Bearer <token>` (Scope: `investigation:admin`)
- **Headers**: `Idempotency-Key: <key>`, `X-Correlation-ID: <uuid>`
- **Request Body**: `{"reason": "Analyst manual pause"}`
- **Response 200**: `{"status": "PAUSED", "signal_received_at": "2026-09-03T18:35:00Z"}`.

### 6.8. Read-Only SQL Capability Internal Execution API
- **Endpoint**: `POST /api/v1/capabilities/sql/query`
- **Auth**: Service Token (Scope: `capability:execute_internal`)
- **Request Body**: `CapabilityRequest` with registered capability ID and parameters.
- **Response 200**: `CapabilityResult` with row digest and evidence record reference.
- **Errors**: 400 `ERR_UNAUTHORIZED_ENTITY`, 403 `ERR_TENANT_MISMATCH`, 408 `ERR_QUERY_TIMEOUT`.

### 6.9. Governed Retrieval Internal API
- **Endpoint**: `POST /api/v1/retrieval/query`
- **Auth**: Service Token (Scope: `retrieval:execute_internal`)
- **Request Body**: `RetrievalQuery` with filters, as_of_time, and top_k.
- **Response 200**: List of `RetrievedEvidenceChunk` with verified citation spans.
- **Errors**: 403 `ERR_ACL_DENIED`, 404 `NO_AUTHORIZED_EVIDENCE`.

---

## 7. Phase 04 Hypothesis, Causal Study, and Verification APIs

### 7.1. Propose Investigation Hypotheses API
- **Endpoint**: `POST /api/v1/investigations/{investigation_id}/hypotheses`
- **Auth**: `Authorization: Bearer <token>` (Scope: `investigation:write`)
- **Headers**: `Idempotency-Key: <key>`, `X-Correlation-ID: <uuid>`
- **Request Body**: List of candidate statements and hypothesis types.
- **Response 201**: List of `HypothesisRecord` objects in `PROPOSED` status.
- **Errors**: 400 `ERR_INVALID_HYPOTHESIS_TYPE`, 403 `ERR_TENANT_MISMATCH`.

### 7.2. Rank Competing Hypotheses API
- **Endpoint**: `POST /api/v1/investigations/{investigation_id}/hypotheses/rank`
- **Auth**: `Authorization: Bearer <token>` (Scope: `investigation:write`)
- **Request Body**: `{"evidence_bundle_id": "uuid", "evaluation_weights": {"w_sup": 0.40, "w_con": 0.45}}`
- **Response 200**: List of `HypothesisRecord` sorted by `ordinal_rank`, detailing supporting/contradicting evidence links and status (`VERIFIED`, `REFUTED`, `NEED_MORE_EVIDENCE`).
- **Errors**: 404 `ERR_EVIDENCE_BUNDLE_NOT_FOUND`.

### 7.3. Deterministic Claim Verification API
- **Endpoint**: `POST /api/v1/claims/verify`
- **Auth**: `Authorization: Bearer <token>` (Scope: `investigation:read`)
- **Request Body**: `{"statement": str, "category": ClaimCategory, "evidence_references": [UUID], "temporal_as_of": UtcDateTime}`
- **Response 200**: `VerifiedClaim` schema with `verifier_status` (`VERIFIED`, `UNSUPPORTED`, `CONTRADICTED`, `NEED_MORE_EVIDENCE`) and `rejection_reason`.

### 7.4. Execute Causal Study API
- **Endpoint**: `POST /api/v1/causal/studies`
- **Auth**: `Authorization: Bearer <token>` (Scope: `causal:write`)
- **Headers**: `Idempotency-Key: <key>`, `X-Correlation-ID: <uuid>`
- **Request Body**:
  ```json
  {
    "investigation_id": "018f3a20-0000-7000-8000-000000000001",
    "causal_question": "What was the ATE of truck capacity shortage on cancellation rate?",
    "treatment_variable": "carrier_truck_shortage",
    "outcome_variable": "order_cancelled",
    "unit_of_analysis": "order_id",
    "treatment_window": {"start": "2026-02-14T08:00:00Z", "end": "2026-02-21T23:59:59Z"},
    "estimand_type": "ATE",
    "estimator": "DOUBLY_ROBUST_AIPW"
  }
  ```
- **Response 201**: `CausalStudy` record including `point_estimate`, `confidence_interval_95`, `overlap`, and `sensitivity`.
- **Errors**: 422 `ERR_OVERLAP_VIOLATION`, 422 `ERR_POST_TREATMENT_COLLIDER`, 403 `ERR_TENANT_MISMATCH`.

### 7.5. Get Causal Study Results API
- **Endpoint**: `GET /api/v1/causal/studies/{study_id}`
- **Auth**: `Authorization: Bearer <token>` (Scope: `causal:read`)
- **Response 200**: Full `CausalStudy` specification with sensitivity diagnostics, E-value, and limitations.

### 7.6. Replay Causal Study API
- **Endpoint**: `POST /api/v1/causal/studies/{study_id}/replay`
- **Auth**: `Authorization: Bearer <token>` (Scope: `causal:read`)
- **Response 200**: Deterministic replay verification confirming bitwise identical `point_estimate` and CI against frozen snapshot.

---

## 8. Phase 05 Churn, Uplift, and Decision Optimization APIs

### 8.1. Predict Calibrated Churn Risk API
- **Endpoint**: `POST /api/v1/ml/churn/score`
- **Auth**: `Authorization: Bearer <token>` (Scope: `analytics:read`)
- **Request Body**: `{"customer_id": "cust_12345", "as_of_time": "2026-02-15T00:00:00Z"}`
- **Response 200**: `ChurnPredictionRecord` including `calibrated_probability`, `risk_tier`, `ece_at_release`, and `is_treatment_contaminated`.
- **Errors**: 404 `ERR_CUSTOMER_NOT_FOUND`, 422 `ERR_UNCALIBRATED_PROBABILITY`.

### 8.2. Get Local Feature Explanation (SHAP) API
- **Endpoint**: `GET /api/v1/ml/churn/{prediction_id}/explanation`
- **Auth**: `Authorization: Bearer <token>` (Scope: `analytics:read`)
- **Response 200**: `LocalExplanationRecord` containing top 5 feature attributions and mandatory epistemic warning: *"Feature attributions describe model statistical associations, not real-world causal mechanisms."*

### 8.3. Estimate Incremental Treatment Uplift API
- **Endpoint**: `POST /api/v1/ml/uplift/estimate`
- **Auth**: `Authorization: Bearer <token>` (Scope: `analytics:read`)
- **Request Body**: `{"customer_id": "cust_12345", "intervention_type": "SERVICE_CREDIT_VOUCHER", "as_of_time": "2026-02-15T00:00:00Z"}`
- **Response 200**: `UpliftScoreRecord` with `cate_estimate`, standard error, confidence interval, and `persuadability_segment`.
- **Errors**: 422 `ERR_OVERLAP_VIOLATION`.

### 8.4. Optimize Intervention Decision API
- **Endpoint**: `POST /api/v1/decisions/optimize`
- **Auth**: `Authorization: Bearer <token>` (Scope: `decision:write`)
- **Headers**: `Idempotency-Key: <key>`, `X-Correlation-ID: <uuid>`
- **Request Body**: `DecisionRequest` schema with candidate interventions, budget allocation, and capacity limits.
- **Response 200**: `RecommendationRecord` with selected intervention, expected utility, ranking, constraint evaluation results, and `decision_digest`.
- **Errors**: 403 `ERR_TENANT_MISMATCH`, 422 `ERR_INVALID_CANDIDATES`.

### 8.5. Simulate Budget Allocation API
- **Endpoint**: `POST /api/v1/decisions/simulate-budget`
- **Auth**: `Authorization: Bearer <token>` (Scope: `decision:read`)
- **Request Body**: `{"tenant_id": "ten_123", "target_cohort_filter": {...}, "budget_scenarios_usd": [500.0, 1000.0, 2500.0]}`
- **Response 200**: Simulated treatment distribution, expected retained ARR, and marginal ROI curves across budget steps.

---

## 9. Phase 06 Approval, Gateway, and Action APIs

### 9.1. Create Approval Request API
- **Endpoint**: `POST /api/v1/approvals`
- **Auth**: `Authorization: Bearer <token>` (Scope: `approval:write`)
- **Request Body**: `{"decision_id": "UUID", "action_type": str, "target_entities": [str], "payload": dict, "estimated_cost_usd": Decimal}`
- **Response 201**: `ApprovalRequestRecord` with status `PENDING`, sealed `payload_digest`, and required `approval_tier`.

### 9.2. Sign and Grant Approval API
- **Endpoint**: `POST /api/v1/approvals/{approval_id}/approve`
- **Auth**: `Authorization: Bearer <token>` (Scope: `approval:tier_1` | `tier_2` | `tier_3`)
- **Request Body**: `{"expected_payload_digest": str, "comments": Optional[str]}`
- **Response 200**: `ApprovalRequestRecord` with status `APPROVED`.
- **Errors**: 403 `ERR_AGENT_SELF_APPROVAL`, 409 `ERR_APPROVAL_DIGEST_MISMATCH`, 422 `ERR_APPROVAL_EXPIRED`.

### 9.3. Execute Action Dry-Run API
- **Endpoint**: `POST /api/v1/actions/dry-run`
- **Auth**: `Authorization: Bearer <token>` (Scope: `action:dry_run`)
- **Request Body**: `{"approval_id": "UUID", "idempotency_key": str}`
- **Response 200**: Simulated impact, cost summary, policy verification results, and zero external socket mutation.

### 9.4. Dispatch Approved Action API
- **Endpoint**: `POST /api/v1/actions/dispatch`
- **Auth**: `Authorization: Bearer <token>` (Scope: `action:write`)
- **Headers**: `Idempotency-Key: <key>`, `X-Correlation-ID: <uuid>`
- **Request Body**: `{"approval_id": "UUID", "idempotency_key": str}`
- **Response 202**: Accepted for asynchronous execution; returns initial `ActionLedgerRecord`.
- **Errors**: 403 `ERR_KILL_SWITCH_ACTIVE`, 409 `ERR_IDEMPOTENCY_CONFLICT`, 422 `ERR_APPROVAL_NOT_APPROVED`.

### 9.5. Safety Kill Switch Management API
- **Endpoint**: `POST /api/v1/actions/kill-switch`
- **Auth**: `Authorization: Bearer <token>` (Scope: `admin:kill_switch`)
- **Request Body**: `{"scope": "GLOBAL" | "TENANT" | "CAPABILITY", "target_id": Optional[str], "reason": str}`
- **Response 200**: Kill switch activated; propagation latency $< 500\text{ms}$.

---

## 10. Phase 07 Tenant Operations, Identity, Connector, and Quota APIs

### 10.1. Tenant Provisioning API
- **Endpoint**: `POST /api/v1/admin/tenants`
- **Auth**: `Authorization: Bearer <token>` (Scope: `platform_admin`, `is_system=True`)
- **Headers**: `Idempotency-Key: <key>`
- **Request Body**: `{"name": str, "slug": str, "tier": "SHARED"|"ENTERPRISE"|"REGULATED", "admin_email": str, "default_quotas": Optional[dict]}`
- **Response 201**: `{"tenant_id": "ten_...", "status": "PROVISIONING", "created_at": "..."}`
- **Errors**: 409 `TENANT_SLUG_EXISTS`, 422 `INVALID_TENANT_CONFIGURATION`.

### 10.2. Tenant Lifecycle Management (Suspend, Reactivate, Legal Hold)
- **Endpoint**: `POST /api/v1/admin/tenants/{tenant_id}/lifecycle`
- **Auth**: `Authorization: Bearer <token>` (Scope: `tenant_admin` or `platform_admin`)
- **Request Body**: `{"target_status": "SUSPENDED"|"ACTIVE"|"LEGAL_HOLD", "reason": str, "matter_id": Optional[str]}`
- **Response 200**: Updated tenant status envelope.
- **Errors**: 403 `INSUFFICIENT_AUTHORITY`, 409 `INVALID_LIFECYCLE_TRANSITION`.

### 10.3. Tenant Data Export API
- **Endpoint**: `POST /api/v1/admin/tenants/{tenant_id}/exports`
- **Auth**: `Authorization: Bearer <token>` (Scope: `tenant_admin`)
- **Request Body**: `{"export_scope": "FULL"|"AUDIT_ONLY"|"ANALYTICS_ONLY", "encryption_public_key": Optional[str]}`
- **Response 202**: `{"export_id": "exp_...", "status": "EXPORTING", "estimated_completion": "..."}`

### 10.4. Tenant Cascade Deletion API
- **Endpoint**: `DELETE /api/v1/admin/tenants/{tenant_id}`
- **Auth**: `Authorization: Bearer <token>` (Scope: `tenant_admin` + Dual Approval `platform_admin`)
- **Request Body**: `{"confirmation_digest": str, "dual_approval_token": str}`
- **Response 202**: Accepted for cascade purge; returns `{"deletion_job_id": "del_..."}`.
- **Errors**: 409 `LEGAL_HOLD_ACTIVE`, 403 `DUAL_APPROVAL_REQUIRED`.

### 10.5. SCIM 2.0 User & Group Management API
- **Base Endpoint**: `/scim/v2/{tenant_id}/Users`, `/scim/v2/{tenant_id}/Groups`
- **Auth**: `Authorization: Bearer <scim_token>`
- **Behavior**: Standard RFC 7643 / RFC 7644 schemas. Deactivating user (`{"active": false}`) revokes all sessions within 1000ms.

### 10.6. Connector Instance Management API
- **Endpoint**: `POST /api/v1/connectors`
- **Auth**: `Authorization: Bearer <token>` (Scope: `connector:manage`)
- **Request Body**: `{"provider": str, "sync_mode": "BATCH_PULL"|"WEBHOOK_PUSH", "secret_ref": str, "scopes": [str]}`
- **Response 201**: Initialized `ConnectorInstanceRecord` with status `CONFIGURED`.

### 10.7. Connector Inbound Webhook Receiver
- **Endpoint**: `POST /api/v1/connectors/{connector_id}/webhooks`
- **Auth**: Cryptographic signature validation (`HMAC-SHA256` in headers)
- **Headers**: Provider signature, timestamp, external event ID
- **Response 202**: `{"status": "ACCEPTED", "inbox_event_id": "evt_..."}`
- **Errors**: 401 `INVALID_SIGNATURE`, 400 `TIMESTAMP_OUT_OF_BOUNDS`, 413 `PAYLOAD_TOO_LARGE`.
