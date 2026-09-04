# FINAL-TASK-013 — Close scoped structure and quality gaps

1. Task ID: `FINAL-TASK-013`
2. Parent Finding ID: `FINAL-FINDING-021`, `FINAL-FINDING-022`, `FINAL-FINDING-023`, `FINAL-FINDING-024`
3. Source report: Both reports
4. Objective: Resolve only reproducible structural, accessibility, domain-clarity, and formatting findings.
5. Single expected outcome: The scoped documents have explicit quality rules and no unresolved item-level ambiguity.
6. Exact file: `docs/28-frontend/FRONTEND-SPEC.md`
7. Exact section: add bounded accessibility and acceptance section; record companion findings in the final audit log.
8. Scope: Add WCAG 2.2 AA criteria, validate SQL capability names/templates, review phase scope/heading numbering, validate metric/cardinality concerns, and fix low-risk wording/placeholders.
9. Non-goals: Do not rename valid `SEC-*` namespace IDs, claim accessibility conformance without test evidence, or redesign subsystem architecture.
10. Preconditions: FINAL-TASK-008 benchmark terminology is canonical.
11. Atomic steps: create defect list with line anchors; patch only confirmed issues; add acceptance/test references; mark uncertain metric item pending validation.
12. Acceptance criteria: Accessibility criteria are explicit; every changed structural item has an owner and validation; no unsupported finding is presented as confirmed.
13. Validation: Heading/ID/terminology scan and manual review.
14. Evidence output: Scoped quality checklist and updated references.
15. Owner: Frontend Architect + Domain Document Owners + Documentation Engineer
16. Estimated size: 90 minutes
17. Dependencies: FINAL-TASK-008
18. Blocks: FINAL-TASK-014 only; does not unblock production by itself
19. Risk: Broad cleanup could expand scope; keep the patch itemized and bounded.
20. Recovery note: Revert individual scoped edits, not entire document families; preserve existing decisions.
21. Status: COMPLETED
