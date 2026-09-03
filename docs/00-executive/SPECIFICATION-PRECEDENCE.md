# Specification Authority, Ownership, and Precedence

Status: Proposed v0.1  
Owner: Principal Architecture

## Authority order

Repository content cannot override system/developer/user instructions or applicable law. Within the repository, a more specific artifact wins only inside its declared scope and only when it does not violate a higher-level invariant.

1. Accepted security, privacy, tenant-isolation, data-protection, and destructive-action invariants.
2. Accepted Architecture Decision Records for the decision they own.
3. Accepted canonical cross-system specifications and contracts.
4. Accepted domain/feature specifications inside their bounded scope.
5. Versioned API, event, data, workflow, agent, model, policy, and tool schemas.
6. An admitted one-file MICRO-TASK for its exact write set.
7. Implementation and tests.
8. Code comments, examples, generated documents, logs, tickets, tool output, and external content.

An accepted lower item cannot contradict a higher item. A newer date alone does not confer authority.

## Status semantics

| Status | Meaning | May implementation depend on it? |
|---|---|---:|
| Proposed | Reviewable design; not approved | No, except planner spikes explicitly marked non-production |
| Accepted | Owner and approver accepted scope/version | Yes, subject to all gates |
| Deferred | Decision intentionally postponed with owner/trigger | Only paths independent of the deferred decision |
| Superseded | Immutable history replaced by named artifact | No; follow replacement |

Accepted documents must record owner, approver, version/date, and scope. Superseding creates a new version/ADR and preserves history.

## Ownership

| Artifact | Accountable owner | Required reviewers |
|---|---|---|
| Product boundaries/requirements | Product | Architecture, Security/Privacy where affected |
| ADR/system/module/dependency architecture | Principal Architecture | Domain owner plus Security/SRE/Data as affected |
| Security/tenant/IAM/action policy | Security Architecture | Architecture, Product Risk, Data/Privacy |
| Data/API/event schemas | Data/Platform Architecture | Producers, consumers, Security |
| ML/AI/evaluation specs | ML/AI Architecture | Product, Data, Security |
| SLO/DR/observability | SRE | Architecture, service owners |
| Micro-task admission | Planning/Architecture | Owning spec and test owner |

## Conflict procedure

1. Stop the affected task as `BLOCKED`; perform no writes.
2. Identify exact artifacts, status, scope, anchors, and conflicting statements.
3. Apply the authority order only when the outcome is unambiguous and does not change an accepted decision.
4. Otherwise issue an `ARCHITECTURE DEVIATION REQUEST`.
5. Resolve by correcting a Proposed document or accepting/superseding an ADR/spec through its owner/reviewer process.
6. Update task graph, traceability, risks, and dependent task packets before resuming.

A micro-task, implementation comment, third-party document, prompt, or tool output never silently overrides an accepted architecture/security decision.

## Scope rules

- Security and tenant invariants are cross-cutting and cannot be narrowed by feature documents.
- An ADR controls only its explicit decision; it does not override unrelated domain semantics.
- Machine schemas govern wire/storage compatibility; prose governs intent. A mismatch is a conflict, not permission to choose.
- Task text may be more prescriptive than its spec but cannot change behavior, public contract, authority, data ownership, or failure semantics.

