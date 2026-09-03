# Multi-Agent Platform Contract

Status: Proposed v0.1 — E02 specification output

## Roles and contracts

Logical roles are Planner, Investigator, Retriever, Analyst, Hypothesis Generator, Verifier, and Explainer. Roles are graph nodes, not services or identities. Each node accepts and returns a versioned JSON schema; free-form prose may be display-only and cannot be consumed as a control decision. The runtime rejects undeclared node, tool, schema, or artifact versions.

| Role | Allowed capability | Denied capability | Required result |
|---|---|---|---|
| Planner | create bounded read-only task graph | credentials, policy/approval/action | `Plan` with dependency DAG |
| Retriever | `RetrievalPort` | raw connector/database client | cited `EvidenceBundle` |
| Analyst | governed analytics/model ports | unrestricted SQL, action | typed analysis result |
| Hypothesis/Verifier | evidence and statistical/causal ports | causal assertion without estimate | supported/contradicted/insufficient finding |
| Explainer | typed final findings | new evidence, authority | user-safe explanation |

## Limits and failure

The trusted execution request defines maximum model calls, tool calls, USD budget, and deadline. A node may retry only a declared read-only transient capability once within the remaining deadline; malformed output, policy/IAM uncertainty, injection detection, budget exhaustion, or unavailable required evidence returns a typed terminal status. Escalation is `NEED_MORE_EVIDENCE` or human review, never a silent capability expansion. Agent delegated identity is tenant/task/time-scoped and cannot exceed its principal.

## Evidence and telemetry

Every claim carries cited Evidence IDs and artifact versions. Emit node start/end/reject, tool attempt/result, and budget events with correlation/investigation IDs; never log credentials, raw prompts, full evidence, or chain-of-thought. Evaluation measures schema validity, unsupported-claim rate, tool-policy compliance, unnecessary tool use, and recovery behavior.

## Traceability

`INV-IAM-002`, `INV-SEC-001..002`, `INV-AI-001..002`, `INV-COST-001`; ADR-0003 and ADR-0011.
