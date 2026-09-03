# IAM and Delegation Contract

Status: Proposed v0.1 — E03 specification output

Authentication establishes a `Principal`; authorization evaluates tenant membership, RBAC permissions and ABAC attributes server-side. User, service account, Agent delegated identity and API credential reference are distinct. MFA/SSO are future identity-provider capabilities and do not change the requirement for verified server-side context. Default is deny.

`Delegation` binds delegating principal, tenant, investigation/task, allowed capability/target, expiry and revocation version. It cannot exceed its delegator, cannot grant credentials, approval authority or unrestricted access, and is rechecked at every capability boundary. Service-to-service identity uses workload identity and least privilege, never a user token copied by an agent. Authorization/policy uncertainty blocks writes and actions.

Audit principal changes, membership, delegation issuance/revocation, privileged access and denied sensitive calls. Required tests: missing/forged/expired/revoked delegation, cross-tenant membership, permission/attribute matrix, service identity and break-glass negatives. Traceability: `INV-IAM-001..002`, `INV-TEN-002..003`, `INV-REL-001`.
