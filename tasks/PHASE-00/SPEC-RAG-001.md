# SPEC-RAG-001 — Define governed retrieval contract

TASK ID: SPEC-RAG-001  
TITLE: Define governed retrieval contract  
TYPE: SPECIFICATION  
STATUS: PASS  
EPIC: SPEC-P00-E02  
COMPLEXITY: M  
REASONING_LOAD: HIGH  
READINESS SCORE: 20/20 — ADR baseline and output are exact.  
NEW_ARCHITECTURAL_DECISIONS_ALLOWED: 0  
PARALLEL_SAFE: YES — disjoint canonical output.  
DEPENDS_ON: SPEC-FND-016  
UNLOCKS: SPEC-P00-E02

OBJECTIVE: Define tenant-safe hybrid retrieval and citation lifecycle.  
WHY THIS EXISTS: Prevent unauthorized/stale context from supporting decisions.  
CANONICAL OUTPUT: `docs/09-rag/RAG-SPEC.md`.  
READ_SET: ADR-0004..0006, evidence/tenant invariants.  
WRITE_SET: `docs/09-rag/RAG-SPEC.md`.  
PROHIBITED_WRITE_SET: Every other path.  
SPEC REFERENCES: `INV-EVD-001..002`, `INV-TEN-001..002`, `NFR-AI-003`.  
INPUT FACTS: PostgreSQL FTS + pgvector is baseline.  
LOCKED DECISIONS: No Qdrant/OpenSearch; Evidence owns cited record.  
QUESTIONS TO RESOLVE: Entity, filters, fusion, deletion/reindex and eval contract.  
QUESTIONS NOT TO REOPEN: Retrieval ADR.  
REQUIRED CONTENT: Required retrieval pipeline and negatives.  
SECURITY: Authorization filters and revalidation are mandatory.  
TENANCY: Trusted scope applied in every store/query.  
RETRY/FALLBACK: No authorized evidence is a typed result.  
FAILURE / CONTRADICTION BEHAVIOR: Quarantine/incomplete state, never fabricate.  
TRACEABILITY: Link citation and isolation tests.  
VERIFICATION: Entity/pipeline/evaluation sections exist.  
BINARY ACCEPTANCE CRITERIA: PASS only if superseded content cannot support a recommendation.  
EXPECTED REPORT FORMAT: ID/status, output, checks, acceptance, deviations, unlocks.
