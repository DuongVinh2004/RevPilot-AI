# Event Contract Standards

Status: Proposed v0.1 — E04 specification output

Baseline delivery is PostgreSQL transactional outbox, dispatcher and consumer inbox/dedup with at-least-once delivery and ordering only per aggregate key. Envelope fields are event ID/type/version, occurred-at UTC, producer, aggregate ID/version, trusted tenant reference, correlation/causation, idempotency key, classification and bounded payload reference. Outbox is not immutable audit.

Producer writes aggregate and outbox atomically. Consumer reauthorizes context, validates schema/version, deduplicates, applies declared retry class and quarantines poison/unsupported events for reconciliation. Payloads contain no credentials and minimized sensitive data. Evolution is additive/compatible until a declared migration window; replay uses versioned handler and cannot bypass current tenant/policy controls.

Traceability: `INV-DATA-002`, `INV-TEN-001`, `INV-SEC-001`, ADR-0007.
