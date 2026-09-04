# Documentation Closure Decisions and Open Contradictions

Status: Accepted v1.0
Owner: Principal Architecture, Security Architecture, SRE, AI Governance and Compliance
Approver: Duong Vinh (Explicit user confirmation covering Repository Owner, Principal Architecture, Security Architecture/IAM, SRE)
Date: 2026-09-04
Approval record: execution/APPROVAL-RECORD-RUN-R03-001.md
Scope: Canonical reconciliation rules for the documentation-completion phase.  
Traceability: SPECIFICATION-PRECEDENCE, SRS, NFR-BASELINE, PRODUCTION-READINESS-GATE, DECISION-CLOSURE-REGISTER

> [!IMPORTANT]
> This document makes documentation ambiguity explicit. It does not approve implementation, change executable policy, or convert any planned verification into an executed result.

## Canonical status rule

The current documentation target is:

`DOCUMENTATION COMPLETE / IMPLEMENTATION PENDING / EMPIRICAL VALIDATION PENDING / GO-LIVE BLOCKED`

“Documentation complete” means requirements, ownership, open decisions, expected evidence and contradictions are documented. It does not mean an Accepted implementation authority exists, code exists, tests passed, or operational evidence exists.

## Binding reconciliation decisions

| Topic | Canonical treatment now | Required approval/evidence before closure |
|---|---|---|
| Foundation documents marked Proposed while downstream docs are Accepted | Treat proposed foundations as authoritative only for content reference, never as implementation authorization. Accepted downstream documents must point to this approval dependency. | Named owner and approver accept foundation pack or downstream status is downgraded. |
| Credential lifetime | `15 minutes maximum` is the stricter operational design target for Tool Gateway credentials. The legacy 60-minute reference is superseded for dispatch credentials. | Security Architecture approval and Credential Broker tests. |
| Approval Tier 3 ceiling | Tier 3 is `<= USD 10,000`; it is not unbounded. Amounts above this threshold require a separately approved exception policy. | IAM/Business approval and policy tests. |
| Automated approval wording | No AI agent, planner, evaluator or service account can approve its own action. “Automated tier-1 action” means automated dispatch only after an authenticated human approval where policy requires it. | Approval policy tests and audit evidence. |
| API availability and latency | `NFR-AVL-001 >=99.9%` and `NFR-LAT-001 p95 <500ms` are the Initial tier baseline. Weaker PRG values are non-canonical until an ADR approves a tier-specific exception. | SRE/Architecture ADR and measured soak evidence. |
| AI safety mapping | Injection safety is governed by `INV-SEC-002` and the AI safety gate, not `NFR-AI-006`. `NFR-AI-006` governs uplift/Qini. | AI Governance approval and benchmark evidence. |
| AI thresholds | Citation precision baseline is `>=0.95`; unsupported-claim acceptance is `0.00%`. Templates must not invent stricter or looser thresholds without an approved ADR. | AI Governance approval for any change. |
| DR cadence | Weekly automated restore validation, monthly ephemeral restore rehearsal, and bi-annual full DR simulation are distinct activities. Each remains planned until executed evidence exists. | SRE/Storage run evidence. |
| Compliance status | “Implemented”, “Tested” and “Evidenced” require the exact artifact defined by the runbook. Otherwise the only valid states are Designed, Pending, Blocked, Unknown or Not Applicable. | Control artifact and owner review. |

## Source-level security implementation boundaries

The following are documented implementation blockers, not documentation-only fixes:

1. Tenant lifecycle and context issuance require a verified principal and operation authorization.
2. Privileged system state must be opaque, provenance-verified and strictly boolean.
3. Execution contexts require expiry, revocation/versioning and boundary revalidation.
4. Tenant aggregates must not expose mutable authorization/lifecycle state across caller boundaries.
5. Provisioning requires atomic create-if-absent semantics and duplicate-ID rejection.

Affected source paths are `packages/backend/src/revpilot/modules/tenancy/service.py`, `domain/models.py`, `adapters/in_memory_repository.py`, `ports/policy.py`, and `shared/context.py`. They remain implementation pending and are production blockers.

## Historical-report rule

Historical reports must display their as-of date, scope and successor document. A historical claim about Git cleanliness, test execution, rail status or release readiness must never be treated as current evidence without independent verification.
