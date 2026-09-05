# Synthetic Dataset and Ground-Truth Specification

Status: Accepted Canonical Specification
Initiative: REVPILOT
Phase: Phase 01 — Canonical Data and Synthetic Benchmark
Owner: AI/ML Architecture + Data Architecture
Traceability: `BR-001`, `BR-002`, `FR-DET-001..003`, `FR-ML-001..004`, `FR-RCA-001..002`, `INV-TEN-001..003`, `INV-DATA-001`, `NFR-TEN-001`, `NFR-AI-002..007`, `AC-001`, `AC-002`, `AC-006`, `AC-014`
Approver: Duong Vinh (Repository Owner)
Version: v1.0
Last Reviewed Date: 2026-09-04

---

## 1. Scope and Architectural Objectives

This specification defines the deterministic synthetic dataset generation architecture, scenario injection parameters, time-leakage controls, and ground-truth isolation boundaries for RevPilot AI.

The synthetic benchmark serves as the primary evaluation bedrock for:
- Phase 01: Canonical data validation and reproducible benchmark generation.
- Phase 02: Statistical and machine learning anomaly detection.
- Phase 03: Governed multi-agent investigation DAGs and hybrid RAG evidence retrieval.
- Phase 04: Root-cause analysis (RCA) hypothesis verification and causal inference.
- Phase 05: Customer churn calibration and uplift decision optimization.

---

## 2. Dataset Profiles and Workload Sizing

The generator supports four discrete workload profiles designed for different development and validation phases:

| Profile | Purpose | Tenants | Order Count | Ticket Count | Time Span | Generation Target | Primary Use Case |
|---|---|---:|---:|---:|---:|---:|---|
| **`DEVELOPMENT`** | Fast local testing | 2 (`ten_alpha`, `ten_beta`) | 1,000 | 100 | 14 days | < 2 seconds | CI unit & contract tests |
| **`DEMO`** | Representative MVP | 3 (`ten_alpha`, `ten_beta`, `ten_gamma`) | 25,000 | 2,500 | 90 days | < 30 seconds | E2E investigation walkthroughs |
| **`INITIAL_COMMERCIAL`** | Baseline simulation | 10 | 250,000 | 25,000 | 180 days | < 5 minutes | Anomaly & causal benchmarks |
| **`SCALE_GROWTH`** | Stress & capacity test | 50 | 2,000,000 | 200,000 | 365 days | Batch job | Performance & concurrency tests |

### Sizing and Entity Ratios
- Average order lines per order: `2.4`
- Shipments per order: `1.02` (split shipments in 2% of multi-item orders)
- Support tickets per order: `0.08` baseline (spikes to `0.35` under severe fulfillment disruption)
- Payment attempts per order: `1.04` (initial attempt + 4% retry after transient failure)

---

## 3. Reproducibility, Manifest, and Cryptographic Verifiability

### 3.1. Deterministic Generation Pipeline
The synthetic generator is fully deterministic. Given identical inputs, the generator produces byte-for-byte identical output files:
- Pseudo-random number generator (PRNG): Python `numpy.random.Generator` with PCG64 bit generator initialized with explicit integer seeds.
- Deterministic record sorting: All generated entity collections are sorted by `(tenant_id, event_time, id)` before serialization.
- Float formatting: Fixed-precision decimal strings (no non-deterministic scientific notation).
- Clock isolation: Wall-clock time is strictly decoupled from generation. All timestamps originate from the scenario reference timeline starting at `2026-01-01T00:00:00Z`.

### 3.2. Benchmark Manifest Schema (`manifest.json`)
Every generated dataset run produces an immutable manifest:
```json
{
  "$schema": "https://revpilot.ai/schemas/benchmark-manifest.v1.json",
  "manifest_id": "mnf_01h8abc1234567890",
  "generator_version": "1.0.0",
  "schema_version": "1.0.0",
  "scenario_version": "1.0.0",
  "profile": "DEVELOPMENT",
  "seed": 42,
  "generated_at_utc": "2026-09-03T18:00:00Z",
  "scenario_window": {
    "start_time": "2026-01-01T00:00:00Z",
    "end_time": "2026-01-15T00:00:00Z"
  },
  "tenants": ["ten_alpha", "ten_beta"],
  "entity_counts": {
    "customers": 200,
    "orders": 1000,
    "order_lines": 2400,
    "shipments": 1020,
    "support_tickets": 100,
    "maintenance_events": 14,
    "contracts": 40,
    "payment_references": 1040
  },
  "artifact_hashes": {
    "raw_orders_csv": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "raw_shipments_csv": "sha256:a1b2c3d4e5f60718293a4b5c6d7e8f90123456789abcdef0123456789abcdef0",
    "ground_truth_labels_json": "sha256:7f83b1657ff1fc53b92dc18148a1d65dfc2d4b1fa3d677284addd200126d9069"
  }
}
```

### 3.3. Regeneration and Mismatch Behavior
- Verification command: `python -m revpilot.benchmark.verify_manifest --manifest manifest.json --data-dir ./fixtures`
- If any artifact hash differs from the manifest: Exit code 1; raise `BenchmarkVerificationFailureError`.
- Under no circumstances is a mismatched dataset used for evaluation or test gating (`AC-001`, `AC-014`).

---

## 4. Multi-Tenant Isolation and A/B Negative Matrix

### 4.1. Dual-Tenant Architecture Baseline
Every synthetic dataset generates at least two completely isolated tenants:
1. `ten_alpha` ("Alpha Logistics & Retail"): Target tenant experiencing injected business disruption.
2. `ten_beta` ("Beta Commerce Global"): Parallel control tenant operating in the same calendar window with standard operational baseline behavior.

### 4.2. Isolation Invariants
- **No Shared Entities**: Customer IDs, Order IDs, and Ticket IDs are prefixed and strictly disjoint between `ten_alpha` and `ten_beta`.
- **Cross-Tenant References Prohibited**: A foreign key pointing across tenant boundaries violates `INV-TEN-001` and fails `DQ-REF-001`.
- **Negative Isolation Fixtures**: Automated tests assert that an authenticated query executed in `ten_beta` context returns exactly 0 rows when attempting to access `ten_alpha` entity IDs.

---

## 5. Temporal Splitting, Leakage Controls, and Watermarking

### 5.1. Chronological Dataset Split
Datasets are partitioned along the time axis to model real-world learning and evaluation:
- **Historical Train Window**: Days 1 to 30 (Baseline historical pattern learning, STL decomposition).
- **Validation Window**: Days 31 to 44 (Threshold calibration, parameter tuning).
- **Evaluation / Incident Window**: Days 45 to 60 (Scenario injection window, real-time investigation testing).

```text
Day 1                       Day 30        Day 44             Day 52          Day 60
  ├───────────────────────────┼─────────────┼──────────────────┼───────────────┤
  │       Train Split         │  Val Split  │ Incident Active  │ Post-Incident │
  │   (Normal Baselines)      │ (Calibrate) │ (Truck Shortage) │ (Recovery)    │
  └───────────────────────────┴─────────────┴──────────────────┴───────────────┘
                                            ▲
                                       as_of Watermark
```

### 5.2. Anti-Leakage Invariants (`INV-DATA-001`)
1. **No Future Data in Features**: When evaluating an investigation as of `Day 47 12:00:00Z`, all records with `event_time > Day 47 12:00:00Z` or `ingested_at > Day 47 12:00:00Z` MUST be excluded from feature vectors, SQL queries, and RAG retrieval.
2. **No Label Leakage**: Entity primary keys, tracking numbers, customer emails, support ticket IDs, and filenames MUST NOT contain strings such as `incident`, `truck_delay`, `ground_truth`, or `root_cause`.
3. **Out-of-Order and Late Arrival Fixtures**: 3% of orders and 5% of shipment events are injected with simulated ingestion delays (`ingested_at - event_time > 24 hours`) to test watermark resilience and backfill consistency.

---

## 6. Primary Causal Scenario: Midwest Truck-Capacity Incident

### 6.1. Incident Metadata
- **Incident ID**: `INC-SYNTH-TRUCK-001`
- **Version**: `1.0.0`
- **Scenario Name**: Midwest Regional Carrier Fleet Capacity Disruption
- **Affected Tenant**: `ten_alpha`
- **Control Tenant**: `ten_beta` (unaffected control population)
- **Causal Disruption Window**:
  - Starts: `Day 45 (2026-02-14) 08:00:00Z`
  - Ends: `Day 52 (2026-02-21) 23:59:59Z`
  - Total Duration: 7.66 days (184 hours)

### 6.2. Geographic and Operational Scope
- **Origin Facility**: `WH-MIDWEST-01` (Warehouse facility in Chicago, IL).
- **Logistics Carrier**: `CARRIER_REGIONAL_LOGISTICS`.
- **Service Scope**: Regional Ground Outbound Shipments.
- **Unaffected Scope within `ten_alpha` (Internal Control Group)**:
  - Shipments from `WH-WEST-01` (Reno, NV).
  - Shipments handled by `CARRIER_AIR_EXPRESS`.

### 6.3. Mechanistic Causal Chain
```text
[Fleet Capacity Shortage at CARRIER_REGIONAL_LOGISTICS]
                      │
                      ▼
[Warehouse WH-MIDWEST-01 Outbound Dispatch Backlog]
(Dispatch latency increases from baseline 12h to 84h)
                      │
                      ▼
[Fulfillment Delivery Delay & SLA Breaches]
(Delivery SLA breaches spike from baseline 2.1% to 38.4%)
                      │
                      ▼
[Customer Dissatisfaction & Support Ticket Inquiries]
(Topic ORDER_STATUS_DELAY volume increases by 4.5x)
                      │
                      ▼
[Customer Order Cancellations Spike]
(cancellation_rate rises from baseline 1.8% to 8.4% on affected cohort)
                      │
                      ▼
[Revenue at Risk & Financial Loss]
(Elevated revenue loss of ~$142,000 USD on affected Midwest orders)
```

### 6.4. Injected Confounders and Noise
To rigorously test causal discovery and prevent trivial correlation matching, the scenario injects realistic real-world confounders:
1. **Confounder 1 — Northeast Winter Storm Event**:
   - Time window: Day 46 to Day 48.
   - Region: `US-NORTHEAST`.
   - Effect: Injected weather alert documents and minor delivery delays in Boston/New York. However, this did NOT cause the Midwest cancellation spike. The causal engine must identify that Midwest cancellations are conditionally independent of the Northeast storm.
2. **Confounder 2 — Marketing Category Promotion**:
   - Time window: Day 44 to Day 50.
   - Category: `ELECTRONICS`.
   - Effect: 25% increase in order volume across all warehouses.
3. **Plausible Alternative 1 — Payment Gateway Outage (Disproved Alternative)**:
   - Competing hypothesis: "Payment gateway timeouts caused customer checkout failure and drop-off."
   - Disproving evidence: Metric `payment_failure_rate` remains stable at `1.2%` across the entire incident window (`METRIC-005`).
4. **Plausible Alternative 2 — Product Quality Defect (Disproved Alternative)**:
   - Competing hypothesis: "Recent batch of SKU-8899 had manufacturing defects prompting returns and cancellations."
   - Disproving evidence: Return reasons cite `CUSTOMER_REQUEST_DELAY` in 89% of cases, not defective merchandise.

### 6.5. True Ground-Truth Annotations (Isolated)
Stored exclusively in `ground_truth.incidents`:
- `true_root_cause`: `TRUCK_CAPACITY_SHORTAGE_MIDWEST`
- `true_causal_effect_ate`: `+0.0660` (+6.6% absolute increase in cancellation rate for orders originating at `WH-MIDWEST-01` handled by `CARRIER_REGIONAL_LOGISTICS`)
- `affected_order_count`: `482`
- `affected_revenue_cents`: `14256000` ($142,560.00 USD)

### 6.6. Data-Generating Process (DGP) Mathematical Equations

To guarantee formal falsifiability and rigorous benchmarking under `NFR-AI-007`, the synthetic data engine models the incident using an explicit structural causal model (SCM):

1. **Treatment Assignment Mechanism ($T_i$)**:
   $$P(T_i = 1 \mid X_i) = \text{logit}^{-1}\left( \alpha_0 + \alpha_1 \cdot \mathbb{I}(\text{wh}_i = \text{WH-MIDWEST-01}) + \alpha_2 \cdot \mathbb{I}(\text{carr}_i = \text{CARRIER_REGIONAL}) + \alpha_3 \cdot \log(\text{vol}_i) \right)$$
   Where parameters ensure common support ($0.08 \le P(T_i=1 \mid X_i) \le 0.88$).

2. **Outbound Dispatch Delay Mediator ($M_i$ in hours)**:
   $$M_i = 12.0 + 72.0 \cdot T_i + 8.5 \cdot \mathbb{I}(\text{storm}_i) + \mathcal{N}(0, 4.0)$$
   During Days 45–52, treatment $T=1$ shifts dispatch delay from $12\text{h}$ baseline to $84\text{h}$.

3. **Order Cancellation Probability ($Y_i$)**:
   $$P(Y_i = 1 \mid T_i, M_i, X_i) = \text{logit}^{-1}\left( \gamma_0 + \gamma_{\text{direct}} \cdot T_i + \gamma_{\text{delay}} \cdot \left(\frac{M_i - 12}{24}\right) + \gamma_{\text{tier}} \cdot \mathbb{I}(\text{tier}_i = \text{ENTERPRISE}) \right)$$
   Parameters $\gamma$ are calibrated such that marginal expectations satisfy:
   $$\mathbb{E}[Y(T=1)] = 0.0840, \quad \mathbb{E}[Y(T=0)] = 0.0180 \implies \text{ATE} = 0.0840 - 0.0180 = +0.0660$$

4. **Confounder & Noise Injections**:
   - Confounder $X_{\text{storm}}$ affects Northeast deliveries but is conditionally independent of Midwest carrier assignments.
   - Confounder $X_{\text{promo}}$ increases order volume by $+25\%$ but preserves baseline cancellation rate across control cohorts.

---

## 7. Ground-Truth Access Control and Air-Gap Architecture

```text
┌───────────────────────────────────────────────────────────┐
│                    RevPilot Database                      │
│                                                           │
│  ┌─────────────────────────┐   ┌───────────────────────┐  │
│  │   canonical.* Tables    │   │  ground_truth Schema  │  │
│  │ (Orders, Shipments, etc)│   │  (Hidden incident DAG)│  │
│  └─────────────────────────┘   └───────────────────────┘  │
└────────────────┬───────────────────────────┬──────────────┘
                 │                           │
                 │ SELECT                    │ SELECT (Privileged)
                 ▼                           ▼
      ┌─────────────────────┐     ┌───────────────────────┐
      │ Investigation Engine│     │  Evaluation Harness   │
      │   (Agents / LLM)    │     │(Offline Benchmarking) │
      └─────────────────────┘     └───────────────────────┘
                 │
                 ▼
      [NO GROUND TRUTH ACCESS]
      (Enforced by DB Permissions & API Policy)
```

1. **PostgreSQL Role Isolation**: The application runtime role (`revpilot_app`) has explicit `REVOKE ALL ON SCHEMA ground_truth FROM revpilot_app`. Attempting to query ground truth raises `insufficient_privilege`.
2. **Air-Gapped Evaluation**: The benchmark evaluator runs in an offline batch container authenticated as `revpilot_evaluator`. It compares the output of the investigation DAG (`Investigation.hypotheses`, ranked RCA output) against `ground_truth.incidents` without exposing the truth labels to the LLM context.
3. **No Trace Exposure**: Prompt templates, reasoning traces, and audit logs are scanned for ground-truth identifiers.
