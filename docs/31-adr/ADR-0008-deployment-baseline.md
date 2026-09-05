# ADR-0008 — Deployment Baseline

Status: Accepted  
Date: 2026-09-03  
Owner: Platform/SRE Architecture  
Approver: Dương Vinh
Version: v1.0

## Context

RevPilot needs reproducible local/demo environments and an initial commercial deployment, but has no measured Kubernetes scheduling, scale, networking, or ownership requirement. Premature orchestration would consume effort needed for correctness and safety.

## Decision

Package runtime components as OCI containers. Use local container composition for development/demo. For initial commercial deployment, use a provider-neutral managed container execution platform with managed PostgreSQL, object storage, identity, secrets, and supported Temporal. Do not implement Kubernetes, service mesh, or active-active multi-region in the baseline.

## Decision Drivers

Environment repeatability, low operational overhead, workload assumptions, modular-monolith deployment, explicit future seams.

## Alternatives

- Kubernetes-first: rejected because scale/network/ownership drivers are unproven.
- Long-lived VMs: rejected as default because patching/process/container orchestration burden is higher.
- Pure serverless functions: rejected for long workers, model workloads, and Temporal Activities.

## Why Selected

Managed containers support current deployables and scaling needs while preserving portability to Kubernetes if justified.

## Pros

Simple environments, smaller SRE surface, portable images, managed scaling/health.

## Cons

Provider capability limits; local composition differs from managed data services; Kubernetes migration remains possible work.

## Consequences

Images are immutable/scanned/signed; configuration is external; workloads use health/readiness and graceful shutdown. Provider selection remains an owned open decision.

## Risks

Provider lock-in or insufficient worker/network controls. Mitigate through portable contracts, workload identity abstraction, and a provider evaluation before production.

## Security Impact

Production requires private service connectivity where supported, managed identity, least privilege, secret broker, image provenance, and separate action boundary.

## Tenancy Impact

Shared versus dedicated runtime follows ADR-0005; container scheduling does not constitute tenant isolation alone.

## Operational Impact

Managed container operations need SLOs, deployment rollback, logs/traces/metrics, backup dependencies, and incident ownership.

## Cost Impact

Lower fixed operations cost initially; managed services may cost more per unit but reduce staffing burden.

## Implementation Implications

Repository documents application/container contracts but creates no deployment implementation in Phase 00. Environment-specific infrastructure waits for provider ADR/spec.

## Revisit Triggers

Evaluate Kubernetes when at least two apply: >10 independently scaled/deployed workloads; managed platform cannot meet a signed network/security/scheduling requirement; workloads sustain >70% platform limits for three 7-day windows; multi-team ownership needs independent namespaces/release policy; required GPU/bin-packing/custom scheduling is unavailable; or platform cost model shows >=25% total-cost improvement including two named Kubernetes operators/on-call ownership. Active-active multi-region needs separate business-impact/consistency ADR.

## Affected Requirements

`NFR-REL-001..002`, `NFR-OBS-001`, `NFR-COST-001`, `SEC-001..003`.

## Affected Specs

Repository topology, deployment architecture, SRE, DR, secrets, observability.
