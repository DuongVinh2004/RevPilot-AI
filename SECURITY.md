# Security Policy

## Supported Versions

Only the latest active release branch receives security updates.

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

We take the security of RevPilot AI seriously. If you believe you have found a security vulnerability, please do **not** report it via public GitHub issues.

### Private Disclosure Process

1. Submit a report privately using [GitHub Security Advisories](https://github.com/DuongVinh2004/RevPilot-AI/security/advisories/new).
2. Alternatively, email the maintainer directly at security@revpilot.ai or contact the repository owner.
3. Include detailed steps to reproduce the vulnerability, proof of concept (PoC), and affected components.

### Response Timelines

- **Initial Acknowledgment**: Within 24 hours.
- **Triage & Impact Assessment**: Within 72 hours.
- **Fix & Advisory Release**: Coordinated with reporter under standard 90-day responsible disclosure.

### Architectural Invariants & Threat Model

For full details on the platform's multi-tenant isolation, fail-closed tool gateway, and threat model, consult:
- [docs/15-security/SECURITY-ARCHITECTURE.md](docs/15-security/SECURITY-ARCHITECTURE.md)
- [docs/15-security/THREAT-MODEL.md](docs/15-security/THREAT-MODEL.md)
- [docs/03-requirements/INVARIANT-REGISTRY.md](docs/03-requirements/INVARIANT-REGISTRY.md)
