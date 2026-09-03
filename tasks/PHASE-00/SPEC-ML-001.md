# SPEC-ML-001 — Define ML system contract

TASK ID: SPEC-ML-001  
TITLE: Define ML system contract  
TYPE: SPECIFICATION  
STATUS: PASS  
EPIC: SPEC-P00-E02  
COMPLEXITY: M  
REASONING_LOAD: HIGH  
READINESS SCORE: 20/20 — model families and gates are bounded.  
NEW_ARCHITECTURAL_DECISIONS_ALLOWED: 0  
PARALLEL_SAFE: YES — disjoint canonical output.  
DEPENDS_ON: SPEC-FND-016  
UNLOCKS: SPEC-P00-E02

OBJECTIVE: Define versioned ML artifact, evaluation and serving rules.  
WHY THIS EXISTS: Prevent leakage and conflated predictive claims.  
CANONICAL OUTPUT: `docs/08-ml-platform/ML-SYSTEM-SPEC.md`.  
READ_SET: NFR baseline, invariants, ADR-0011.  
WRITE_SET: `docs/08-ml-platform/ML-SYSTEM-SPEC.md`.  
PROHIBITED_WRITE_SET: Every other path.  
SPEC REFERENCES: `INV-DATA-001`, `INV-AI-001..002`, `NFR-AI-005..007`.  
INPUT FACTS: Target/as-of semantics are versioned; training is tenant-isolated by default.  
LOCKED DECISIONS: No implicit model selection or production promotion.  
QUESTIONS TO RESOLVE: Dataset/model artifact, split, metrics, calibration, failure contract.  
QUESTIONS NOT TO REOPEN: Product claims or provider choice.  
REQUIRED CONTENT: Separate anomaly, forecast, churn, uplift and causal families.  
SECURITY: Authorized data references only.  
TENANCY: No cross-tenant training absent governance approval.  
RETRY/FALLBACK: Typed insufficient-data/gate-failed responses.  
FAILURE / CONTRADICTION BEHAVIOR: No decision eligibility on failed gate.  
TRACEABILITY: Link all model gates.  
VERIFICATION: Families, artifact fields, leakage rule and metrics appear.  
BINARY ACCEPTANCE CRITERIA: PASS only if churn/uplift/causal remain distinct.  
EXPECTED REPORT FORMAT: ID/status, output, checks, acceptance, deviations, unlocks.
