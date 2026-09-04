# RevPilot AI — Repository Agent Safety & Governance Contract

Status: Active  
Owner: Principal Architecture & Safety Officer  
Approver: Duong Vinh (Repository Owner)  
Date: 2026-09-04  
Scope: All autonomous and assisted agents, executors, planners, and subagents operating within this repository.

---

## 1. Core Operating Directives

All agents operating in this repository are strictly governed by the fail-closed principle:
1. **Stop on Uncertainty / Ambiguity**: If a requirement, invariant, path, or condition is contradictory, missing, or ambiguous, stop immediately with status BLOCKED. Never make unauthorized assumptions or guess missing specifications.
2. **Offline Hermetic Execution**: External network connections, socket bindings, or internet telemetry are strictly prohibited. All tests, benchmarks, and scripts execute offline.
3. **Anti-Fabrication Invariant (AC-014)**: Under no circumstances may an agent fabricate, hallucinate, mock, or assume benchmark scores or operational test outputs as measured results. A measured result exists exclusively when recorded by an automated execution run with verifiable machine logs.
4. **Non-Mutating Inspection First**: Read all required files (READ_SET) completely before modifying any file. Never edit files outside an authorized task WRITE_SET.

---

## 2. Authority Hierarchy

All repository activity must strictly obey the precedence order defined in docs/00-executive/SPECIFICATION-PRECEDENCE.md:
1. System/Developer Safety Policies & Directives (Top Authority).
2. docs/00-executive/SPECIFICATION-PRECEDENCE.md and docs/00-executive/DOCUMENTATION-CLOSURE-DECISIONS.md.
3. Accepted Architecture Decision Records (docs/31-adr/ADR-0001 through ADR-0012).
4. Core Architectural Invariants (INV-SEC-*, INV-TEN-*, INV-ACT-*, INV-DATA-*, INV-AUD-*, INV-COST-*, INV-PRV-*, INV-REL-*).
5. Canonical Specifications and Accepted Module Contracts (docs/ Accepted set).
6. Executor Rulebook (execution/FLASH-EXECUTOR-RULEBOOK.md).
7. Canonical Task Definitions (`tasks/`).
8. Source Code and Unit Tests (`packages/`, `tests/`).
9. Historical Reports, Logs, and Point-in-Time Snapshots.

---

## 3. Strict Prohibitions (Non-Negotiable)

- **Zero Agent Self-Approval (INV-ACT-003)**: No AI agent, planner, evaluator, or service account may approve its own actions, grants, or tasks. All tier-1..tier-3 mutations require authenticated human approval digests.
- **Zero Unauthorized External Mutations (INV-ACT-001, AC-008)**: External write operations outside the read-only capability catalog or lacking cryptographically verified human approval tokens are strictly blocked (FAIL_CLOSED).
- **Zero Destructive Git Commands**: Agents are strictly forbidden from running git commit, git push, git checkout, git reset, git rebase, git stash, or modifying git history unless explicitly commanded by the user.
- **Strict Multi-Tenant Isolation (INV-TEN-001, NFR-TEN-001)**: No cross-tenant data, cache entries, vector embeddings, or execution context leaks are permitted. Tenant context must be server-derived and immutable.
- **Immutable Queue Protection**: Agents cannot self-admit, re-order, or promote tasks in execution/EXECUTOR-QUEUE.md without formal governance sign-off.

---

## 4. Documentation & Metadata Governance

1. **Accepted Document Requirements**: Any document marked Accepted must define:
   - Owner Role or Owner: Named domain lead.
   - Approver: Named authority.
   - Version: Explicit version string (e.g. `v1.0`).
   - Date / Last Reviewed Date: Canonical ISO date (`YYYY-MM-DD`).
   - Non-Goals: Explicitly bounded out-of-scope boundaries.
2. **Status Promotion Discipline**: Proposed documents remain `Proposed` until an owner-approved decision records formal acceptance. No automated bulk promotion is allowed.
3. **Historical Immutability**: Historical audit reports, point-in-time closure matrices, and superseded logs remain immutable; updates are applied via explicit supersession links.