## Description

Clearly explain the purpose and scope of this pull request.

Fixes #(issue)

## Type of Change

- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Refactoring / Infrastructure optimization

## Invariant Compliance Checklist

Please ensure your changes satisfy all architectural invariants:

- [ ] **Fail-Closed Principle**: Fails safely on missing, ambiguous, or invalid inputs.
- [ ] **Multi-Tenant Isolation (INV-TEN-001)**: No cross-tenant data, cache, or context leaks.
- [ ] **Zero Agent Self-Approval (INV-ACT-003)**: Mutating business actions require cryptographically verified human approval tokens.
- [ ] **Anti-Fabrication Invariant (AC-014)**: No fabricated/mocked test scores or benchmark metrics.
- [ ] **Audit Provenance (INV-AUD-001)**: Actions and decisions produce immutable ledger entries.

## Verification & Testing

- [ ] Added unit / integration tests covering the new behavior.
- [ ] All 550+ tests pass locally (`python -m pytest tests/`).
- [ ] Type checking passes (`mypy packages/backend/src`).
- [ ] Linter passes without warnings (`ruff check .`).
