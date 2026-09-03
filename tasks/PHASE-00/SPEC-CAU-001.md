# SPEC-CAU-001 — Define causal inference contract

TASK ID: SPEC-CAU-001  
TITLE: Define causal inference contract  
TYPE: SPECIFICATION  
STATUS: PASS  
EPIC: SPEC-P00-E02  
COMPLEXITY: M  
REASONING_LOAD: HIGH  
READINESS SCORE: 20/20 — output defines fixed claim conditions.  
NEW_ARCHITECTURAL_DECISIONS_ALLOWED: 0  
PARALLEL_SAFE: YES — disjoint canonical output.  
DEPENDS_ON: SPEC-FND-016  
UNLOCKS: SPEC-P00-E02

OBJECTIVE: Define causal study/estimate semantics and gates.  
WHY THIS EXISTS: Prevent causal claims from correlations or LLM output.  
CANONICAL OUTPUT: `docs/10-causal-ai/CAUSAL-INFERENCE-SPEC.md`.  
READ_SET: ML system, invariants, NFR AI baseline.  
WRITE_SET: `docs/10-causal-ai/CAUSAL-INFERENCE-SPEC.md`.  
PROHIBITED_WRITE_SET: Every other path.  
SPEC REFERENCES: `INV-AI-001`, `INV-DATA-001`, `NFR-AI-007`.  
INPUT FACTS: Causal is conditional on declared identification.  
LOCKED DECISIONS: Insufficient evidence is valid terminal outcome.  
QUESTIONS TO RESOLVE: Study schema, lifecycle, overlap/sensitivity/eval rules.  
QUESTIONS NOT TO REOPEN: Causal product objective.  
REQUIRED CONTENT: Treatment/outcome/confounder/estimand/uncertainty fields.  
SECURITY: Authorized versioned inputs only.  
TENANCY: Study data is tenant scoped.  
RETRY/FALLBACK: No estimator substitution; label association/insufficient.  
FAILURE / CONTRADICTION BEHAVIOR: Gate failure blocks decision use.  
TRACEABILITY: Link causal test/evaluation IDs.  
VERIFICATION: Required study fields and state transitions exist.  
BINARY ACCEPTANCE CRITERIA: PASS only if causal output requires validation evidence.  
EXPECTED REPORT FORMAT: ID/status, output, checks, acceptance, deviations, unlocks.
