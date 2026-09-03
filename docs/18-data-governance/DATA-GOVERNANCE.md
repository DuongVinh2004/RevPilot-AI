# Data Governance Contract

Status: Proposed v0.1 — E03 specification output

Every data field has owner, tenant scope, classification, purpose, retention category, source/lineage and access policy. Source systems remain authoritative; raw, normalized and derived projections are rebuildable and labelled with as-of/source version. Collection, model/RAG context, logs and exports are purpose-limited and minimized.

Access is enforced through TenantContext, authorization and classification policy. Retention, deletion, export and legal hold requirements are `UNKNOWN` until legal/commercial policy is supplied; this blocks commercial implementation but not the abstract contract. Deletion emits a request/proof workflow across primary, derived, object, retrieval, cache, feature, evaluation, log and export stores; immutable audit keeps only allowlisted non-sensitive references.

Data-quality violations quarantine source records and surface freshness/lineage state; they never silently become canonical. Required tests cover classification, DLP/redaction, deletion/export propagation, as-of leakage and rebuild reconciliation. Traceability: `INV-DATA-001..002`, `INV-PRV-001`, `INV-AUD-002`.
