# Contributing to RevPilot AI

Thank you for your interest in contributing to RevPilot AI!

RevPilot AI operates under rigorous enterprise architectural invariants, fail-closed safety governance, and strict anti-fabrication standards. Please read this guide before submitting contributions.

---

## 1. Architectural Invariants & Governance

All contributions must strictly adhere to the repository's core invariants:
- **Fail-Closed Execution**: If an action, policy, or tenant context is ambiguous or invalid, the system must fail closed.
- **Strict Multi-Tenancy (INV-TEN-001)**: No cross-tenant data leakage in persistence, caches, or LLM context.
- **Zero Agent Self-Approval (INV-ACT-003)**: Autonomous agents cannot approve their own mutations. Human approval tokens are mandatory for risk tiers 1–3.
- **Anti-Fabrication Invariant (AC-014)**: Never mock or fabricate benchmark metrics or test outputs. A measured result exists exclusively when recorded by an automated execution run with verifiable machine logs.
- See [AGENTS.md](AGENTS.md) and [docs/03-requirements/INVARIANT-REGISTRY.md](docs/03-requirements/INVARIANT-REGISTRY.md) for the full registry.

---

## 2. Development Setup

### Prerequisites
- **Python**: >= 3.12
- **Node.js**: >= 20.0
- **Docker & Docker Compose**: v2+
- **Git**

### Local Environment Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/DuongVinh2004/RevPilot-AI.git
   cd RevPilot-AI
   ```

2. **Set up Python Virtual Environment**:
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux/macOS:
   source .venv/bin/activate

   pip install -e ".[dev]"
   ```

3. **Set up Frontend Dependencies**:
   ```bash
   cd apps/web
   npm install
   cd ../..
   ```

4. **Launch Infrastructure with Docker Compose**:
   ```bash
   docker compose up -d postgres redis temporal
   ```

---

## 3. Running Tests & Linters

Always verify tests and formatting before creating a pull request:

```bash
# Run backend test suite (550+ tests)
python -m pytest tests/ -v

# Run type checker
mypy packages/backend/src

# Run code linter
ruff check .
```

---

## 4. Commit Message Guidelines

We enforce **Conventional Commits**:
- `feat:` A new feature or capability
- `fix:` A bug fix
- `docs:` Documentation-only changes
- `test:` Adding or updating tests
- `refactor:` Code change that neither fixes a bug nor adds a feature
- `chore:` Changes to build process, dependencies, or auxiliary tools

Example:
```bash
git commit -m "feat(verifier): add claim grounding verification rules"
```

---

## 5. Pull Request Process

1. Fork the repository and create your branch from `main`:
   ```bash
   git checkout -b feat/your-feature-name
   ```
2. Implement your changes following existing code style and typing rules.
3. Ensure all automated tests pass (`python -m pytest tests/`).
4. Add unit / integration tests covering new functionality.
5. Submit a Pull Request targeting `main`. Fill out the [Pull Request Template](.github/PULL_REQUEST_TEMPLATE.md).
