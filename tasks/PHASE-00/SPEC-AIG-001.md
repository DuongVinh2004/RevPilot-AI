# SPEC-AIG-001 — Define AI governance

TASK ID: SPEC-AIG-001  
TITLE: Define AI governance  
TYPE: SPECIFICATION  
STATUS: PASS  
EPIC: SPEC-P00-E02  
COMPLEXITY: S  
REASONING_LOAD: HIGH  
READINESS SCORE: 20/20 — artifact lifecycle is bounded.  
NEW_ARCHITECTURAL_DECISIONS_ALLOWED: 0  
PARALLEL_SAFE: YES — disjoint canonical output.  
DEPENDS_ON: SPEC-FND-016, SPEC-AI-001  
UNLOCKS: SPEC-P00-E02

OBJECTIVE: Define governed version/release lifecycle for AI artifacts.  
WHY THIS EXISTS: Make AI artifacts auditable and revocable.  
CANONICAL OUTPUT: `docs/19-ai-governance/AI-GOVERNANCE.md`.  
READ_SET: AI architecture, ADR-0009..0011, invariants/NFRs.  
WRITE_SET: `docs/19-ai-governance/AI-GOVERNANCE.md`.  
PROHIBITED_WRITE_SET: Every other path.  
SPEC REFERENCES: `INV-AI-002`, `INV-SEC-001..002`, `NFR-AI-001`.  
INPUT FACTS: No secrets/chain-of-thought in artifacts/logs.  
LOCKED DECISIONS: Versioning/release gate cannot grant action authority.  
QUESTIONS TO RESOLVE: Manifest, release state, incident/retire rules.  
QUESTIONS NOT TO REOPEN: Provider/secret baseline.  
REQUIRED CONTENT: Artifact provenance, policy, audit, metrics.  
SECURITY: Taint and redaction controls are mandatory.  
TENANCY: Eligibility and artifacts are tenant scoped.  
RETRY/FALLBACK: Gate failure blocks promotion.  
FAILURE / CONTRADICTION BEHAVIOR: Retire/suspend, preserve history.  
TRACEABILITY: Link release gate and security controls.  
VERIFICATION: Lifecycle and required artifact fields exist.  
BINARY ACCEPTANCE CRITERIA: PASS only if unversioned artifact cannot activate.  
EXPECTED REPORT FORMAT: ID/status, output, checks, acceptance, deviations, unlocks.
