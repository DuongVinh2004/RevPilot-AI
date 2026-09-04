# Implementation Dependency Graph

Status: Accepted Post-Phase-08 v1.9 — Rails 0–5 GREEN; Rails 6–18 LOCKED; Phase 08 documentation closure complete (`DOCUMENTATION COMPLETE / VALIDATION PENDING / GO-LIVE BLOCKED`).

This file describes phase/feature dependencies. It is not an executor queue. The normative rail gates are in `execution/MICRO-TASK-RAIL-SYSTEM.md`; machine-readable planning edges are in `execution/task-graph.json`. Only one-file MICRO-TASKS explicitly listed in `execution/EXECUTOR-QUEUE.md` may be executed.

Completed Rail 1: `TASK-R01-001` through `TASK-R01-004` (all PASS). Completed Rail 2: `TASK-R02-001` through `TASK-R02-004` (all PASS). Completed Rail 3: `TASK-R03-001` through `TASK-R03-004` (all PASS). Completed Rail 4: `TASK-R04-001` through `TASK-R04-004` (all PASS). Completed Rail 5: `TASK-R05-001` through `TASK-R05-004` (all PASS). Rails 0–5 are GREEN. Rails 6–18 are LOCKED. No admitted execution node (executor queue empty).

## Control Plane Rails 3–5 Sequential Rail Dependency Chain

```mermaid
flowchart TD
  subgraph Rail02 [Rail 2: Tenant Context - GREEN]
    R02_04[TASK-R02-004 PASS]
  end

  subgraph Rail03 [Rail 3: Authentication - GREEN]
    R03_01[TASK-R03-001 PASS] --> R03_02[TASK-R03-002 PASS]
    R03_02 --> R03_03[TASK-R03-003 PASS]
    R03_03 --> R03_04[TASK-R03-004 PASS Exit Gate]
  end

  subgraph Rail04 [Rail 4: Authorization and Delegation - GREEN]
    R04_01[TASK-R04-001 PASS] --> R04_02[TASK-R04-002 PASS]
    R04_02 --> R04_03[TASK-R04-003 PASS]
    R04_03 --> R04_04[TASK-R04-004 PASS Exit Gate]
  end

  subgraph Rail05 [Rail 5: Persistence Isolation - GREEN]
    R05_01[TASK-R05-001 PASS] --> R05_02[TASK-R05-002 PASS]
    R05_02 --> R05_03[TASK-R05-003 PASS]
    R05_03 --> R05_04[TASK-R05-004 PASS Exit Gate]
  end

  R02_04 --> R03_01
  R03_04 --> R04_01
  R04_04 --> R05_01
```

## Phase 01 Canonical Data and Synthetic Benchmark Micro-Task Chain

```mermaid
flowchart TD
  subgraph Phase01 [Phase 01: Canonical Data and Synthetic Benchmark - DRAFT PLANNING]
    P01_01[TASK-P01-001 DRAFT\nCanonical Data Model Contracts]
    P01_02[TASK-P01-002 DRAFT\nMetric Registry & Semantics]
    P01_03[TASK-P01-003 DRAFT\nSynthetic Generator Contract]
    P01_04[TASK-P01-004 DRAFT\nHidden Ground Truth & Midwest Incident]
    P01_05[TASK-P01-005 DRAFT\nData Quality, Lineage & Quarantine]
    P01_06[TASK-P01-006 DRAFT\nPhase 01 Exit Gate]

    P01_01 --> P01_02
    P01_01 --> P01_03
    P01_02 --> P01_03
    P01_03 --> P01_04
    P01_01 --> P01_05
    P01_03 --> P01_05
    P01_01 --> P01_06
    P01_02 --> P01_06
    P01_03 --> P01_06
    P01_04 --> P01_06
    P01_05 --> P01_06
  end

  R02_04[TASK-R02-004 PASS\nRail 2 Exit Gate] --> P01_01
```

## Phase 02 Detection and Analytics Micro-Task Chain

```mermaid
flowchart TD
  subgraph Phase02 [Phase 02: Detection and Analytics - DRAFT PLANNING]
    P02_01[TASK-P02-001 DRAFT\nMetric Service Contract & Queries]
    P02_02[TASK-P02-002 DRAFT\nDeterministic Detection Baselines]
    P02_03[TASK-P02-003 DRAFT\nDetector Benchmark & Rolling Split]
    P02_04[TASK-P02-004 DRAFT\nAnomaly Localization & Drill-Down]
    P02_05[TASK-P02-005 DRAFT\nLifecycle, Replay & Reconciliation]
    P02_06[TASK-P02-006 DRAFT\nPhase 02 Exit Gate]

    P02_01 --> P02_02
    P02_01 --> P02_03
    P02_02 --> P02_03
    P02_01 --> P02_04
    P02_03 --> P02_04
    P02_01 --> P02_05
    P02_04 --> P02_05
    P02_01 --> P02_06
    P02_02 --> P02_06
    P02_03 --> P02_06
    P02_04 --> P02_06
    P02_05 --> P02_06
  end

  P01_06[TASK-P01-006 DRAFT\nPhase 01 Exit Gate] --> P02_01
```

## Phase 03 Governed Evidence and Investigation Micro-Task Chain

```mermaid
flowchart TD
  subgraph Phase03 [Phase 03: Governed Evidence and Investigation - DRAFT PLANNING]
    P03_01[TASK-P03-001 DRAFT\nInvestigation Domain, Manifest & Budget]
    P03_02[TASK-P03-002 DRAFT\nTemporal Investigation Workflow Contract]
    P03_03[TASK-P03-003 DRAFT\nRegistered Read-Only SQL Catalog]
    P03_04[TASK-P03-004 DRAFT\nEvidence Provenance, ACL & Dates]
    P03_05[TASK-P03-005 DRAFT\nGoverned Hybrid Retrieval & Citations]
    P03_06[TASK-P03-006 DRAFT\nTyped Agent Planner & Verifier]
    P03_07[TASK-P03-007 DRAFT\nTicket Intelligence & Untrusted Bound]
    P03_08[TASK-P03-008 DRAFT\nPhase 03 Exit Gate & Recovery]

    P03_01 --> P03_02
    P03_01 --> P03_03
    P03_01 --> P03_04
    P03_02 --> P03_04
    P03_04 --> P03_05
    P03_02 --> P03_06
    P03_03 --> P03_06
    P03_04 --> P03_06
    P03_04 --> P03_07
    P03_01 --> P03_08
    P03_02 --> P03_08
    P03_03 --> P03_08
    P03_04 --> P03_08
    P03_05 --> P03_08
    P03_06 --> P03_08
    P03_07 --> P03_08
  end

  P02_06[TASK-P02-006 DRAFT\nPhase 02 Exit Gate] --> P03_01
  R05_04[TASK-R05-004 PASS\nRail 5 Exit Gate] --> P03_01
```

## Phase 04 Hypothesis, Causal Analysis, and Verification Micro-Task Chain

```mermaid
flowchart TD
  subgraph Phase04 [Phase 04: Hypothesis, Causal Analysis, and Verification - DRAFT PLANNING]
    P04_01[TASK-P04-001 DRAFT\nHypothesis Domain & Competing Ranking]
    P04_02[TASK-P04-002 DRAFT\nClaim Taxonomy & Verifier Policy]
    P04_03[TASK-P04-003 DRAFT\nCausal Study & Estimand Identification]
    P04_04[TASK-P04-004 DRAFT\nAIPW Estimation & Overlap Diagnostics]
    P04_05[TASK-P04-005 DRAFT\nSynthetic Causal & RCA Benchmark]
    P04_06[TASK-P04-006 DRAFT\nPhase 04 Exit Gate & Replay]

    P04_01 --> P04_02
    P04_01 --> P04_03
    P04_03 --> P04_04
    P04_01 --> P04_05
    P04_02 --> P04_05
    P04_04 --> P04_05
    P04_01 --> P04_06
    P04_02 --> P04_06
    P04_03 --> P04_06
    P04_04 --> P04_06
    P04_05 --> P04_06
  end

  P03_06[TASK-P03-006 DRAFT\nTyped Agent Planner & Verifier] --> P04_01
  P03_08[TASK-P03-008 DRAFT\nPhase 03 Exit Gate] --> P04_01
  P03_03[TASK-P03-003 DRAFT\nRegistered Read-Only SQL Catalog] --> P04_03
  P01_04[TASK-P01-004 DRAFT\nHidden Ground Truth & Midwest Incident] --> P04_05
```

## Phase 05 Churn, Uplift, and Decision Optimization Micro-Task Chain

```mermaid
flowchart TD
  subgraph Phase05 [Phase 05: Churn, Uplift, and Decision Optimization - DRAFT PLANNING]
    P05_01[TASK-P05-001 DRAFT\nChurn Prediction & ECE Calibration]
    P05_02[TASK-P05-002 DRAFT\nLocal SHAP & Epistemic Safety]
    P05_03[TASK-P05-003 DRAFT\nUplift CATE & Qini Benchmark]
    P05_04[TASK-P05-004 DRAFT\nBudget, Capacity & Policy Constraints]
    P05_05[TASK-P05-005 DRAFT\nExpected Utility Optimizer & Simulation]
    P05_06[TASK-P05-006 DRAFT\nFairness Slices & Reproducibility]
    P05_07[TASK-P05-007 DRAFT\nPhase 05 Exit Gate]

    P05_01 --> P05_02
    P05_01 --> P05_05
    P05_03 --> P05_05
    P05_04 --> P05_05
    P05_01 --> P05_06
    P05_02 --> P05_06
    P05_05 --> P05_06
    P05_01 --> P05_07
    P05_02 --> P05_07
    P05_03 --> P05_07
    P05_04 --> P05_07
    P05_05 --> P05_07
    P05_06 --> P05_07
  end

  P01_03[TASK-P01-003 DRAFT\nCanonical Entity Schemas] --> P05_01
  P01_04[TASK-P01-004 DRAFT\nHidden Ground Truth & Midwest Incident] --> P05_01
  P01_04 --> P05_03
  P04_04[TASK-P04-004 DRAFT\nAIPW Estimation & Overlap Diagnostics] --> P05_03
  P03_03[TASK-P03-003 DRAFT\nRegistered Read-Only SQL Catalog] --> P05_04
  R05_04[TASK-R05-004 PASS\nRail 5 Exit Gate] --> P05_04
```

## Phase 06 Approval and Safe Action Loop Micro-Task Chain

```mermaid
flowchart TD
  subgraph Phase06 [Phase 06: Approval and Safe Action Loop - DRAFT PLANNING]
    P06_01[TASK-P06-001 DRAFT\nApproval Lifecycle & Immutable Digest]
    P06_02[TASK-P06-002 DRAFT\nPolicy Revalidation & Authority Tiers]
    P06_03[TASK-P06-003 DRAFT\nDry-Run & Action Ledger Idempotency]
    P06_04[TASK-P06-004 DRAFT\nTool Gateway & Credential Broker]
    P06_05[TASK-P06-005 DRAFT\nMulti-Tier Kill Switches & Blast Radius]
    P06_06[TASK-P06-006 DRAFT\nSaga Compensation & UNKNOWN Reconciliation]
    P06_07[TASK-P06-007 DRAFT\nAction Outcome & Outbox Audit]
    P06_08[TASK-P06-008 DRAFT\nPhase 06 Composite Exit Gate]

    P06_01 --> P06_02
    P06_01 --> P06_03
    P06_02 --> P06_03
    P06_02 --> P06_04
    P06_03 --> P06_04
    P06_03 --> P06_05
    P06_04 --> P06_05
    P06_03 --> P06_06
    P06_04 --> P06_06
    P06_03 --> P06_07
    P06_06 --> P06_07
    P06_01 --> P06_08
    P06_02 --> P06_08
    P06_03 --> P06_08
    P06_04 --> P06_08
    P06_05 --> P06_08
    P06_06 --> P06_08
    P06_07 --> P06_08
  end

  P05_05[TASK-P05-005 DRAFT\nExpected Utility Optimizer] --> P06_01
  R03_01[TASK-R03-001 PASS\nAuthentication Claims Primitives] --> P06_01
  R04_04[TASK-R04-004 DRAFT\nRail 4 Authorization Exit Gate] --> P06_02
  P05_04[TASK-P05-004 DRAFT\nBudget Constraints] --> P06_05
  P03_01[TASK-P03-001 DRAFT\nTemporal Workflow Skeleton] --> P06_06
```

## Phase 07 Multi-Tenant Pilot and Connectors Micro-Task Chain

```mermaid
flowchart TD
  subgraph Phase07 [Phase 07: Multi-Tenant Pilot, Connectors & Operations - DRAFT PLANNING]
    P07_01[TASK-P07-001 DRAFT\nTenant Lifecycle & Deletion Cascade]
    P07_02[TASK-P07-002 DRAFT\nOIDC Identity Federation & PKCE]
    P07_03[TASK-P07-003 DRAFT\nSAML ACS & SCIM Provisioning]
    P07_04[TASK-P07-004 DRAFT\nConnector Secret & Key Rotation]
    P07_05[TASK-P07-005 DRAFT\nConnector Lifecycle & Health]
    P07_06[TASK-P07-006 DRAFT\nWebhook Replay & Drift Quarantine]
    P07_07[TASK-P07-007 DRAFT\nTenant Quotas & Metering Attribution]
    P07_08[TASK-P07-008 DRAFT\nPhase 07 Composite Exit Gate]

    P07_01 --> P07_02
    P07_02 --> P07_03
    P07_01 --> P07_04
    P07_04 --> P07_05
    P07_01 --> P07_05
    P07_05 --> P07_06
    P07_06 --> P07_07
    P07_01 --> P07_07
    P07_01 --> P07_08
    P07_02 --> P07_08
    P07_03 --> P07_08
    P07_04 --> P07_08
    P07_05 --> P07_08
    P07_06 --> P07_08
    P07_07 --> P07_08
  end

  P06_08[TASK-P06-008 DRAFT\nPhase 06 Composite Exit Gate] --> P07_01
  R02_04[TASK-R02-004 PASS\nRail 2 Tenancy Exit Gate] --> P07_01
  R03_01[TASK-R03-001 PASS\nAuthentication Claims Primitives] --> P07_02
  P06_04[TASK-P06-004 DRAFT\nTool Gateway & Credential Broker] --> P07_04
```

## Phase 08 Production Readiness, Release Governance & Operational Evidence Micro-Task Chain

```mermaid
flowchart TD
  subgraph Phase08 [Phase 08: Production Readiness, Release Governance & Operational Evidence - DRAFT PLANNING]
    P08_01[TASK-P08-001 DRAFT\nProduction Readiness Gate & Matrix]
    P08_02[TASK-P08-002 DRAFT\nObservability, SLOs & Telemetry]
    P08_03[TASK-P08-003 DRAFT\n13-Tier Canary & Rollback Manager]
    P08_04[TASK-P08-004 DRAFT\nAI Model & Prompt Release Controls]
    P08_05[TASK-P08-005 DRAFT\nDR Cold Restore & WAL Validation]
    P08_06[TASK-P08-006 DRAFT\nLoad, Stress & Chaos Harness]
    P08_07[TASK-P08-007 DRAFT\nCompliance Evidence & DLP Scanner]
    P08_08[TASK-P08-008 DRAFT\nPhase 08 Final Exit Review]

    P08_01 --> P08_08
    P08_02 --> P08_08
    P08_03 --> P08_08
    P08_04 --> P08_08
    P08_05 --> P08_08
    P08_06 --> P08_08
    P08_07 --> P08_08
  end

  P07_08[TASK-P07-008 DRAFT\nPhase 07 Composite Exit Gate] --> P08_01
  P07_08 --> P08_02
  P07_08 --> P08_03
  P07_08 --> P08_04
  P07_08 --> P08_05
  P07_08 --> P08_06
  P07_08 --> P08_07
  P07_07[TASK-P07-007 DRAFT\nQuotas & Metering Attribution] --> P08_02
```

## Top-Level Phase Overview

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
