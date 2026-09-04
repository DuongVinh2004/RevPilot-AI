# FINAL-TASK-004 — Restore omitted NFR closure rows

1. Task ID: `FINAL-TASK-004`
2. Parent Finding ID: `FINAL-FINDING-004`
3. Source report: Both reports
4. Objective: Align the closure matrix with all 28 NFRs in `NFR-BASELINE.md`.
5. Single expected outcome: The closure matrix contains explicit rows for AVL, LAT, THR, and REC NFRs and reports the correct denominator.
6. Exact file: `execution/TRACEABILITY-CLOSURE-MATRIX.md`
7. Exact section: `§3 Non-Functional Requirement Traceability Matrix` and `§4 Traceability Summary`
8. Scope: Add seven NFR rows with canonical spec, ADR, prospective implementation/test markers, evidence, owner, status, and gap.
9. Non-goals: Do not turn design targets into measurements or change the NFR baseline.
10. Preconditions: `docs/03-requirements/NFR-BASELINE.md` is the source list.
11. Atomic steps: copy canonical descriptions; map artifacts; label absent paths PROSPECTIVE; update 21/21 summary to 28/28 after insertion.
12. Acceptance criteria: All 28 NFR IDs appear exactly once as matrix rows; every row has owner and gap status.
13. Validation: Scripted row-ID comparison against NFR-BASELINE and table review.
14. Evidence output: ID comparison output and matrix diff.
15. Owner: Compliance Lead + SRE Lead
16. Estimated size: 60 minutes
17. Dependencies: None
18. Blocks: FINAL-TASK-012 and traceability gate
19. Risk: Incorrect mapping can hide a production gap; retain `[PROSPECTIVE]` and PENDING labels.
20. Recovery note: Restore only the matrix patch under review; do not remove legacy evidence.
21. Status: COMPLETED
