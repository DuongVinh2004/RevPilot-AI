# Connector Platform Contract

Status: Proposed v0.1 — E04 specification output

Connectors owns configuration, credential reference (never value), state, sync cursor/run, provider capability, schema/canonical mapping, health and rate-limit policy. Lifecycle: `DISCONNECTED -> AUTHORIZING -> INITIAL_SYNC -> ACTIVE -> DEGRADED -> REAUTH_REQUIRED -> PAUSED -> DISCONNECTED`. MVP uses mocks/dry-run, not commercial live integrations.

Sync requests require trusted tenant and scoped credential broker reference. Initial/incremental/webhook/CDC data validates signature/schema, deduplicates by provider event/cursor, records source version and quarantines drift/malformed records. Retries honor provider rate class/deadline; ambiguous writes go to reconciliation/DLQ, never blind replay. Adapter cannot decide policy or expose credentials; external action goes through Tool Gateway.

Traceability: `INV-SEC-001..003`, `INV-TEN-001`, `INV-DATA-002`, ADR-0009.
