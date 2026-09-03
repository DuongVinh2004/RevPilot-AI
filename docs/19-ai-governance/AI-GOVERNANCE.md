# AI Governance Contract

Status: Proposed v0.1 — E02 specification output

## Artifact governance

All prompts, graphs, tools, model routes, datasets, indexes, evaluators and model artifacts are immutable versioned artifacts with owner, source digest, intended capability, tenant eligibility, data classification, evaluation report and release state. A production-eligible artifact requires an approved release record; Proposed ADRs do not constitute production authorization.

## Controls

Provider use follows tenant retention/residency eligibility and ADR-0011. Prompts/tool outputs/external content are tainted untrusted inputs. Registered schema validation, output allowlists, capability limits, budget controls, evidence requirements and redaction apply before use. No artifact may weaken tenant, authorization, audit or action controls. Model training/prompt logs do not collect secrets or raw chain-of-thought.

## Release and incident rules

`DRAFT -> EVALUATED -> APPROVED -> ACTIVE -> RETIRED` is controlled by the release process. Gate failure, provenance gap, safety incident, budget breach or provider-term violation blocks promotion and can retire an artifact; existing decisions retain references. Audit artifact changes, release decision, evaluator IDs and rollback selection. Required metrics include schema-valid result rate, unsupported claim rate, policy violations, cost, latency and declared quality gates.

## Traceability

`INV-AI-002`, `INV-SEC-001..002`, `INV-COST-001`, `NFR-AI-001`, `NFR-PRV-001`; ADR-0009..0011.
