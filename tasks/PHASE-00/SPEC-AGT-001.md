# SPEC-AGT-001 — Define multi-agent contracts

TASK ID: SPEC-AGT-001  
TITLE: Define multi-agent contracts  
TYPE: SPECIFICATION  
STATUS: PASS  
EPIC: SPEC-P00-E02  
COMPLEXITY: M  
REASONING_LOAD: HIGH  
READINESS SCORE: 20/20 — role boundary is fixed.  
NEW_ARCHITECTURAL_DECISIONS_ALLOWED: 0  
PARALLEL_SAFE: YES — disjoint canonical output.  
DEPENDS_ON: SPEC-FND-016  
UNLOCKS: SPEC-P00-E02

OBJECTIVE: Specify typed logical agent roles and limits.  
WHY THIS EXISTS: Remove free-form multi-agent authority ambiguity.  
CANONICAL OUTPUT: `docs/06-agent-platform/MULTI-AGENT-SPEC.md`.  
READ_SET: ADR-0003/0011, AI architecture, invariants.  
WRITE_SET: `docs/06-agent-platform/MULTI-AGENT-SPEC.md`.  
PROHIBITED_WRITE_SET: Every other path.  
SPEC REFERENCES: `INV-IAM-002`, `INV-SEC-001..002`, `INV-AI-001`.  
INPUT FACTS: Agents are roles, not unrestricted identities.  
LOCKED DECISIONS: Registered capabilities only; no credential/action/approval access.  
QUESTIONS TO RESOLVE: Per-role schema, tools, budgets, retry, escalation, evidence and eval.  
QUESTIONS NOT TO REOPEN: Temporal ownership or provider selection.  
REQUIRED CONTENT: Role matrix and typed terminal states.  
SECURITY: Delegation is tenant/task/time scoped.  
TENANCY: Context is trusted and immutable.  
RETRY/FALLBACK: Read-only bounded retry; otherwise typed terminal state.  
FAILURE / CONTRADICTION BEHAVIOR: Fail closed and report contradiction.  
TRACEABILITY: Link agent controls to invariants/evals.  
VERIFICATION: Required role and denied-capability matrix exists.  
BINARY ACCEPTANCE CRITERIA: PASS only if no role has implicit authority.  
EXPECTED REPORT FORMAT: ID/status, output, checks, acceptance, deviations, unlocks.
