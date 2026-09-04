# FINAL-TASK-005 — Reconcile TTL and approval-tier semantics

1. Task ID: `FINAL-TASK-005`
2. Parent Finding ID: `FINAL-FINDING-005`, `FINAL-FINDING-006`, `FINAL-FINDING-007`
3. Source report: Both reports
4. Objective: Publish one owner-approved security/action policy for broker TTL and approval tiers.
5. Single expected outcome: Credential lifetime, Tier 3 ceiling, and Tier 1 approval wording are unambiguous and consistent.
6. Exact file: `docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md`
7. Exact section: `§4.2`, per-action spend ceiling and approval terminology
8. Scope: Reconcile against IAM-SPEC and ADR-0012; update mirrored statements, NFR references, and denial criteria.
9. Non-goals: Do not choose a value without Security/FinOps sign-off or implement the broker.
10. Preconditions: Security Architect and FinOps Lead approve TTL and Tier 3 policy.
11. Atomic steps: enumerate conflicting statements; decide policy; update primary and mirror text; add exact negative acceptance wording.
12. Acceptance criteria: One TTL is present across specs; Tier 3 is either bounded or explicitly escalated; Tier 1 cannot imply agent self-approval.
13. Validation: Cross-document search and policy-review sign-off.
14. Evidence output: Decision record, diff, and boundary-test requirements.
15. Owner: Security Architect + FinOps Lead
16. Estimated size: 90 minutes
17. Dependencies: None
18. Blocks: FINAL-TASK-010 and security/action acceptance
19. Risk: A lower TTL or ceiling may affect product workflows; document the trade-off.
20. Recovery note: Preserve the prior wording in review history; do not delete the conflicting source without approval.
21. Status: COMPLETED
