# Definition of Done

Status: Proposed v0.1

## Task done

A task is done when all linked requirements and acceptance criteria are implemented; exact tests/evals pass; failure, security, tenancy, observability, idempotency, migration, and compensation requirements are exercised; docs/contracts/traceability are updated; no unrelated changes exist; and any deviation has an accepted ADR.

## Phase done

A phase is done when all mandatory tasks are accepted, migrations are rehearsed, rollback/recovery is tested, benchmark results are recorded as actual values, risks are updated, and downstream contracts are stable enough for dependent work.

## Production ready

- No open P0 security findings and no unaccepted Critical/High threat prerequisite.
- Cross-tenant tests pass with zero disclosure/write leakage.
- Approval binding, idempotency, reconciliation, blast limits, and all kill switches are verified.
- Backup restoration and DR exercise meet approved RPO/RTO.
- Offline/regression/adversarial/tenant/shadow/canary AI gates pass.
- Audit integrity and data deletion/export propagation are verified.
- Load/chaos tests meet approved SLOs; monitoring and alert ownership are active.
- Cost budgets, rate limits, and runaway-agent guardrails are enabled.
- Connector token expiry, revocation, schema drift, duplicate/out-of-order events, replay, and reconciliation are tested.
- Runbooks, on-call ownership, incident response, dependency/model inventory, and compliance evidence process exist.
- Production enablement of each real action adapter has separate operational approval.

Software controls provide compliance readiness evidence; they do not constitute SOC 2, ISO 27001, GDPR, or other certification.

