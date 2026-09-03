# Data Platform Contract

Status: Proposed v0.1 — E04 specification output

Data zones are raw immutable source capture, normalized source mapping, and canonical RevPilot projections. Source systems remain authoritative; each derived record carries source reference/version, tenant, event/effective/as-of time, classification, lineage and quality state. Metric definitions are versioned with calculation, grain, currency/timezone, valid-as-of semantics and owner.

Ingestion validates schema, tenant, timestamps and idempotency before normalized/canonical publication. Malformed/schema-drift/late data is quarantined with freshness status; it never silently changes a metric. Projection rebuild and reconciliation use source manifests/hashes. Analytics/ML/RAG consume authorized as-of views and cannot use future information.

Traceability: `INV-DATA-001..002`, `INV-EVD-001`, `NFR-AI-004`; PostgreSQL baseline per ADR-0004.
