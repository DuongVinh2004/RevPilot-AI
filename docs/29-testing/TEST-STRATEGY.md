# Test Strategy Contract

Status: Proposed v0.1 — E04 specification output

Verification order is format/lint, unit, module integration, contract, data/model/AI eval, E2E, security/tenant, recovery/idempotency and performance proportional to risk. Tests use public contracts, synthetic fixtures and isolated non-production targets; no production secrets/data/destructive target.

Mandatory negative suites cover authentication/authorization/delegation, every-store tenant A/B isolation, RLS, RAG ACL/effective-date, injection/SSRF, policy/approval digest, action duplicate/UNKNOWN/kill switch, schema drift, event replay/DLQ, workflow replay/crash, audit tamper/redaction, deletion/export, model leakage/calibration/causal gates and DR restore. Every test maps to one requirement/invariant/acceptance ID.

Fixtures declare version, tenant, as-of and expected result. A target is not a passing measured test. Missing mandated coverage is failure, not a waived pass. Traceability: all `INV-*`, `NFR-*` and future exact `TEST-*` identifiers.
