# Rail Status

Status: Authoritative execution gate snapshot v7.0 — Rail 0 GREEN, Rail 1 GREEN, Rail 2 GREEN, Rail 3 GREEN, Rail 4 GREEN, Rail 5 GREEN, Rail 6 GREEN, Rail 7 GREEN, Rails 8–18 LOCKED

| Rail | State | Evidence | Blocker to GREEN |
|---|---|---|---|
| 0 — Repository/tooling foundation | GREEN | E01–E05 PASS; 12 ADRs Accepted (`ADR-0001..0012`); `DECISION-CLOSURE-REGISTER.md`; `TRACEABILITY-CLOSURE-MATRIX.md` closed; `TASK-BOOTSTRAP-001` PASS (scaffold, manifests, topology pytest pass, git baseline clean); see `CURRENT-STATE-RECONCILIATION.md` | None |
| 1 — Core domain primitives | GREEN | TASK-R01-001..004 PASS; shared kernel identifiers, temporal, monetary, errors, results, and context pass automated unit and contract tests | None |
| 2 — Tenant context & lifecycle | GREEN | TASK-R02-001..004 PASS; tenancy domain models, lifecycle state machine, ports, in-memory adapter, and exhaustive cross-tenant negative matrix pass 100 automated tests (fail-closed exit gate verified) | None |
| 3 — Authentication | GREEN | TASK-R03-001 PASS (21 unit tests pass); TASK-R03-002 PASS (17 unit tests pass); TASK-R03-003 PASS (16 unit tests pass); TASK-R03-004 PASS (29 exit gate and contract tests pass, 183/183 total tests pass) | None |
| 4 — Authorization & Delegation | GREEN | TASK-R04-001 PASS (27 unit tests pass); TASK-R04-002 PASS (12 unit tests pass); TASK-R04-003 PASS (23 unit tests pass); TASK-R04-004 PASS (28 exit gate and contract tests pass, 273/273 total backend tests pass) | None |
| 5 — Persistence Isolation | GREEN | TASK-R05-001 PASS (15 unit tests pass); TASK-R05-002 PASS (9 unit tests pass); TASK-R05-003 PASS (16 unit tests pass); TASK-R05-004 PASS (30 exit gate and contract tests pass, 343/343 total backend tests pass) | None |
| 6 — Investigation Domain & Budget | GREEN | TASK-P03-001 PASS (investigation domain model, state machine, and budget tracking pass 14 unit tests) | None |
| 7 — Durable Workflow Engine | GREEN | TASK-P03-002 PASS (Temporal investigation workflow, signals, replay durability pass 18 tests) | None |
| 8–18 | LOCKED | Canonical specifications expanded; Phase 03 tasks `TASK-P03-003..008`, Phase 04 tasks `TASK-P04-001..006`, Phase 05 tasks `TASK-P05-001..007`, Phase 06 tasks `TASK-P06-001..008`, Phase 07 tasks `TASK-P07-001..008`, and Phase 08 tasks `TASK-P08-001..008` authored (DRAFT) | Upstream rail gates (Rails 8–18) not GREEN |

`GREEN` on Rails 0–7 confirms that repository foundation, domain primitives, tenant lifecycle, authentication, authorization/delegation, persistence RLS isolation, investigation domain/budgeting, and Temporal durable workflow orchestration are fully implemented and verified under contracts and automated tests (947/947 tests PASS across workspace). Rail 6 and Rail 7 are `GREEN`. Rails 8–18 remain LOCKED.


