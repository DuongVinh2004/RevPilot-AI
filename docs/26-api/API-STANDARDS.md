# API Standards Contract

Status: Proposed v0.1 — E04 specification output

Public APIs are versioned REST contracts published from `packages/contracts`; controllers compose application ports and contain no business authority. Every authenticated request derives Principal/TenantContext server-side, carries correlation ID, validates schema, enforces authorization and returns stable error code/message. Client tenant/role fields are ignored/rejected.

Mutations require `Idempotency-Key`, scoped by tenant/principal/route/request digest with retained replay response; optimistic concurrency uses explicit version/ETag. Collections use bounded cursor pagination, explicit sort/filter allowlists and no unbounded exports. Errors use `{code,message,correlation_id,details?}`; details are safe/allowlisted. Version deprecation has compatibility window, owner and migration notice.

Rate limits, audit and policy requirements are per endpoint. API contracts declare auth, tenant, input/output, error, idempotency, pagination and audit before implementation. Traceability: `INV-TEN-002`, `INV-IAM-001`, `INV-AUD-001`.
