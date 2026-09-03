# AI Architecture Contract

Status: Proposed v0.1 — E02 specification output

## Authority and boundary

`investigations` owns the investigation scope; the AI platform owns bounded reasoning execution, version selection, and typed result validation. The platform is not an authority: it cannot authorize, approve, mutate business state, or call an external provider except through a registered capability port. Temporal calls it from Activities; it never owns durable workflow state.

## Execution contract

`AgentExecutionRequest` contains `tenant_id`, `investigation_id`, `run_id`, immutable `scope_digest`, `principal_delegation_ref`, `capability_catalog_version`, `artifact_manifest`, `deadline_utc`, and `budget`. `AgentExecutionResult` contains a schema version, `status` (`COMPLETED|NEED_MORE_EVIDENCE|DEGRADED|FAILED`), typed evidence/hypothesis/recommendation references, cost/usage, and safe diagnostics. Missing tenant, expired delegation, invalid schema, unavailable policy context, or exhausted budget rejects the request; no fallback may create authority.

Every execution records model, prompt, graph, tool-schema, dataset/index, policy and evaluator versions in the Investigation manifest. Model output is untrusted content. The verifier requires supporting Evidence references before a claim may reach Decision Intelligence. Explanations are generated summaries of structured findings; hidden chain-of-thought is neither stored nor exposed.

## Controls and evaluation

The trusted adapter enforces per-investigation model-call, token, tool-call, cost, and deadline limits before each call. Provider routing uses ADR-0011 capability requirements and tenant eligibility; it does not grant Tool authority. Emit `ai.execution.started`, `ai.execution.completed`, `ai.execution.degraded`, and `ai.execution.rejected` with opaque IDs only. Required gates are schema-validation, unsupported-claim, budget, prompt-injection, artifact-manifest completeness, and version-replay tests.

## Traceability

Implements `INV-AI-001..002`, `INV-SEC-001..002`, `INV-COST-001`, `NFR-AI-001`, and `NFR-OBS-001`; controlled by ADR-0003, ADR-0010, ADR-0011 and `SYSTEM-BOUNDARIES.md`.
