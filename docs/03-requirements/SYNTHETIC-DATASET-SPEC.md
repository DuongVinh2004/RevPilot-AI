# Synthetic Dataset and Ground-Truth Contract

Status: Proposed v0.1 — E04 specification output

The synthetic generator produces deterministic tenant-scoped revenue datasets from versioned scenario manifest, seed, generator version and output hash. It models canonical entities/times/currencies, ingestion anomalies, CRM drift, documents/evidence, interventions and hidden ground-truth incidents. Runtime investigation cannot access hidden truth labels.

Each scenario declares population, as-of window, tenant segmentation, causal data-generating process, treatment/outcome/confounders, anomaly/forecast/churn/uplift/RCA expected evaluation fields and leakage controls. Train/validation/test are time-based; fixtures assert no future data and no cross-tenant content. Output is non-production test data only and does not represent customer data or measured product performance.

Required verification: same manifest/seed yields same hash, referential/time consistency, tenant isolation, hidden label access denial, and benchmark manifest completeness. Traceability: `INV-DATA-001`, `NFR-AI-002..007`.
