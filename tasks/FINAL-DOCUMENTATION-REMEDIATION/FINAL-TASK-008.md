# FINAL-TASK-008 — Publish a canonical benchmark manifest

1. Task ID: `FINAL-TASK-008`
2. Parent Finding ID: `FINAL-FINDING-011`, `FINAL-FINDING-016`
3. Source report: Both reports
4. Objective: Make benchmark scenario, incident ID, dates, budgets, and quality gates deterministic across evaluation documents.
5. Single expected outcome: All benchmark protocols consume one approved parameter set.
6. Exact file: `docs/20-evaluation/EVALUATION-FRAMEWORK.md`
7. Exact section: benchmark suite definitions and gate references
8. Scope: Select the canonical Midwest/incident identity or an approved alternative; reconcile date windows, $ budget, RCA, unsupported-claim, retrieval, and cost thresholds; fix template placeholder.
9. Non-goals: Do not report scores or execute model evaluations.
10. Preconditions: Product Lead and AI Evaluation Lead approve scenario and thresholds.
11. Atomic steps: inventory parameters; create manifest table; update protocol references; label target versus measured values.
12. Acceptance criteria: No conflicting incident/date/budget/threshold values remain without an explicit scope label; cost field is numeric or approved TBD with owner/trigger.
13. Validation: Cross-document parameter diff.
14. Evidence output: Versioned benchmark manifest and consistency scan.
15. Owner: AI Evaluation Lead + Product Lead
16. Estimated size: 90 minutes
17. Dependencies: FINAL-TASK-003
18. Blocks: AI validation readiness and FINAL-TASK-013
19. Risk: Threshold changes can alter release gates; preserve rationale and approval.
20. Recovery note: Keep historical benchmark documents immutable and add a supersession link.
21. Status: COMPLETED
