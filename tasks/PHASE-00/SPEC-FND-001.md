# SPEC-FND-001 — Define canonical terminology

TASK_ID: SPEC-FND-001  
TITLE: Define canonical terminology  
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
DEPENDS_ON: NONE  
UNLOCKS: SPEC-FND-002, SPEC-FND-003, SPEC-FND-004, SPEC-FND-008, SPEC-ADR-001, SPEC-ADR-002, SPEC-ADR-003, SPEC-ADR-004, SPEC-ADR-005, SPEC-ADR-006, SPEC-ADR-007, SPEC-ADR-008, SPEC-ADR-009, SPEC-ADR-010, SPEC-ADR-011  
PARALLEL_SAFE: YES — with SPEC-FND-007; write sets are disjoint.

## Objective and why this exists

Create one authoritative glossary so specifications cannot silently assign different meanings to identity, investigation, evidence, decision, workflow, model, and version concepts.

## Canonical output and change boundary

CANONICAL OUTPUT / WRITE_SET / CREATE: `docs/00-executive/GLOSSARY.md`.  
READ_SET: `docs/00-executive/EXECUTIVE-VISION.md`, `docs/01-product/PRD.md`, `docs/02-domain/BUSINESS-DOMAIN-MODEL.md`, `docs/03-requirements/SRS.md`, `docs/04-system-architecture/SYSTEM-ARCHITECTURE.md`, `execution/MICRO-TASK-RAIL-SYSTEM.md`.  
PROHIBITED_WRITE_SET: every file except the canonical output.  
SPEC REFERENCES: `docs/02-domain/BUSINESS-DOMAIN-MODEL.md#core-aggregates-and-invariants`, `docs/04-system-architecture/SYSTEM-ARCHITECTURE.md#plane-boundaries`.

## Decision envelope

INPUT FACTS: five-plane architecture; Temporal owns durable business workflow; agent output is untrusted; Tool Gateway is the side-effect boundary.  
DECISIONS ALREADY LOCKED: distinguish Tenant/Organization, Actor/Principal/User/Agent, Investigation/Run, Decision/Recommendation, Action/Attempt/Intervention, Workflow/Agent graph, and every version artifact.  
QUESTIONS THIS TASK MUST RESOLVE: normative definition, ownership, lifecycle distinction, and prohibited synonyms for each foundational term.  
QUESTIONS THIS TASK MUST NOT REOPEN: technology selection, tenant tiers, side-effect path, or product lifecycle.

## Required content and controls

Define at least Tenant, Organization, Actor, Principal, User, Service Principal, Agent, Delegated Agent Identity, Investigation, Investigation Run, Hypothesis, Evidence, Evidence Bundle, Decision, Recommendation, Approval, Action, Action Attempt, Intervention, Outcome, Connector, Tool, Policy, Business Workflow, Agent Graph, Model/Prompt/Agent/Dataset/RAG Index Version. Include “not the same as” distinctions and naming rules. Security/tenancy terms must preserve deny-by-default and tenant ownership. Contradictions are recorded and returned BLOCKED; they are not harmonized by silently changing another file. Trace every term to owning domain/plane.

## Verification and binary acceptance

COMMAND: `rg -n "^### (Tenant|Organization|Actor|Principal|Investigation|Evidence|Decision|Recommendation|Action|Connector|Tool|Policy|Business Workflow|Agent Graph|Model Version)" docs/00-executive/GLOSSARY.md`. Expected exit code 0.  
PASS only if the output exists, contains every required concept, assigns one normative definition and owner, distinguishes listed near-synonyms, contains no technology decision, and modifies no prohibited file.

## Expected report format

Report task ID/status, created file, verification command/exit code, each acceptance result, contradictions/deviations, and next unlocked IDs. No implementation code.
