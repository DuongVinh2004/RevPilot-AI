# SPEC-FND-002 — Define system and trust boundaries

TASK_ID: SPEC-FND-002  
TITLE: Define system and trust boundaries  
OBJECTIVE: The first execution section states the single task-specific outcome.  
WHY THIS EXISTS: The first objective section states the task-specific Rail 0 ambiguity or risk removed by this task.  
CANONICAL OUTPUT: The first boundary section declares the exact repository-relative output path or paths.  
READ_SET: The first boundary section declares the exact permitted input artifacts.  
WRITE_SET: The first boundary section declares the exact permitted create/modify artifacts.  
PROHIBITED_WRITE_SET: Everything outside the declared write set is prohibited unless explicitly enumerated.  
SPEC REFERENCES: The first boundary or decision section cites the controlling canonical artifacts and IDs.  
INPUT FACTS: The decision/required-content sections state the task-specific facts; undocumented assumptions are not facts.  
DECISIONS ALREADY LOCKED: Existing higher-precedence decisions cited by this task remain closed.  
QUESTIONS THIS TASK MUST RESOLVE: Only the objective and acceptance questions assigned by this packet.  
QUESTIONS THIS TASK MUST NOT REOPEN: Product scope, safety invariants, and higher-precedence decisions outside the allowed decision budget.  
REQUIRED CONTENT: The named required-content section is normative and must be complete.  
SECURITY CONSIDERATIONS: Preserve deny-by-default authorization, evidence integrity, auditability, secret isolation, and the Tool Gateway side-effect boundary where applicable.  
TENANCY CONSIDERATIONS: Preserve explicit tenant ownership and isolation; a cross-tenant ambiguity is a blocking contradiction.  
FAILURE / CONTRADICTION HANDLING: Return BLOCKED with exact references; never silently harmonize conflicting canonical statements.  
TRACEABILITY REQUIREMENTS: Cite the output path, controlling IDs, dependencies, acceptance evidence, and every deviation.  
VERIFICATION: Run the exact checks named in the verification section and record their results.  
BINARY ACCEPTANCE CRITERIA: The verification section is normative; every listed condition must pass, otherwise the task is not PASS.  
EXPECTED REPORT FORMAT: Task ID/status, changed paths, verification command/result, binary acceptance results, contradictions/deviations, and unlocked IDs.  
 TYPE: SPECIFICATION  
TYPE: SPECIFICATION  
STATUS: PASS  
PHASE/EPIC: PHASE-00 / SPEC-P00-E01  
COMPLEXITY: M  
REASONING_LOAD: MEDIUM  
READINESS_SCORE: 20/20 — every readiness dimension is 2/2  
NEW_ARCHITECTURAL_DECISIONS_ALLOWED: 0  
DEPENDS_ON: SPEC-FND-001  
UNLOCKS: SPEC-FND-005, SPEC-FND-008, SPEC-ADR-003, SPEC-ADR-005, SPEC-ADR-009, SPEC-ADR-010  
PARALLEL_SAFE: YES — with SPEC-FND-003 after SPEC-FND-001.

## Objective and why this exists

Create one ownership and trust-boundary specification covering what RevPilot owns, what external systems own, and which component enforces each crossing.

## Canonical output and change boundary

CANONICAL OUTPUT / WRITE_SET / CREATE: `docs/04-system-architecture/SYSTEM-BOUNDARIES.md`.  
READ_SET: `docs/00-executive/GLOSSARY.md`, `docs/01-product/PRD.md`, `docs/04-system-architecture/SYSTEM-ARCHITECTURE.md`, `docs/15-security/THREAT-MODEL.md`.  
PROHIBITED_WRITE_SET: every other file.  
SPEC REFERENCES: `docs/04-system-architecture/SYSTEM-ARCHITECTURE.md#plane-boundaries`, `docs/15-security/THREAT-MODEL.md#primary-trust-boundaries`.

## Decision envelope

INPUT FACTS: RevPilot consumes but does not become system of record for CRM/ERP/WMS/payment/email/IdP/LLM-provider data; all writes use Tool Gateway.  
DECISIONS ALREADY LOCKED: five planes, external-system ownership, no agent credentials, no MVP real side effects.  
QUESTIONS TO RESOLVE: ownership, authoritative data, transferred data/authority, enforcing control, fail behavior, and unresolved provider obligations per boundary.  
MUST NOT REOPEN: whether Tool Gateway is mandatory or whether agents can call providers directly.

## Required content and controls

Cover browser/API, IdP, model provider, CRM, ERP, WMS, payment, email, object storage, relational/vector/search stores, Temporal, agent runtime, connectors, Control Plane, and build/model supply chain. Include responsibility and trust-boundary matrices plus a diagram. Tenant, credentials, PII, approval, audit, and failure behavior must be explicit. Unknown cloud/provider details remain `UNKNOWN` with owner/revisit trigger.

## Verification and binary acceptance

COMMAND: `rg -n "CRM|ERP|WMS|payment|email|identity provider|LLM provider|Trust boundary|Enforcing control|UNKNOWN" docs/04-system-architecture/SYSTEM-BOUNDARIES.md`. Expected exit 0.  
PASS only if every required system has an owner and non-owner, each authority crossing names an enforcing component and fail behavior, external systems remain authoritative for their records, and no direct agent external call exists.

## Expected report format

Task/status, created file, verification, acceptance results, unresolved boundary owners, deviations, unlocked IDs.
