# Data Platform Architecture Specification

Status: Accepted Canonical Specification
Initiative: REVPILOT
Phase: Phase 01 — Canonical Data and Synthetic Benchmark
Owner: Data Architecture
Traceability: `BR-001`, `BR-004`, `INV-TEN-001`, `INV-TEN-002`, `INV-DATA-001`, `INV-DATA-002`, `INV-EVD-001`, `NFR-TEN-001`, `NFR-AI-004`, `ADR-0004`, `ADR-0005`
Approver: Duong Vinh (Repository Owner)
Version: v1.0
Last Reviewed Date: 2026-09-04

---

## 1. Architectural Overview and Invariants

The RevPilot Data Platform serves as the central data backbone for operational analytics, revenue anomaly detection, causal inference, and automated decision workflows. It enforces a strict layered data topology, separating raw ingestion from canonical business state and derived read-optimized projections.

### Core Architecture Invariants
1. **Relational Source of Truth (`ADR-0004`)**: PostgreSQL is the primary, authoritative relational store for all canonical transactional business entities, configuration, and audit logs.
2. **Tenant Isolation Across All Storage Surfaces (`ADR-0005`, `INV-TEN-001`)**: Isolation is enforced at the database level using composite keys `(tenant_id, id)` and PostgreSQL Row-Level Security (RLS). Storage partitions, object keys, and caches MUST encode `tenant_id`.
3. **Immutability of Source Truth (`INV-DATA-002`)**: Raw incoming records and external event streams are immutable. Derived projections, vector indexes, and analytical summaries are fully rebuildable from canonical state.
4. **Temporal Disambiguation and Anti-Leakage (`INV-DATA-001`)**: All analytical queries, baseline models, and investigation workflows execute relative to an explicit `as_of` watermark, strictly preventing future information leakage into historical analyses.
5. **Separation of Benchmark Ground Truth**: Synthetic benchmark labels and causal scenario annotations are isolated in a separate `ground_truth` schema and are inaccessible to the runtime investigation service.

### 1.1 Non-Goals (MVP / v1 Scope)
- **Real-Time Streaming CDC Engine**: Real-time sub-second streaming Change Data Capture (e.g. Debezium / Kafka) is deferred to post-Phase 07; initial architecture relies on scheduled batch sync and transactional PostgreSQL ingestion.
- **Distributed Big Data Engine**: Provisioning or managing multi-node Apache Spark or Hadoop clusters is out of scope; compute remains within single-instance PostgreSQL and in-process analytical workers.
- **Cross-Tenant Data Aggregation / Shared Lakehouse**: Universal multi-tenant data warehousing or shared lakehouse layers across distinct tenants are strictly prohibited (`INV-TEN-001`).

---

## 2. Layered Data Storage Topology

```text
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                                RevPilot Data Layer Topology                                  │
├───────────────────┬───────────────────┬──────────────────────────┬──────────────────────────┤
│ Layer / Zone      │ Technology Store  │ Access Pattern           │ Invariant & Authority    │
├───────────────────┼───────────────────┼──────────────────────────┼──────────────────────────┤
│ 1. Raw Zone       │ PostgreSQL (JSONB)│ Append-Only / WORM       │ Verbatim payload capture │
│ 2. Normalized     │ PostgreSQL        │ Ephemeral Staging        │ Typed syntactic mapping  │
│ 3. Canonical      │ PostgreSQL (RLS)  │ Transactional (ACID)     │ Authoritative domain truth│
│ 4. Ground Truth   │ PostgreSQL (Priv) │ Read-Only Fixture        │ Offline Evaluator ONLY   │
│ 5. Projections    │ Postgres / Redis  │ Read-Optimized Views     │ Rebuildable projections  │
└───────────────────┴───────────────────┴──────────────────────────┴──────────────────────────┘
```

1. **Raw Ingestion Zone**: Captures payloads from connectors, webhooks, and synthetic generators. Encapsulates `raw_payload`, `payload_hash` (SHA-256), `source_system`, `received_at`, and `tenant_id`.
2. **Normalized Transformation Staging**: Intermediate layer parsing JSONB strings into typed schemas, performing syntactic validations and mapping source IDs to internal tenant domains.
3. **Canonical Relational Core**: Governed by `docs/07-data-platform/CANONICAL-DATA-MODEL.md`. Enforces relational integrity, composite primary/foreign keys, business rules, and PostgreSQL RLS.
4. **Benchmark Ground-Truth Store**: Houses hidden scenario labels (`is_incident_affected`, `true_cause_id`, counterfactual treatment effects) generated for synthetic benchmarks. Governed by database permission restrictions (`REVOKE ALL ON ground_truth.* FROM revpilot_app`).
5. **Derived Projections & Feature Stores**: Read-optimized projections, hourly/daily pre-aggregated metric rollups, and document vector embeddings (`pgvector` per `ADR-0004`).

---

## 3. Component Architecture and Ingestion Flow

```text
   [Connector Platform / API / Synthetic Generator]
                          │
                          ▼
            ┌───────────────────────────┐
            │   Ingestion Controller    │ (Token auth, rate limits, size check)
            └───────────────────────────┘
                          │
                          ▼
            ┌───────────────────────────┐
            │       Raw Append Store    │ (Write to raw.events, compute hash)
            └───────────────────────────┘
                          │
                          ▼
            ┌───────────────────────────┐
            │    Data Quality Gateway   │ (Validates schema, types, tenant, range)
            └───────────────────────────┘
                    │            │
            FAIL    │            │ PASS
                    ▼            ▼
        ┌──────────────────┐  ┌───────────────────────────┐
        │  raw_quarantine  │  │   Canonical Loader Job    │
        └──────────────────┘  └───────────────────────────┘
                                         │
                                         ▼
                              ┌───────────────────────────┐
                              │  Canonical Core Database  │
                              └───────────────────────────┘
                                         │
                                         ▼
                              ┌───────────────────────────┐
                              │ Projection & Metric Engine│
                              └───────────────────────────┘
```

---

## 4. Time Semantics and Watermarking

The platform enforces four distinct temporal attributes across all data records:

1. `event_time`: The timestamp when the business event actually occurred in the external world (e.g., when the customer pressed "Place Order" or when the truck broke down). Used for all business metrics, trend baselines, and causal timelines.
2. `effective_from` / `effective_to`: The validity window of a business definition, contract, SLA clause, or policy rule. Used for point-in-time policy evaluation.
3. `ingested_at`: The platform arrival timestamp (UTC `CURRENT_TIMESTAMP`). Used for freshness monitoring, data arrival latency tracking, and operational SLA adherence.
4. `as_of_time`: A query-level parameter representing the perspective timestamp of the analyst or investigation. Any record where `ingested_at > as_of_time` or `event_time > as_of_time` is invisible to that query.

---

## 5. Metric Computation Architecture

All metric calculations MUST strictly resolve through the `AnalyticsPort` and conform to definitions in `docs/07-data-platform/METRIC-REGISTRY.md`.
- **Pre-Aggregated Rollups**: For high-volume operational metrics (e.g., hourly `order_volume`, `cancellation_rate`), background rollups compute incremental aggregations partitioned by `(tenant_id, grain, window_start)`.
- **On-Demand Slice Queries**: Analysts and investigation DAG nodes request dimensional slice queries (e.g., cancellation rate by carrier and warehouse). The SQL query generator enforces parameter allowlists and composite tenant filters. Unrestricted ad-hoc SQL generation is strictly prohibited (`FR-INV-004`).

---

## 6. Data Governance, Retention, and Deletion

1. **Classification Policy**: Every canonical entity defines its data classification level:
   - `PUBLIC`: General reference codes, public benchmarks.
   - `INTERNAL`: Operational warehouse IDs, carrier codes.
   - `CONFIDENTIAL`: Business aggregate revenue, customer names, contract terms.
   - `RESTRICTED_PII`: Customer emails, phone numbers, raw support ticket transcripts.
2. **Retention Classes**:
   - `REVENUE_FINANCIAL_7YR`: Orders, order lines, payment references (7-year statutory retention).
   - `OPERATIONAL_FULFILLMENT_2YR`: Shipments, warehouse maintenance logs (2-year retention).
   - `SERVICE_COMMUNICATION_1YR`: Support tickets, customer communication (1-year retention).
   - `BENCHMARK_SYNTHETIC_IMMUTABLE`: Synthetic benchmark datasets (retained until scenario deprecation).
3. **Tenant Offboarding / Deletion (`INV-TEN-003`, `FR-CTL-003`)**: Tenant deletion invokes a cascading delete job executing in transaction-scoped context, scrubbing all records where `tenant_id = :target_tenant_id` across canonical, raw, projection, and quarantine stores.

---

## 7. Downstream Contract Specifications

- Canonical Schema: [`CANONICAL-DATA-MODEL.md`](CANONICAL-DATA-MODEL.md)
- Metric Semantics: [`METRIC-REGISTRY.md`](METRIC-REGISTRY.md)
- Quality and Lineage: [`DATA-QUALITY-LINEAGE-SPEC.md`](DATA-QUALITY-LINEAGE-SPEC.md)
- Database Implementation: [`../27-database/DATABASE-SCHEMA.md`](../27-database/DATABASE-SCHEMA.md)
- Synthetic Benchmark: [`../03-requirements/SYNTHETIC-DATASET-SPEC.md`](../03-requirements/SYNTHETIC-DATASET-SPEC.md)
