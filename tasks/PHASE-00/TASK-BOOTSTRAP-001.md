# TASK-BOOTSTRAP-001 — Establish and Verify Canonical Source and Toolchain Scaffold

TYPE: MICRO-TASK  
STATUS: READY  
RAIL: 0  
INITIATIVE: REVPILOT  
PHASE: PHASE-00  
EPIC: SPEC-P00-E05  
FEATURE: REPOSITORY-TOOLCHAIN-BOOTSTRAP  
COMPLEXITY: S  
REASONING_LOAD: LOW  
READINESS_SCORE: 20/20  
NEW_ARCHITECTURAL_DECISIONS_ALLOWED: 0  
PARALLEL_SAFE: NO  
PARALLEL_WITH: NONE  
DEPENDS_ON: SPEC-P00-E05  
UNLOCKS: RAIL-0-GREEN, RAIL-1  

---

## Objective and rationale

OBJECTIVE: Establish git tracking baseline, approved repository directory skeleton matching `REPOSITORY-TOPOLOGY.md`, core workspace configuration manifests (`pyproject.toml`, `package.json`, `.gitignore`, `.gitattributes`, `.editorconfig`), safe placeholder environment configuration (`config/examples/env.example`), and a non-destructive topology verification test (`tests/test_bootstrap_topology.py`).

BUSINESS RATIONALE: Provide a concrete, reproducible, machine-verifiable workspace foundation so that subsequent Stage-B implementation micro-tasks can lease exact source paths and run automated tests without guessing directory structure, toolchain configuration, or Git policies.

ARCHITECTURAL OWNER: Repository Governance Architect + Platform Architecture  
ARCHITECTURAL CONTEXT: Conforms to `ADR-0001` (Modular Monolith), `ADR-0008` (Deployment Baseline), `docs/04-system-architecture/REPOSITORY-TOPOLOGY.md`, `docs/04-system-architecture/MODULE-BOUNDARIES.md`, and `execution/MICRO-TASK-RAIL-SYSTEM.md`.

---

## Canonical specification references

- `docs/04-system-architecture/REPOSITORY-TOPOLOGY.md` §topology, §top-level-ownership, §backend-module-shape, §bootstrap-gate
- `docs/04-system-architecture/MODULE-BOUNDARIES.md` §module-map
- `docs/04-system-architecture/DEPENDENCY-RULES.md` §layer-direction, §cross-module-rules
- `docs/31-adr/ADR-0001-application-architecture.md`
- `docs/31-adr/ADR-0008-deployment-baseline.md`
- `docs/03-requirements/INVARIANT-REGISTRY.md` (`INV-SEC-001`, `INV-TEN-001..003`, `INV-ACT-001..004`)
- `execution/MICRO-TASK-RAIL-SYSTEM.md` §rail-sequence (Rail 0 exit criteria), §two-stage-generation
- `execution/IMPLEMENTATION-STANDARDS.md` §change-boundary-rule, §engineering-invariants
- `execution/FLASH-EXECUTOR-RULEBOOK.md` §task-selection, §git-rules, §evidence-rules

---

## Preconditions

1. `SPEC-P00-E01` through `SPEC-P00-E05` are in `PASS` status.
2. Rail 0 is currently in `AMBER` status.
3. Git is installed and available in PATH (`git version 2.54.0.windows.1` or compatible).
4. Python 3.12+ is installed and available in PATH (`python --version` returns >= 3.12; local runtime is Python 3.14.4).
5. Node.js v20+ and npm v10+ are available in PATH (local runtime is Node.js v26.5.1, npm 11.17.0).
6. Python module `pytest` is available (`python -m pytest --version` returns exit code 0).
7. Workspace root `C:\Users\Duong Vinh\RevPilot AI` contains no application source files (`apps/` and `packages/backend/src/` do not yet exist).
8. Git is currently uninitialized (directory `.git` does not exist).

---

## Scope

### IN_SCOPE

- Initialize local Git repository with default branch `main`.
- Create `.gitignore` and `.gitattributes` tailored to Python, TypeScript, Node.js, and RevPilot artifacts.
- Create `.editorconfig` specifying indentation, charset, and newline standards.
- Create root `pyproject.toml` declaring package metadata, Python >= 3.12 constraint, `pytest` configuration, and module package discovery for `packages/backend/src`.
- Create root `package.json` declaring workspace scripts and metadata (private workspace).
- Create directory skeleton matching `REPOSITORY-TOPOLOGY.md` with `.gitkeep` markers where empty.
- Create `config/examples/env.example` documenting required environment variables with safe placeholder values.
- Create `tests/test_bootstrap_topology.py` verifying that all canonical directories exist, Python version >= 3.12, and no secrets exist in examples.
- Create initial git commit capturing the scaffold.
- Run non-destructive verification commands and report exact exit codes.

### OUT_OF_SCOPE

- Application business logic in any module.
- Domain entities, aggregates, repositories, or services.
- Database models, migrations, or active connections.
- API route handlers, controllers, or FastAPI composition code.
- Next.js application code or React components.
- Temporal workflow or activity definitions.
- Agent runtime, LangGraph graphs, or prompt templates.
- Machine learning or causal inference models or training scripts.
- Live connector or third-party provider integrations.
- Secret generation, credential storage, or production deployment declarations.
- Any remote Git operations (`git remote add`, `git push`, `git pull`, `git fetch`).
- Modifying any files under `docs/**` or `execution/**` (except standard executor completion report).

---

## Change boundary

### READ_SET

- `docs/04-system-architecture/REPOSITORY-TOPOLOGY.md`
- `docs/04-system-architecture/MODULE-BOUNDARIES.md`
- `docs/04-system-architecture/DEPENDENCY-RULES.md`
- `docs/31-adr/ADR-0001-application-architecture.md`
- `execution/FLASH-EXECUTOR-RULEBOOK.md`
- `execution/STAGE-B-PREFLIGHT-REPORT.md`
- `tasks/PHASE-00/TASK-BOOTSTRAP-001.md`

### WRITE_SET

- `.git/` (created via `git init`)
- `.gitignore`
- `.gitattributes`
- `.editorconfig`
- `pyproject.toml`
- `package.json`
- `config/examples/env.example`
- `tests/test_bootstrap_topology.py`
- `apps/api/.gitkeep`
- `apps/web/.gitkeep`
- `apps/workflow-worker/.gitkeep`
- `apps/ingestion-worker/.gitkeep`
- `apps/ml-worker/.gitkeep`
- `packages/backend/src/revpilot/shared/.gitkeep`
- `packages/backend/src/revpilot/modules/.gitkeep`
- `packages/backend/tests/.gitkeep`
- `packages/contracts/.gitkeep`
- `packages/web-client/.gitkeep`
- `tests/contract/.gitkeep`
- `tests/integration/.gitkeep`
- `tests/e2e/.gitkeep`
- `tests/security/.gitkeep`
- `tests/tenancy/.gitkeep`
- `tests/recovery/.gitkeep`
- `tests/performance/.gitkeep`
- `tests/ai-evals/.gitkeep`
- `config/schemas/.gitkeep`
- `infra/local/.gitkeep`
- `infra/environments/.gitkeep`
- `infra/policies/.gitkeep`
- `scripts/.gitkeep`
- `generated/.gitkeep`

### CREATE

All items in `WRITE_SET`.

### MODIFY

NONE.

### DO NOT MODIFY

- `docs/**` (all canonical specifications)
- `execution/**` (all control-plane tracking files)
- `tasks/**` (all task packets)
- `README.md`

### EXPECTED CHANGE SET

Exact file and directory layout created matching the canonical future repository topology without adding business code.

---

## Git authorization

LOCAL GIT INITIALIZATION AUTHORIZED: YES.

- Allowed command: `git init -b main` in `C:\Users\Duong Vinh\RevPilot AI`
- Initial commit allowed: YES, after all files in `WRITE_SET` are created and verification tests pass.
- Allowed commit command: `git add .` followed by `git commit -m "chore(scaffold): initialize canonical repository structure and toolchain baseline"`
- Remote configuration authorized: NO.
- Push authorized: NO.
- Branching authorized: NO (stay on initial default branch `main`).
- Modifying remote repository: PROHIBITED.

---

## Toolchain baseline

- **Runtime**: Python >= 3.12 (environment runtime: Python 3.14.4)
- **Frontend Runtime**: Node.js >= 20.0.0 (environment runtime: Node.js v26.5.1)
- **Package Manager (Python)**: `pip` + `pyproject.toml` standard build backend (`setuptools` or `hatchling`)
- **Package Manager (Node)**: `npm` >= 10.0.0 (environment runtime: npm 11.17.0)
- **Test Runner (Python)**: `pytest` >= 8.0.0 (installed: pytest 9.1.1)
- **Linter/Formatter (Python)**: Configured via `pyproject.toml` (target: `ruff` or standard flake8/black settings)
- **Typechecker (Python)**: Configured via `pyproject.toml` (target: `mypy` / standard typing)
- **Workspace Monorepo Structure**: Modular monolith with Python `packages/backend` and TypeScript `apps/web`

---

## Directory topology

Every directory created must match `docs/04-system-architecture/REPOSITORY-TOPOLOGY.md`:

| Directory | Purpose | Owner | Allowed Content | Prohibited Content |
|---|---|---|---|---|
| `apps/api/` | FastAPI composition and HTTP adapters | API Platform | App entrypoint, routing, dependency injection | Domain business rules, provider SDKs, direct table access |
| `apps/web/` | Next.js frontend Experience Plane | Experience | UI components, pages, web client consumer | Database credentials, raw CoT, enterprise secrets |
| `apps/workflow-worker/` | Temporal worker process composition | Execution | Workflow/activity worker registration | Business logic in worker memory, agent credentials |
| `apps/ingestion-worker/` | Connector data sync worker | Data Platform | Ingestion scheduling, connector ports | Business actions, cross-tenant unsanitized data |
| `apps/ml-worker/` | Offline ML/eval worker | ML Platform | ML/data evaluation job registration | Production promotion without gate |
| `packages/backend/src/revpilot/shared/` | Stable shared primitives & contracts | Backend Architecture | Opaque IDs, TenantContext, UTC time, Money | Business entities, repositories, provider SDKs |
| `packages/backend/src/revpilot/modules/` | Domain modules (16 bounded contexts) | Domain owners | Entities, ports, use cases, local adapters | Cross-module direct table mutation, provider secrets |
| `packages/backend/tests/` | Unit and module-level backend tests | Backend Architecture | Pytest unit/integration tests | Production secrets, live external endpoints |
| `packages/contracts/` | Versioned schemas (OpenAPI, JSON Schema) | Platform Contracts | Schema declarations | Business code, credentials |
| `packages/web-client/` | Generated API client for web | Experience/API | Generated client code | Hand-written business logic |
| `tests/contract/` | API and event contract tests | Platform Contracts | Contract compatibility tests | Live production targets |
| `tests/integration/` | Cross-module integration tests | Quality Owners | Port-based integration tests | Bypassing published ports |
| `tests/e2e/` | End-to-end workflow verification | Quality Owners | Simulated user/workflow journeys | Unmocked external destructive actions |
| `tests/security/` | Security, authz, taint, SSRF tests | Security Architecture | Adversarial suites, policy checks | Real production exploit targets |
| `tests/tenancy/` | Cross-tenant A/B negative matrix | Security/Tenancy | Tenant isolation negative tests | Sharing tenant data across tests |
| `tests/recovery/` | Temporal crash/replay & idempotency tests| SRE/Execution | Crash-at-step, idempotency tests | Uncontrolled state mutation |
| `tests/performance/` | Benchmark and latency tests | SRE/Platform | Synthetic load tests | Production target hammering |
| `tests/ai-evals/` | AI quality, RAG recall, RCA benchmarks | AI Governance | Hidden synthetic ground-truth suites | Leaking ground truth to runtime |
| `config/schemas/` | Non-secret configuration schemas | Platform | Validated config schemas | Credentials, production values |
| `config/examples/` | Safe environment placeholder examples | Platform | `env.example` with safe fakes | Real secrets, API keys, tokens |
| `infra/local/` | Local composition (docker-compose) | SRE/Platform | Local development service declarations| Production credentials |
| `infra/environments/` | Managed environment declarations | SRE/Platform | Declarative environment definitions | Hardcoded secrets |
| `infra/policies/` | Deployment and security policy rules | Security | Conftest/OPA policy rules | Dynamic bypasses |
| `scripts/` | Bounded developer and CI scripts | Developer Platform | Verification and build scripts | Destructive scripts without confirmation |
| `generated/` | Reproducible derived artifacts | Pipelines | Generated schemas, client code | Hand-edited source files |

---

## File specifications to create

### 1. `.gitignore`

Must ignore:
- Python: `__pycache__/`, `*.py[cod]`, `*$py.class`, `*.so`, `.Python`, `build/`, `develop-eggs/`, `dist/`, `downloads/`, `eggs/`, `.eggs/`, `lib/`, `lib64/`, `parts/`, `sdist/`, `var/`, `wheels/`, `*.egg-info/`, `.installed.cfg`, `*.egg`, `.env`, `.venv`, `env/`, `venv/`, `ENV/`
- Testing/Coverage: `.pytest_cache/`, `.coverage`, `htmlcov/`, `.mypy_cache/`, `.ruff_cache/`
- Node/Frontend: `node_modules/`, `npm-debug.log*`, `yarn-debug.log*`, `yarn-error.log*`, `.pnpm-debug.log*`, `.next/`, `out/`
- OS/Editor: `.DS_Store`, `Thumbs.db`, `*.swp`, `*.swo`, `.idea/`, `.vscode/` (except safe settings if approved)
- Secrets: `*.pem`, `*.key`, `*.cert`, `*.pfx`, `secrets/`, `*.local.env`, `.env.local`, `.env.production`
- Generated cache: `generated/cache/`

### 2. `.gitattributes`

Must declare:
- `* text=auto eol=lf`
- `*.py text eol=lf diff=python`
- `*.ts text eol=lf`
- `*.tsx text eol=lf`
- `*.json text eol=lf`
- `*.md text eol=lf`
- `*.sh text eol=lf`
- `*.ps1 text eol=crlf`
- `*.bat text eol=crlf`

### 3. `.editorconfig`

Must declare:
- `root = true`
- `[*]` charset = utf-8, end_of_line = lf, insert_final_newline = true, trim_trailing_whitespace = true
- `[*.py]` indent_style = space, indent_size = 4
- `[*.{js,jsx,ts,tsx,json,yml,yaml,md}]` indent_style = space, indent_size = 2
- `[*.{ps1,bat}]` end_of_line = crlf

### 4. `pyproject.toml`

Must declare:
```toml
[build-system]
requires = ["setuptools>=68.0.0"]
build-backend = "setuptools.build_meta"

[project]
name = "revpilot-backend"
version = "0.1.0"
description = "RevPilot AI — Modular Monolith Backend"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.110.0",
    "pydantic>=2.6.0",
    "pydantic-settings>=2.2.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "httpx>=0.27.0",
]

[tool.setuptools.packages.find]
where = ["packages/backend/src"]

[tool.pytest.ini_options]
minversion = "8.0"
testpaths = ["tests", "packages/backend/tests"]
python_files = ["test_*.py", "*_test.py"]
python_functions = ["test_*"]
asyncio_mode = "auto"

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.mypy]
python_version = "3.12"
strict = true
ignore_missing_imports = true
```

### 5. `package.json`

Must declare:
```json
{
  "name": "revpilot-ai",
  "version": "0.1.0",
  "private": true,
  "description": "RevPilot AI — Enterprise Revenue Intelligence & Action Platform",
  "scripts": {
    "test": "python -m pytest tests/",
    "lint:editor": "editorconfig-checker"
  },
  "workspaces": [
    "apps/*",
    "packages/*"
  ]
}
```

### 6. `config/examples/env.example`

Must declare non-secret placeholder variables:
```bash
# RevPilot AI Safe Development Environment Configuration
# Copy to local uncommitted environment file for development.
# NEVER commit real credentials, tokens, or production URLs.

REVPILOT_ENV=development
REVPILOT_LOG_LEVEL=info
REVPILOT_PORT=8000

# Primary Relational Persistence (ADR-0004, ADR-0005)
DATABASE_URL=postgresql://revpilot_app:placeholder_dev_pw@localhost:5432/revpilot_dev

# Temporal Durable Execution (ADR-0002)
TEMPORAL_HOST=localhost:7233
TEMPORAL_NAMESPACE=revpilot-dev

# Observability (ADR-0010)
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317

# Mock / Dry-run Action Safety (ADR-0009, INV-ACT-004)
ACTION_EXECUTION_MODE=dry_run
```

### 7. `tests/test_bootstrap_topology.py`

Must contain automated tests verifying:
- All required directories from `REPOSITORY-TOPOLOGY.md` exist on the filesystem.
- Python version is >= 3.12 (`sys.version_info >= (3, 12)`).
- `config/examples/env.example` exists and contains no forbidden secret patterns (no real API keys, no `sk-`, no `ghp_`, no `AKIA`).
- `pyproject.toml` exists and requires-python is `>=3.12`.

---

## Verification commands

The executor must run the following exact commands from `C:\Users\Duong Vinh\RevPilot AI`:

```powershell
# 1. Verify Git tracking initialized and clean status
git status

# 2. Run automated topology and environment validation suite
python -m pytest tests/test_bootstrap_topology.py -v

# 3. Verify git log shows the single authorized initial commit
git log -n 1 --oneline
```

Expected output:
- `git status` exits `0`, reports clean working directory on branch `main`.
- `pytest` exits `0`, all topology and scaffold tests pass.
- `git log` exits `0`, shows commit with subject matching `chore(scaffold): initialize canonical repository structure and toolchain baseline`.

---

## Binary acceptance criteria

- `AC-BOOTSTRAP-01`: PASS only if `.git` directory exists and `git status` exits code 0 with clean working tree.
- `AC-BOOTSTRAP-02`: PASS only if all 22 required topology directories exist under `apps/`, `packages/`, `tests/`, `config/`, `infra/`, `scripts/`, `generated/`.
- `AC-BOOTSTRAP-03`: PASS only if `.gitignore`, `.gitattributes`, and `.editorconfig` exist at workspace root with exact required sections.
- `AC-BOOTSTRAP-04`: PASS only if `pyproject.toml` and `package.json` exist at workspace root and declare valid metadata.
- `AC-BOOTSTRAP-05`: PASS only if `config/examples/env.example` exists and contains zero real secrets or production credentials.
- `AC-BOOTSTRAP-06`: PASS only if `python -m pytest tests/test_bootstrap_topology.py` executes and exits code 0 with all test cases passing.
- `AC-BOOTSTRAP-07`: PASS only if exactly one git commit exists on `main` with authorized message.
- `AC-BOOTSTRAP-08`: PASS only if zero application business logic, domain models, database migrations, or external network adapters were created.

---

## Postconditions

1. Workspace contains tracked source/toolchain skeleton.
2. `git status` is clean.
3. Automated test suite runs and passes via standard `pytest`.
4. Rail 0 is eligible for promotion from `AMBER` to `GREEN` upon verification of executor success report.

---

## Readiness score

| Dimension | Score (0–2) | Rationale |
|---|---:|---|
| Objective clarity | 2 | Single bounded outcome: initialize scaffold, manifests, git baseline, and test. |
| Dependency clarity | 2 | Dependencies resolved (`SPEC-P00-E05` PASS; local runtimes verified). |
| File boundary clarity | 2 | Exact list of 31 file paths in `WRITE_SET`; exact prohibited paths listed. |
| Contract clarity | 2 | Exact schemas for manifests, env example, and topology test provided verbatim. |
| Failure behavior | 2 | Failure stops task; git remains clean; failure modes defined. |
| Security/tenancy | 2 | No secrets; dry-run default; no tenant data access; safe fakes only. |
| Testability | 2 | Automated `pytest` suite included in write set; exact non-destructive command. |
| Verification | 2 | Exact commands, exit codes, and output requirements specified. |
| Acceptance criteria | 2 | 8 binary PASS/FAIL criteria defined with machine-verifiable conditions. |
| Reasoning independence | 2 | Executor requires zero architectural, framework, or directory choices. |
| **TOTAL** | **20/20** | **Ready for Queue Admission** |

---

## Definition of done

All 8 acceptance criteria pass; `git status` clean; `python -m pytest tests/test_bootstrap_topology.py` exits 0; no prohibited files modified; executor success report delivered matching `execution/MICRO-TASK-RAIL-SYSTEM.md#executor-success-report`.

---

## Do not

- Do not implement application business logic.
- Do not create routes, schemas, models, or workers.
- Do not configure a remote Git repository or push.
- Do not install unauthorized packages or alter installed runtimes.
- Do not modify any file under `docs/**` or `execution/**`.

---

## Required executor report

Use the exact format specified in `execution/FLASH-EXECUTOR-RULEBOOK.md` §7.
