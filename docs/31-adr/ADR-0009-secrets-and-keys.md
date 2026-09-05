# ADR-0009 — Secrets and Keys

Status: Accepted  
Date: 2026-09-03  
Owner: Security Architecture  
Approver: Dương Vinh
Version: v1.0

## Context

RevPilot integrates with model and enterprise providers. Reusable credentials in prompts, source, logs, task packets, or Agent Runtime would create a critical confused-deputy/exfiltration risk. Production cloud is not selected.

## Decision

Local development may inject secrets into process environment from an uncommitted developer-controlled secret source; test defaults use fakes. Commercial environments use a managed secret/key service accessed through workload identity. Tool Gateway's Credential Broker obtains the narrowest short-lived provider credential available. Agents receive capability results, never credential values. Tenant envelope encryption and CMEK are introduced by entitlement/contract triggers.

## Decision Drivers

`SEC-002..004`, provider integration, rotation/revocation, auditability, cloud neutrality.

## Alternatives

- Self-hosted Vault by default: capable but rejected without an operations team/need.
- Static environment secrets in production: rejected due lifetime/rotation/audit weakness.
- Agent-held API keys: prohibited.

## Why Selected

It establishes one safe interface and lifecycle while deferring vendor choice until deployment is known.

## Pros

No secret in AI context, managed rotation/audit, short-lived provider authority, testability.

## Cons

Provider capability varies; managed dependency outage blocks actions; CMEK/dedicated keys add lifecycle work.

## Consequences

Secret values are never logged, audited, returned, persisted in task/workflow inputs, or placed in Git. Only reference, purpose, recipient, and access event may be recorded safely.

## Risks

Long-lived fallback tokens, cache leakage, broker overprivilege. Mitigate with expiry, memory-only bounded cache, redaction/DLP tests, explicit scopes, revocation runbooks.

## Security Impact

Credential broker failure, ambiguous Tenant, policy failure, or key revocation fails closed for external actions.

## Tenancy Impact

Secret references/scopes are Tenant-bound. Enterprise/Regulated may have dedicated secret namespace/key/CMEK.

## Operational Impact

Requires access audit, rotation/revocation, expiry alerts, break-glass separation, backup/key-loss recovery design.

## Cost Impact

Managed secret operations and dedicated keys incur per-tenant cost; entitlement/billing must capture it.

## Implementation Implications

Define `SecretProvider` and `CredentialBroker` ports after spec acceptance. Production provider adapter is blocked until deployment provider is selected.

## Revisit Triggers

Evaluate self-hosted Vault only if multi-cloud/on-prem contracts require a common control plane, cloud-native store cannot meet dynamic credential/CMEK requirements, or managed secret costs exceed the supported Vault total cost by >=25% with named 24/7 ownership. Require dedicated tenant key/namespace when signed contract/regulation mandates it or shared-key blast radius is rejected by risk review.

## Affected Requirements

`SEC-002..004`, `FR-ACT-001`, `FR-CTL-001..003`, `NFR-PRV-001`.

## Affected Specs

Security architecture, IAM, Tool Gateway, connectors, multi-tenancy, audit, deployment.
