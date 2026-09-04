# FINAL-TASK-001 — Re-seal EVD-TEN-001 with a real digest

1. Task ID: `FINAL-TASK-001`
2. Parent Finding ID: `FINAL-FINDING-001`
3. Source report: Both reports
4. Objective: Replace the empty-string SHA-256 placeholder with the digest of the exact evidence manifest/log.
5. Single expected outcome: `EVD-TEN-001` has a reproducible, non-empty SHA-256 seal and an honest status.
6. Exact file: `execution/evidence/EVIDENCE-INDEX.md`
7. Exact section: `§2 Master Evidence Index Table`, row `EVD-TEN-001`
8. Scope: Identify the evidence bytes, compute SHA-256, record command/input identity, and preserve the in-memory/DB split.
9. Non-goals: Do not claim DB RLS validation, alter test code, or delete the old report.
10. Preconditions: Evidence content and local test output are available; target digest is independently recomputable.
11. Atomic steps: inspect evidence file; choose canonical bytes; compute digest; update one row; peer-check the value.
12. Acceptance criteria: Hash differs from the empty-string digest; a second computation matches; status remains partial if DB RLS is pending.
13. Validation: Byte-level hash recomputation and table-row review.
14. Evidence output: Hash command, input path/manifest identifier, output digest, reviewer initials.
15. Owner: Tenancy Lead + SRE Lead
16. Estimated size: 30 minutes
17. Dependencies: None
18. Blocks: Evidence integrity gate and FINAL-TASK-014
19. Risk: Hashing the wrong representation could create false integrity.
20. Recovery note: Restore the prior row from Git if the scoped edit is rejected; do not delete evidence.
21. Status: COMPLETED
