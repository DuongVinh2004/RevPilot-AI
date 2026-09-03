# SPEC-EVL-001 — Define AI evaluation framework

TASK ID: SPEC-EVL-001  
TITLE: Define AI evaluation framework  
TYPE: SPECIFICATION  
STATUS: PASS  
EPIC: SPEC-P00-E02  
COMPLEXITY: S  
REASONING_LOAD: HIGH  
READINESS SCORE: 20/20 — gates are exact.  
NEW_ARCHITECTURAL_DECISIONS_ALLOWED: 0  
PARALLEL_SAFE: YES — disjoint canonical output.  
DEPENDS_ON: SPEC-FND-016, SPEC-ML-001, SPEC-RAG-001, SPEC-CAU-001  
UNLOCKS: SPEC-P00-E02

OBJECTIVE: Define reproducible evaluation record and suite rules.  
WHY THIS EXISTS: Distinguish measured evidence from targets.  
CANONICAL OUTPUT: `docs/20-evaluation/EVALUATION-FRAMEWORK.md`.  
READ_SET: NFR baseline, intelligence docs, invariants.  
WRITE_SET: `docs/20-evaluation/EVALUATION-FRAMEWORK.md`.  
PROHIBITED_WRITE_SET: Every other path.  
SPEC REFERENCES: `NFR-AI-001..007`, `INV-DATA-001`, `INV-AI-001..002`.  
INPUT FACTS: Eval artifacts require immutable versions.  
LOCKED DECISIONS: Target is not a measured result.  
QUESTIONS TO RESOLVE: EvalRun schema, suite/gate/comparability rules.  
QUESTIONS NOT TO REOPEN: NFR thresholds.  
REQUIRED CONTENT: RAG/SQL/RCA/ML/uplift/causal/agent suite.  
SECURITY: Eval data follows governance.  
TENANCY: No unapproved mixed datasets.  
RETRY/FALLBACK: Inconclusive is not pass.  
FAILURE / CONTRADICTION BEHAVIOR: Failed suite blocks declared use.  
TRACEABILITY: NFR-to-eval mapping.  
VERIFICATION: EvalRun and suite sections exist.  
BINARY ACCEPTANCE CRITERIA: PASS only if a comparison requires matching versions/split.  
EXPECTED REPORT FORMAT: ID/status, output, checks, acceptance, deviations, unlocks.
