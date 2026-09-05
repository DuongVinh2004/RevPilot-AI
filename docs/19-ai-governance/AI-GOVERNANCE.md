# AI Governance Contract

Status: Accepted v1.0
Approver: Duong Vinh (Repository Owner)
Version: v1.0
Date: 2026-09-04

Owner: AI Governance Lead
## 1. Artifact Governance

All prompts, graphs, tools, model routes, datasets, indexes, evaluators and model artifacts are immutable versioned artifacts with owner, source digest, intended capability, tenant eligibility, data classification, evaluation report and release state. A production-eligible artifact requires an approved release record; Proposed ADRs do not constitute production authorization.

## 2. Security and Safety Controls

Provider use follows tenant retention/residency eligibility and ADR-0011. Prompts/tool outputs/external content are tainted untrusted inputs. Registered schema validation, output allowlists, capability limits, budget controls, evidence requirements and redaction apply before use. No artifact may weaken tenant, authorization, audit or action controls. Model training/prompt logs do not collect secrets or raw chain-of-thought.

## 3. Release and Incident Rules

`DRAFT -> EVALUATED -> APPROVED -> ACTIVE -> RETIRED` is controlled by the release process. Gate failure, provenance gap, safety incident, budget breach or provider-term violation blocks promotion and can retire an artifact; existing decisions retain references. Audit artifact changes, release decision, evaluator IDs and rollback selection. Required metrics include schema-valid result rate, unsupported claim rate, policy violations, cost, latency and declared quality gates.

---

## 4. Phase 05 Model, Uplift, and Decision Artifact Governance

### 4.1. Separation of Candidate vs Production Artifacts
1. **Candidate Artifacts**: Churn models, uplift estimators, and decision policies generated during experimentation or training are tagged `STATUS = CANDIDATE`.
2. **Strict Production Promotion Barrier (`NFR-AI-001`)**: No candidate artifact can be served to live operational pipelines without:
   - Full evaluation report meeting all declared gates (`ECE <= 0.05`, `Qini > 0.20`, `Zero action mutations`).
   - Disparity audit confirming slice stability across protected dimensions.
   - Dual human approval sign-off (ML Platform Lead + Product Risk Owner).
   - Bitwise reproducible release manifest.

### 4.2. Shadow Evaluation and Canary Readiness
- New models run in offline shadow mode alongside production baselines for a minimum of 14 days.
- Retrained models are evaluated on identical test splits. Any regression in calibration ($> 0.05$ ECE) or uplift ($< 0.20$ Qini) halts deployment and triggers automatic rollback.

---

## 5. Traceability

`INV-AI-001..002`, `INV-SEC-001..002`, `INV-COST-001`, `INV-ACT-001..004`, `NFR-AI-001..007`, `NFR-PRV-001`; `ADR-0009..0012`.

---

## 6. Appendix: Industry Standards Alignment (NIST AI RMF & OWASP LLM)

### 6.1. NIST AI Risk Management Framework (AI RMF 1.0) Mapping

| NIST AI RMF Function | Subcategory / Objective | RevPilot AI Governance Control | Architectural Invariant / Reference |
|---|---|---|---|
| **GOVERN** (GV) | GV-1.1: Legal/regulatory requirements understood & managed | Statutory residency rules, zero retention SLA, tenant boundaries | `INV-TEN-001..003`, `ADR-0011`, `BLK-001`, `BLK-003` |
| **GOVERN** (GV) | GV-1.2: Clear roles, responsibilities, separation of duties | Explicit multi-agent boundaries; zero agent self-approval | `INV-ACT-003`, `ADR-0012`, `AGENTS.md` §3 |
| **MAP** (MP) | MP-2.1: Context of AI use & task boundaries categorized | Explicit investigation scope digest, typed DAG input/output | `INV-AI-001`, `AI-ARCHITECTURE.md` §Execution contract |
| **MAP** (MP) | MP-2.2: Third-party dependencies & supply chain documented | Registered model provider adapters, pinned model digests | `INV-SEC-002`, `ADR-0011`, `MODEL-RELEASE-PROCESS.md` |
| **MEASURE** (MS) | MS-1.1: Quantitative metrics for trustworthiness & safety | Golden-set regression evaluations, calibration ECE, Qini curve | `NFR-AI-001..007`, `EVALUATION-SPEC.md` |
| **MEASURE** (MS) | MS-2.5: Mitigation of disparate impact across groups | Protected slice fairness analysis, small-sample noise suppression | `FAIRNESS-SLICE-EVALUATION.md`, `AC-014` |
| **MANAGE** (MG) | MG-1.1: Risk treatment plans prioritized and implemented | Fail-closed tool gateway, budget hard stop ($2.00 target, $5.00 limit) | `INV-COST-001`, `INV-ACT-001`, `TOOL-GATEWAY-SPEC.md` |
| **MANAGE** (MG) | MG-2.2: Incident tracking, rollback, and continuous oversight | 14-day shadow validation, automated canary rollback on regression | `AI-GOVERNANCE.md` §4.2, `CANARY-ROLLBACK-VALIDATION.md` |

### 6.2. OWASP Top 10 for Large Language Model Applications (2025)

| Risk ID | Vulnerability Category | RevPilot Architecture Defense | Enforcement Mechanism |
|---|---|---|---|
| **LLM01** | Prompt Injection | Tainted input boundaries, pre-registered SQL catalog, zero raw SQL | `INV-ACT-001`, `SQL-CAPABILITY-CATALOG.md`, `INV-SEC-002` |
| **LLM02** | Sensitive Information Disclosure | Strict PII redaction interceptors, zero raw credentials in telemetry | `INV-PRV-001`, `NFR-PRV-001`, `OBSERVABILITY-SPEC.md` §4 |
| **LLM03** | Supply Chain Vulnerabilities | Bitwise reproducible release manifests, SHA-256 prompt/model digests | `INV-AI-001`, `AC-011`, `MODEL-RELEASE-PROCESS.md` |
| **LLM04** | Data and Model Poisoning | Air-gapped synthetic ground truth, read-only analytical catalog | `AC-001`, `SYNTHETIC-DATASET-SPEC.md`, `INV-DATA-002` |
| **LLM05** | Improper Output Handling | Schema validation, typed Pydantic models, JSON schema allowlists | `INV-AI-001`, `INV-EVD-001`, `AI-ARCHITECTURE.md` |
| **LLM06** | Excessive Agency | Strict prohibition of agent self-approval, mandatory human approval digests | `INV-ACT-001..003`, `ADR-0012`, `APPROVAL-ACTION-LOOP-SPEC.md` |
| **LLM07** | System Prompt Leakage | System prompts stored in immutable registry, excluded from client outputs | `INV-AI-001`, `FRONTEND-SPEC.md`, `PROMPT-REGISTRY.md` |
| **LLM08** | Vector and Embedding Weaknesses | Tenant-scoped vector indexes, RLS enforcement at retrieval time | `INV-TEN-001`, `RAG-SPEC.md`, `EVIDENCE-PROVENANCE-SPEC.md` |
| **LLM09** | Misinformation / Hallucination | Citation verification, evidence provenance ACL, zero unsupported claims | `INV-EVD-001..002`, `UNSUPPORTED-CLAIM-POLICY.md`, `AC-004` |
| **LLM10** | Unbounded Consumption | Multi-tier cost quotas, $2.00 target / $5.00 limit, execution timeouts | `INV-COST-001`, `NFR-COST-001..002`, `FINOPS-SPEC.md` |

