# Experience Plane Contract

Status: Proposed v0.1 — E04 specification output

The web client renders investigation, evidence, recommendation, approval, action outcome, freshness/degraded state and audit-safe explanations from versioned API contracts. It has no database/provider credentials and cannot create tenant/role authority. Server responses control permitted actions; UI hiding is never authorization.

Every state represents loading, empty, unauthorized, stale/partial, failed and success explicitly. Evidence citations show provenance/effective date/classification according to access policy. Approval UI displays immutable action/target/cost/policy/version/expiry digest and invalidates on amendment/expiry. Generative explanation is labelled with evidence/limitation and never exposes chain-of-thought.

Required tests: accessibility, tenant/permission negatives, stale/partial behavior, error safety, digest tamper/replay and keyboard/screen-reader flows. Traceability: `INV-TEN-002`, `INV-ACT-003`, `INV-EVD-001`.
