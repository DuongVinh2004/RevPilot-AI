# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0-rc1] - 2026-09-04

### Added
- **Core Architecture Baseline**: Complete domain, platform, and infrastructure specifications (ADR-0001 through ADR-0012).
- **Domain Modules**:
  - `analytics`: Anomaly localization and time-series telemetry.
  - `investigation`: Multi-agent ticket reasoning and graph-based evidence provenance.
  - `verifier`: Anti-hallucination claim grounder with fail-closed rejection policies.
  - `causal`: Causal graph inference and uplift estimation engine.
  - `decision`: Constraint-satisfaction decision engine with financial budget bounding.
  - `approval`: Human-in-the-loop approval workflows with cryptographic HMAC tokens.
  - `action`: Idempotent tool execution gateway with blast radius limiters.
  - `safety`: Emergency kill-switch mechanisms for real-time risk mitigation.
- **Enterprise IAM & Tenancy**: Multi-tenant isolation with tenant-scoped DB schemas and SCIM/OIDC identity management.
- **Micro-Services & Apps**:
  - `apps/api`: High-performance FastAPI gateway with full domain routing.
  - `apps/web`: TypeScript/Vite frontend featuring real-time Anomaly Dashboard, Investigation Explorer, and Approval Center.
  - `apps/ingestion-worker`, `apps/ml-worker`, `apps/workflow-worker`: Async background processing services.
- **Automated Verification**: Comprehensive test suite with 554 automated integration and unit tests passing.
- **Deployment Topology**: Multi-container `compose.yaml` featuring 3-zone defense-in-depth isolation (DMZ, Compute, Persistence).

## [0.1.0] - 2026-08-15

### Added
- Initial repository layout, toolchain configuration, and specification foundations.
