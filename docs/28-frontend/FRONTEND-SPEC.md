# Experience Plane Contract

Status: Accepted v1.0
Owner: Frontend Architect  
Approver: Duong Vinh (Repository Owner)
Version: v1.0
Date: 2026-09-04

The web client renders investigation, evidence, recommendation, approval, action outcome, freshness/degraded state and audit-safe explanations from versioned API contracts. It has no database/provider credentials and cannot create tenant/role authority. Server responses control permitted actions; UI hiding is never authorization.

Every state represents loading, empty, unauthorized, stale/partial, failed and success explicitly. Evidence citations show provenance/effective date/classification according to access policy. Approval UI displays immutable action/target/cost/policy/version/expiry digest and invalidates on amendment/expiry. Generative explanation is labelled with evidence/limitation and never exposes chain-of-thought.

Required tests: accessibility, tenant/permission negatives, stale/partial behavior, error safety, digest tamper/replay and keyboard/screen-reader flows. Traceability: `INV-TEN-002`, `INV-ACT-003`, `INV-EVD-001`.

## Accessibility acceptance requirements

The client is `WCAG 2.2 AA design-target only`; conformance is not claimed until executed accessibility evidence exists.

- Every interactive control is keyboard reachable in a visible logical focus order; modal approval flows return focus to the invoking control.
- Native semantic landmarks, labels, headings, tables and status messages are required; custom controls expose the equivalent accessible name, role and state.
- Error, authorization-denied, stale and partial-data states are programmatically announced without exposing secrets, tenant data or hidden reasoning.
- Text and non-text contrast, zoom/reflow, target size and motion behavior meet the documented WCAG design target.
- Citation and approval digest views provide keyboard copy/navigation and screen-reader-safe summaries.
- Planned verification includes automated accessibility scanning plus manual keyboard and screen-reader flows. Results remain `NOT EXECUTED` until retained in the release evidence package.
