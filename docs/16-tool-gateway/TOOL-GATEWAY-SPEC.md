# Tool Gateway and Action Safety Contract

Status: Proposed v0.1 — E03 specification output

Actions owns `ActionIntent`, `ActionAttempt`, `ActionLedger` and `KillSwitch`; Tool Gateway is the only path to an external side effect. Before dispatch it revalidates trusted tenant/principal/delegation, registered tool/destination/schema version, policy result, required approval digest/expiry, budget, blast radius, idempotency key and kill state. MVP adapters are mock/dry-run only.

The idempotency key scopes tenant + action type + target + immutable intent digest; ledger uniqueness returns the original terminal/replay-safe response. Attempt states are `DRY_RUN|PENDING|DISPATCHED|CONFIRMED|FAILED|UNKNOWN|RECONCILING|COMPENSATED`. Timeout after dispatch is `UNKNOWN`, never blind retry. Reconciliation uses provider query/dedup evidence; compensation is permitted only for declared reversible actions. Irreversible actions require explicit policy/approval treatment.

Emit security/audit/action events at 100% sampling. Required tests cover policy/digest/expiry/replay tamper, dry-run, blast/budget, kill switch, crash-at-step, duplicate and unknown result. Traceability: `INV-ACT-001..004`, `NFR-SEC-001`, `NFR-DUR-001`.
