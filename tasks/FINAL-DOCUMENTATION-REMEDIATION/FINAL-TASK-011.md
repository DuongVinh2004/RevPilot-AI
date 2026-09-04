# FINAL-TASK-011 — Establish repository-local governance metadata

1. Task ID: `FINAL-TASK-011`
2. Parent Finding ID: `FINAL-FINDING-012`, `FINAL-FINDING-019`, `FINAL-FINDING-020`
3. Source report: Both reports plus final audit
4. Objective: Provide a repository-local governance contract and make accepted-document metadata auditable.
5. Single expected outcome: Root AGENTS.md exists under owner review and accepted documents have required control metadata without unauthorized status promotion.
6. Exact file: `AGENTS.md`
7. Exact section: new repository-local safety and document-control policy
8. Scope: Add non-weakened repository instructions; inventory accepted docs missing owner/approver/version/review date; create a family-based metadata remediation list.
9. Non-goals: Do not override the supplied safety policy, bulk-promote Proposed documents, or edit every spec in this task.
10. Preconditions: Principal Architect and Safety Officer review the proposed policy.
11. Atomic steps: draft AGENTS; compare against supplied safety policy; run metadata inventory; assign owners and separate follow-up tasks.
12. Acceptance criteria: AGENTS.md preserves fail-closed/destructive-action rules; metadata inventory has zero unowned accepted docs; no status changes are made without approval.
13. Validation: Rule diff and metadata linter output.
14. Evidence output: Reviewed AGENTS.md and accepted-document metadata inventory.
15. Owner: Principal Architect + Safety Officer + Documentation Engineer
16. Estimated size: 90 minutes
17. Dependencies: FINAL-TASK-007
18. Blocks: Governance/documentation closure
19. Risk: Local instructions can accidentally weaken global safety; require explicit safety review.
20. Recovery note: New file is reviewable; if rejected, leave no destructive residue and preserve the inventory output.
21. Status: COMPLETED
