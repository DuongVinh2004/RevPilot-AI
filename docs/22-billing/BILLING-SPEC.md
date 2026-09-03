# Billing Contract

Status: Proposed v0.1 — E03 specification output

Billing owns plan, subscription, billable aggregation, invoice reference and credit ledger; it consumes immutable Usage records through a versioned query/event contract and never recalculates model/action source facts. Payment-card storage and live payment-provider integration are out of scope. Invoice state is `DRAFT|PROVISIONAL|FINALIZED|ADJUSTED|VOID_REFERENCE`; historical ledger entries are append-only adjustments, not rewrites.

Tenant entitlement changes are authorized admin operations, effective-dated and audited. Usage gaps retain provisional status and surface reconciliation; they do not silently overcharge. Financial-side-effect implementation requires 20/20 executor readiness and approved commercial/compliance decisions.

Traceability: `INV-COST-001`, `INV-AUD-001`, `NFR-COST-002`; unknown commercial billing/tax policy remains deferred.
