# Audit Baseline Record

Date: 2026-09-08  
Audit Commit SHA: `80eb4cbfdbba5011a1815e8d617033d8cad6ccb9`  
Current HEAD Commit SHA: `ecb45c90497ced93a583223365c1b6d5b0dc259a`  
Branch: `main`  
Auditor Scope: Zero-Trust Production Readiness & Security Remediation (30 Micro-Tasks, AR-001..AR-030)  
Status: BASELINE ESTABLISHED (Immutable)  

---

## 1. Runtime Environment

- **Python Version**: Python 3.14.4 (tags/v3.14.4:23116f9, Apr  7 2026, 14:10:54) [MSC v.1944 64 bit (AMD64)]
- **Node.js Version**: v26.5.1
- **Operating System**: Windows (AMD64)

---

## 2. Tool Availability Status

| Tool | Version / Path | Status |
|---|---|---|
| pytest | pytest 9.1.1 (`python -m pytest`) | AVAILABLE |
| ruff | ruff 0.16.6 (`python -m ruff`) | AVAILABLE |
| mypy | Module not found in active environment | BLOCKED |
| docker | Docker version 29.7.2, build a7dcaa6 (`C:\Program Files\Docker\Docker\resources\bin\docker.EXE`) | AVAILABLE |
| terraform | Not found in PATH | BLOCKED |
| psql | Not found in PATH | BLOCKED |
| temporal | Not found in PATH | BLOCKED |

---

## 3. Blocked Checks from Zero-Trust Audit Report

The following 15 findings were identified during the Zero-Trust Audit on commit `80eb4cbfdbba5011a1815e8d617033d8cad6ccb9`:

| Finding ID | Severity | Description | Remediation Task |
|---|---|---|---|
| P0-GOV-001 | P0 | False-green production acceptance & evidence claims | AR-001, AR-002, AR-029, AR-030 |
| P0-SEC-001 | P0 | Permissive startup & fail-open auth configuration | AR-004, AR-005 |
| P0-SEC-002 | P0 | SCIM bearer token & tenant binding bypass | AR-007, AR-008, AR-009 |
| P0-ACT-001 | P0 | Tool gateway unverified execution & digest mismatch | AR-011, AR-012, AR-013, AR-014, AR-016 |
| P1-FE-001 | P1 | Frontend dev auth bypass in production build | AR-010 |
| P1-DOM-001 | P1 | Domain analytics mock query returns | AR-017 |
| P1-DOM-002 | P1 | Decision / ML synthetic model returns | AR-018 |
| P1-DOM-003 | P1 | Causal inference synthetic estimators | AR-019 |
| P1-WF-001 | P1 | Temporal investigation workflow mock completions | AR-021 |
| P1-TEN-001 | P1 | Admin persistence & export tenant binding missing | AR-022, AR-024 |
| P1-SEC-003 | P1 | Webhook HMAC verification disabled / mock bypass | AR-023 |
| P1-REL-001 | P1 | Observability metrics simulated instrumentation | AR-025 |
| P1-IAC-001 | P1 | Production IaC hardening unverified | AR-026 |
| P1-SCM-001 | P1 | CI pipeline enforcement missing gates & dependency lock | AR-027, AR-028 |
| P2-TEST-001 | P2 | Inconsistent test collection counts across documentation | AR-003 |

---

## 4. Governance & Immutability

This baseline is immutable. Updates require a new baseline file with supersession link.
All remediation tasks must trace back to this provenance record.
