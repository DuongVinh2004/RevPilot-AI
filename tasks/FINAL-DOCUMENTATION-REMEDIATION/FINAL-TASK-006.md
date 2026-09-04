# FINAL-TASK-006 — Align context and evidence schema contracts

1. Task ID: `FINAL-TASK-006`
2. Parent Finding ID: `FINAL-FINDING-008`, `FINAL-FINDING-009`
3. Source report: Both reports
4. Objective: Make system tenant context and evidence supersession fields type-consistent.
5. Single expected outcome: Published contracts can represent system context and evaluate supersession without an undeclared field.
6. Exact file: `docs/06-agent-platform/EVIDENCE-PROVENANCE-SPEC.md`
7. Exact section: `§2 EvidenceRecord` and `§4 temporal validity`
8. Scope: Select a discriminated `is_system`/nullable context model and reconcile `superseded_at` versus `superseded_by_ref` across the two specs.
9. Non-goals: Do not weaken tenant isolation, add a runtime bypass, or claim implementation exists.
10. Preconditions: Tenancy and Evidence owners agree on canonical field names.
11. Atomic steps: compare schemas; record decision; update both contract snippets and predicates; define negative fixtures.
12. Acceptance criteria: Every field used by a predicate is declared; null/system cases are explicit; normal tenant operations reject null context.
13. Validation: Schema lint plus review of tenant/supersession test cases.
14. Evidence output: Contract diff and fixture list.
15. Owner: Tenancy Architect + Evidence Architecture
16. Estimated size: 90 minutes
17. Dependencies: None
18. Blocks: Tenant/evidence validation readiness
19. Risk: Changing a schema field can affect downstream task packets; add an ID-preserving mapping note.
20. Recovery note: Revert the contract patch only through owner review; keep old names in a supersession note.
21. Status: COMPLETED
