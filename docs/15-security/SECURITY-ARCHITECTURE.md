# Security Architecture Contract

Status: Proposed v0.1 — E03 specification output

Trust boundaries are Browser/API, identity provider, Temporal, AgentRuntime, data/retrieval, Policy/Approval, Tool Gateway and external providers. Client/model/external content is untrusted and cannot create tenant, authority, tool, destination or policy rights. Agents never receive reusable credentials; registered Tool Gateway adapters obtain scoped credentials from the broker.

Controls: authenticated trusted-context resolution; deny-by-default authorization; schema/taint validation; tool registry and egress allowlist with DNS/IP SSRF checks; classification/minimization/redaction; immutable minimized audit; RLS/cross-store isolation; secrets through ADR-0009; dependency boundary scans; safe errors. Security uncertainty fails closed for writes/actions. Operational telemetry excludes secrets, raw prompts and chain-of-thought.

Security reviews each Threat Model story against control, owner, negative test and alert. No certification/compliance claim is made without evidence. Traceability: `SEC-001..010`, `INV-SEC-001..003`, `INV-ACT-001..004`, `INV-PRV-001`.
