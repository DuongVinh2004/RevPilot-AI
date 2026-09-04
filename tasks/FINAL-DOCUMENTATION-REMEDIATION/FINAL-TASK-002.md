# FINAL-TASK-002 — Reconcile evidence status and execution prerequisites

1. Task ID: `FINAL-TASK-002`
2. Parent Finding ID: `FINAL-FINDING-002`
3. Source report: Both reports
4. Objective: Make the ten-package evidence index distinguish executed, partial, planned, and blocked packages.
5. Single expected outcome: Every evidence row has a status that matches its evidence file and an executable next step.
6. Exact file: `execution/evidence/EVIDENCE-INDEX.md`
7. Exact section: `§1 Governance Policy`, `§2 Master Evidence Index Table`, `§3 Evidence Status Summary`
8. Scope: Reconcile all ten rows and list the nine missing empirical packages without fabricating metrics.
9. Non-goals: Do not run staging/prod tests, provision infrastructure, or mark any package PASS.
10. Preconditions: Current evidence files, DoD Stage D, and production gate are read.
11. Atomic steps: inventory statuses; compare each linked file; classify execution prerequisites; update summary and blockers.
12. Acceptance criteria: Counts reconcile to 10 total and 9 not empirically executed; each missing package has owner, environment, and required output.
13. Validation: Cross-file status scan and manual row-count check.
14. Evidence output: Status reconciliation table and list of execution commands/runbook references.
15. Owner: SRE Lead with domain owners
16. Estimated size: 60 minutes
17. Dependencies: None
18. Blocks: FINAL-TASK-009 and production evidence gate
19. Risk: A status downgrade may expose previously assumed readiness; that is intentional and fail-closed.
20. Recovery note: Revert only the scoped index edit through review; preserve all evidence templates and logs.
21. Status: COMPLETED
