# Temporal Workflow Contract

Status: Proposed v0.1 — E03 specification output

Temporal owns durable business sequencing, timers, retries, cancellation, compensation and history; AgentRuntime owns only bounded reasoning inside Activities. Workflow ID is `tenant/{tenantId}/investigation/{investigationId}`. `InvestigationWorkflowInput` requires trusted tenant/principal references, immutable scope/artifact digest, idempotency key and deadline. Signals (`approval`, `cancel`, `amend`) are authenticated at the application boundary; queries expose sanitized state only.

Workflow code is deterministic: network, database, model, clock and random work occur in Activities. Each Activity has explicit retry class, start-to-close, schedule-to-close and heartbeat policy; side-effect activities call Actions and use ledger idempotency. Cancellation stops new work, awaits compensatable activities, and records partial outcome. Unknown provider results transition to reconciliation. Versioning uses compatible workflow changes and replay tests; no history rewrite.

Traceability: `INV-WF-001..002`, `INV-ACT-002`, `NFR-DUR-001`, `NFR-REL-001`; ADR-0002.
