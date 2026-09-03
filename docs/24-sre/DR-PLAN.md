# Disaster Recovery Plan Contract

Status: Proposed v0.1 — E03 specification output

Design target is transactional RPO <=5 minutes and RTO <=30 minutes. Recovery scope covers PostgreSQL, Temporal history/visibility, object/retrieval rebuild sources, configuration/secret references, audit integrity, workflow/action reconciliation and tenant tier. Backups, restore targets and providers are not selected in this planning pass; no DR capability is claimed as implemented.

An exercise validates restore into isolated non-production target, integrity/tenant checks, workflow replay compatibility, outbox/inbox reconciliation, action `UNKNOWN` reconciliation, evidence/retrieval rebuild and documented decision. Restore never uses test data to overwrite a production source. Incident recovery preserves audit evidence and uses a distinct authorized privileged context.

Failure of an exercise creates a blocker and remediation task; it does not relax RPO/RTO. Traceability: `NFR-REC-001`, `NFR-DUR-001`, `INV-ACT-002`, `INV-AUD-001`.
