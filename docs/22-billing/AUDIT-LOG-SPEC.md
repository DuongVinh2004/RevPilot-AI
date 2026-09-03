# Immutable Audit Log Contract

Status: Proposed v0.1 — E03 specification output

Audit owns append-only `AuditEvent` and `IntegrityCheckpoint`, separate from operational traces. Required event fields: ID, timestamp UTC, tenant or privileged-context reference, actor/delegation, action/resource, decision/policy/approval/artifact references, outcome, correlation/causation, previous/hash reference and classification. Allowed payload is minimized structured metadata; raw prompts, secrets and raw PII are prohibited.

Security/policy/approval/action/privileged changes are captured at 100% sampling. Append failure or integrity uncertainty blocks high-risk writes/actions. Query access is tenant/role scoped; an audit event cannot grant authorization. Retention/legal hold policy is UNKNOWN pending authority, but integrity/deletion boundaries must preserve the applicable legal obligation rather than silently remove evidence.

Required tests cover required-event completeness, chain verification, tamper, tenant query isolation and redaction. Traceability: `INV-AUD-001..002`, `NFR-AUD-001`, `NFR-OBS-002`.
