# Implementation Dependency Graph

Status: Proposed v0.1

This file describes phase/feature dependencies. It is not an executor queue. The normative rail gates are in `execution/MICRO-TASK-RAIL-SYSTEM.md`; machine-readable planning edges are in `execution/task-graph.json`. Only one-file MICRO-TASKS explicitly listed in `execution/EXECUTOR-QUEUE.md` may be executed.

Active execution node: `TASK-BOOTSTRAP-001` (Stage-B source/toolchain bootstrap under Phase 00, Rail 0). All downstream phase nodes (`D01`, `C01`, `W01`, etc.) remain blocked until Rail 0 is GREEN.

```mermaid
flowchart TD
  P00[Phase 00\nAccepted specs + ADRs] --> D01[Canonical schema + metric registry]
  P00 --> C01[Tenant/IAM context contracts]
  P00 --> W01[Temporal/agent contracts]
  D01 --> S01[Synthetic generator + ground truth]
  D01 --> I01[Ingestion + data quality]
  S01 --> A02[Anomaly benchmark]
  I01 --> A02
  C01 --> Q03[Authorized SQL capability]
  C01 --> R03[Governed hybrid RAG]
  W01 --> F03[Durable investigation workflow]
  A02 --> F03
  Q03 --> F03
  R03 --> F03
  F03 --> H04[Hypothesis + verifier]
  S01 --> CA04[Causal benchmark]
  H04 --> RCA04[RCA evaluation]
  CA04 --> RCA04
  S01 --> CH05[Churn/calibration]
  S01 --> UP05[Uplift benchmark]
  RCA04 --> DE05[Decision optimizer]
  CH05 --> DE05
  UP05 --> DE05
  C01 --> PA06[Policy + approval binding]
  DE05 --> PA06
  PA06 --> TG06[Tool Gateway + mock adapters]
  TG06 --> OM06[Outcome measurement]
  C01 --> CT07[Connector + tenant lifecycle]
  TG06 --> CT07
  CT07 --> PR08[Production readiness gates]
  OM06 --> PR08
```

## Parallelizable work

- After Phase 00: canonical schema, IAM/tenant context, and Temporal/agent contract spikes can proceed in parallel.
- After canonical schema: synthetic generator and ingestion/data quality can proceed in parallel.
- In Phase 03: authorized SQL, governed RAG, and durable workflow implementation can proceed in parallel against accepted contracts.
- In Phase 04/05: causal, churn, and uplift experiments can run in parallel, but decision integration waits for their versioned output contracts.
- Observability, threat tests, and cost attribution are cross-cutting tasks in every phase, not a final add-on.

## Hard gates

- No investigation implementation before tenant context and evidence contracts are accepted.
- No action adapter before policy, approval digest, idempotency, ledger, dry-run, and kill-switch contracts pass.
- No learned artifact reaches production without offline/regression/safety/canary release gates.
- No pilot tenant before cross-store isolation and deletion/export tests pass.
- No EPIC/FEATURE or wildcard task is sent to Antigravity; executor tasks require readiness >=18/20, or 20/20 for critical security/tenant/financial/action work.
- No dependent micro-task starts while an upstream task or rail is FAIL/BLOCKED/RED.
