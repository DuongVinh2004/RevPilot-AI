# FINAL-TASK-010 — Extend executor authority to ADR-0012

1. Task ID: `FINAL-TASK-010`
2. Parent Finding ID: `FINAL-FINDING-018`
3. Source report: Both reports plus final audit
4. Objective: Ensure the executor rulebook explicitly inherits the action-approval autonomy boundary.
5. Single expected outcome: The rulebook lists ADR-0012 and prohibits self-approval or unauthorized writes.
6. Exact file: `execution/FLASH-EXECUTOR-RULEBOOK.md`
7. Exact section: authority/subordination header
8. Scope: Add ADR-0012 to the precedence list and add a concise action-boundary clause.
9. Non-goals: Do not change queue admission logic or provider selection.
10. Preconditions: FINAL-TASK-005 has an approved action policy.
11. Atomic steps: inspect current authority statement; add ADR-0012; add no-self-approval/no-unauthorized-write wording; review against queue rules.
12. Acceptance criteria: All 12 ADRs are referenced or explicitly scoped; ADR-0012 is visible in executor authority; no queue mutation permission is implied.
13. Validation: ADR reference inventory and security review.
14. Evidence output: Rulebook diff and authority checklist.
15. Owner: Planning/Architecture + Security
16. Estimated size: 30 minutes
17. Dependencies: FINAL-TASK-005
18. Blocks: Executor governance readiness
19. Risk: Overbroad rulebook text could create authority ambiguity; keep it subordinate to higher policy.
20. Recovery note: Revert the one-file patch if reviewers reject the wording; preserve existing queue status.
21. Status: COMPLETED
