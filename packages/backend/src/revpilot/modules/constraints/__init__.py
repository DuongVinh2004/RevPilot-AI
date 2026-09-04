"""
RevPilot AI — Hard Business Constraints and Budget Ledger Module
Specification: docs/11-decision-intelligence/BUDGET-CONSTRAINT-SPEC.md
Specification: docs/11-decision-intelligence/DECISION-ENGINE-SPEC.md §1.1, §2 Step 4–7
Conforms to BR-005, FR-DEC-001, INV-COST-001, INV-TEN-001..003, and AC-007.
"""

from revpilot.modules.constraints.domain import (
    CandidateIntervention,
    BudgetLedgerEntry,
    ConstraintEvaluatorRequest,
    ConstraintEvaluationOutcome,
    ConstraintViolationError,
)
from revpilot.modules.constraints.evaluator import (
    evaluate_hard_constraints,
    filter_eligible_candidates,
)
from revpilot.modules.constraints.ports import (
    BudgetLedgerRepository,
    InMemoryBudgetLedgerRepository,
)

__all__ = [
    # Domain Models
    "CandidateIntervention",
    "BudgetLedgerEntry",
    "ConstraintEvaluatorRequest",
    "ConstraintEvaluationOutcome",
    "ConstraintViolationError",
    # Evaluator Engine
    "evaluate_hard_constraints",
    "filter_eligible_candidates",
    # Ports & Adapters
    "BudgetLedgerRepository",
    "InMemoryBudgetLedgerRepository",
]
