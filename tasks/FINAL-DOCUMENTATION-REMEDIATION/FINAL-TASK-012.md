# FINAL-TASK-012 — Normalize path text and prospective markers

1. Task ID: `FINAL-TASK-012`
2. Parent Finding ID: `FINAL-FINDING-015`
3. Source report: Both reports plus final audit
4. Objective: Remove literal tab corruption from traceability/evidence paths and distinguish absent future artifacts.
5. Single expected outcome: Every path in the closure matrix and evidence index is readable, resolvable when claimed existing, or explicitly PROSPECTIVE.
6. Exact file: `execution/TRACEABILITY-CLOSURE-MATRIX.md`
7. Exact section: all invariant/NFR table path columns
8. Scope: Replace literal tabs in the affected scoped tables/files, correct `tenancy/ports/policy.py`, and mark nonexistent implementation/test paths prospective.
9. Non-goals: Do not create the future source/test modules or alter queue admission.
10. Preconditions: FINAL-TASK-004 has established complete NFR rows.
11. Atomic steps: byte-scan; patch scoped path text; validate actual paths; add markers; re-run link/path scan.
12. Acceptance criteria: Zero literal tabs in scoped tables; actual policy path resolves; absent paths are labeled PROSPECTIVE; rendered Markdown links remain valid.
13. Validation: Byte scan, path existence scan, and fenced-code-aware Markdown link scan.
14. Evidence output: Path inventory with EXISTS/PROSPECTIVE classification.
15. Owner: Documentation Engineer + Platform Architect
16. Estimated size: 60 minutes
17. Dependencies: FINAL-TASK-004
18. Blocks: Traceability evidence readiness
19. Risk: Mechanical replacement can alter intended code examples; review every changed line.
20. Recovery note: Use a narrow patch and preserve all unrelated tabs outside the approved scope.
21. Status: COMPLETED
