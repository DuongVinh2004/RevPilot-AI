# SRE Reliability Contract

Status: Proposed v0.1 — E03 specification output

Targets are the design targets in `NFR-BASELINE.md`: API availability/latency, workflow propagation/recovery, zero confirmed workflow loss/duplicate side effects, fail-closed writes, isolation and audit coverage. SLI ownership is API, Execution, Security, Tenancy, Audit and SRE as named there; no target is a measured result.

Dependencies declare retry, timeout, circuit/load-shed and degraded-read behavior. IAM/Policy/Audit uncertainty blocks writes/actions; workflow failure resumes from durable history; provider unknown result reconciles. Capacity decisions use workload assumptions and trigger ADR review rather than premature Kafka/Kubernetes. Runbooks require alert, owner, safe mitigation, evidence and post-incident tracking.

Required exercises: worker/process recovery, dependency outage matrix, tenant overload isolation, audit buffering, load test and chaos proportional to risk. Traceability: `INV-REL-001..002`, `NFR-AVL-*`, `NFR-REL-*`, `NFR-THR-*`.
