# FinOps and Metering Contract

Status: Proposed v0.1 — E03 specification output

Usage owns immutable `UsageRecord` and `CostAllocation`; attribution chain is Tenant -> User/Principal -> Investigation -> Agent -> Model/Tool -> provider usage. COGS is distinct from customer billing. Each record includes trusted tenant, artifact/tool version, quantity/unit, currency, provider reference, observed/estimated flag and idempotency key.

Before each spend boundary, enforce per-investigation model budget (USD2 target, USD5 default hard stop), tenant daily/monthly budget, call/token/tool/duration limits and action budget. A concurrent budget race must serialize/reject rather than overspend. Missing or unreconciled provider usage is provisional and cannot be invented; high-risk action is blocked when required cost guardrail is unavailable.

Reconcile daily/monthly against provider records; target >=99.5% attribution reconciliation. Emit budget/usage/reconciliation events without sensitive payloads. Traceability: `INV-COST-001`, `NFR-COST-001..002`.
