# Final Documentation Remediation

Status: PROPOSED — not admitted to `execution/EXECUTOR-QUEUE.md`
Date: 2026-09-04
Owner: Final Documentation Quality Adjudicator / Principal Architect

This directory contains the normalized remediation plan produced after comparing Report A and Report B against the current repository. Existing `TASK-DA-*`, phase, and rail task IDs are preserved; these new IDs are a separate proposed remediation set.

## Task index

| Task | Outcome | Parent findings | Size | Depends on | Status |
|---|---|---|---:|---|---|
| FINAL-TASK-001 | Replace evidence placeholder hash with reproducible digest | FINAL-FINDING-001 | 30 min | None | COMPLETED |
| FINAL-TASK-002 | Reconcile evidence package status and execution prerequisites | FINAL-FINDING-002 | 60 min | None | COMPLETED |
| FINAL-TASK-003 | Close PRD-to-SRS ownership and RCA mapping gap | FINAL-FINDING-003, 010 | 90 min | None | COMPLETED |
| FINAL-TASK-004 | Add seven omitted NFR rows and correct closure summary | FINAL-FINDING-004 | 60 min | None | COMPLETED |
| FINAL-TASK-005 | Reconcile credential TTL and approval-tier semantics | FINAL-FINDING-005, 006, 007 | 90 min | None | COMPLETED |
| FINAL-TASK-006 | Align tenant/system context and EvidenceRecord supersession schema | FINAL-FINDING-008, 009 | 90 min | None | COMPLETED |
| FINAL-TASK-007 | Make reconciliation, queue, and historical pointers unambiguous | FINAL-FINDING-013, 014 | 60 min | None | COMPLETED |
| FINAL-TASK-008 | Publish one canonical benchmark manifest | FINAL-FINDING-011, 016 | 90 min | FINAL-TASK-003 | COMPLETED |
| FINAL-TASK-009 | Reconcile SRE gate count, DR cadence, and test IDs | FINAL-FINDING-017 | 90 min | FINAL-TASK-002 | COMPLETED |
| FINAL-TASK-010 | Add ADR-0012 to executor authority and action boundary | FINAL-FINDING-018 | 30 min | FINAL-TASK-005 | COMPLETED |
| FINAL-TASK-011 | Establish repository-local governance and metadata controls | FINAL-FINDING-012, 019, 020 | 90 min | FINAL-TASK-007 | COMPLETED |
| FINAL-TASK-012 | Normalize tabs and mark prospective traceability paths | FINAL-FINDING-015 | 60 min | FINAL-TASK-004 | COMPLETED |
| FINAL-TASK-013 | Resolve scoped structure, accessibility, and domain-quality items | FINAL-FINDING-021, 022, 023, 024 | 90 min | FINAL-TASK-008 | COMPLETED |
| FINAL-TASK-014 | Run final non-mutating audit validation and produce evidence index | All open findings | 60 min | FINAL-TASK-001..013 | COMPLETED |

## Proposed DAG

`FINAL-TASK-003 -> FINAL-TASK-008 -> FINAL-TASK-013 -> FINAL-TASK-014`

`FINAL-TASK-004 -> FINAL-TASK-012 -> FINAL-TASK-014`

`FINAL-TASK-005 -> FINAL-TASK-010 -> FINAL-TASK-014`

`FINAL-TASK-002 -> FINAL-TASK-009 -> FINAL-TASK-014`

`FINAL-TASK-007 -> FINAL-TASK-011 -> FINAL-TASK-014`

`FINAL-TASK-001 -> FINAL-TASK-014`

The proposed graph is acyclic. These tasks must not be admitted to the executor queue until individually reviewed, scored, and reconciled with the authoritative implementation graph.
