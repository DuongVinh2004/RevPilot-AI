# SPEC-DEC-001 — Define decision intelligence contract

TASK ID: SPEC-DEC-001  
TITLE: Define decision intelligence contract  
TYPE: SPECIFICATION  
STATUS: PASS  
EPIC: SPEC-P00-E02  
COMPLEXITY: M  
REASONING_LOAD: HIGH  
READINESS SCORE: 20/20 — deterministic ranking boundary is fixed.  
NEW_ARCHITECTURAL_DECISIONS_ALLOWED: 0  
PARALLEL_SAFE: YES — disjoint canonical output.  
DEPENDS_ON: SPEC-FND-016, SPEC-ML-001, SPEC-CAU-001  
UNLOCKS: SPEC-P00-E02

OBJECTIVE: Define candidate eligibility, constraint and utility decision contract.  
WHY THIS EXISTS: Separate quantitative decision from generated explanation.  
CANONICAL OUTPUT: `docs/11-decision-intelligence/DECISION-ENGINE-SPEC.md`.  
READ_SET: ML/causal docs, invariants, policy/action boundaries.  
WRITE_SET: `docs/11-decision-intelligence/DECISION-ENGINE-SPEC.md`.  
PROHIBITED_WRITE_SET: Every other path.  
SPEC REFERENCES: `INV-AI-001`, `INV-ACT-003..004`, `NFR-AI-005..007`.  
INPUT FACTS: Policy eligibility and exact digest precede action.  
LOCKED DECISIONS: Generative explanation cannot modify authority/ranking.  
QUESTIONS TO RESOLVE: Input/output, constraints, fallback/state lifecycle.  
QUESTIONS NOT TO REOPEN: Approval or action ownership.  
REQUIRED CONTENT: Objective decomposition and no-decision behavior.  
SECURITY: Decisions grant no action authority.  
TENANCY: Candidate/evidence/artifact scopes must match trusted tenant.  
RETRY/FALLBACK: `NO_DECISION|REQUIRES_REVIEW` on insufficiency.  
FAILURE / CONTRADICTION BEHAVIOR: Reject mismatched digest/context.  
TRACEABILITY: Link to policy/approval/action tasks.  
VERIFICATION: Eligibility, constraints and terminal states exist.  
BINARY ACCEPTANCE CRITERIA: PASS only if hard constraints precede ranking.  
EXPECTED REPORT FORMAT: ID/status, output, checks, acceptance, deviations, unlocks.
