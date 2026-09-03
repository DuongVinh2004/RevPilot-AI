# SPEC-REL-001 — Define AI release process

TASK ID: SPEC-REL-001  
TITLE: Define AI release process  
TYPE: SPECIFICATION  
STATUS: PASS  
EPIC: SPEC-P00-E02  
COMPLEXITY: S  
REASONING_LOAD: MEDIUM  
READINESS SCORE: 20/20 — release states and gates are explicit.  
NEW_ARCHITECTURAL_DECISIONS_ALLOWED: 0  
PARALLEL_SAFE: YES — disjoint canonical output.  
DEPENDS_ON: SPEC-FND-016, SPEC-AIG-001, SPEC-EVL-001  
UNLOCKS: SPEC-P00-E02

OBJECTIVE: Define activation, rollback and retire procedure for AI artifacts.  
WHY THIS EXISTS: Prevent implicit unsafe promotion.  
CANONICAL OUTPUT: `docs/20-evaluation/MODEL-RELEASE-PROCESS.md`.  
READ_SET: AI governance, evaluation framework, NFRs.  
WRITE_SET: `docs/20-evaluation/MODEL-RELEASE-PROCESS.md`.  
PROHIBITED_WRITE_SET: Every other path.  
SPEC REFERENCES: `INV-AI-002`, `NFR-AI-001..007`, `NFR-COST-001`.  
INPUT FACTS: Approved immutable artifact and rollback are required.  
LOCKED DECISIONS: Release grants no action authority.  
QUESTIONS TO RESOLVE: Record/states/gates/monitor/rollback.  
QUESTIONS NOT TO REOPEN: NFR gate thresholds.  
REQUIRED CONTENT: Authorized transition and failure/retire behavior.  
SECURITY: Audit and provider eligibility enforced.  
TENANCY: Activation scope is eligibility constrained.  
RETRY/FALLBACK: Gate failure blocks activation.  
FAILURE / CONTRADICTION BEHAVIOR: Suspend/retire, preserve decision history.  
TRACEABILITY: Link each release gate to EvalRun.  
VERIFICATION: States/gates/rollback sections exist.  
BINARY ACCEPTANCE CRITERIA: PASS only if an incomplete manifest cannot activate.  
EXPECTED REPORT FORMAT: ID/status, output, checks, acceptance, deviations, unlocks.
