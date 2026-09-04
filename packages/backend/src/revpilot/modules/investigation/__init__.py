"""
RevPilot AI — Investigation Module (Phase 03)
Provides governed investigation workflows, typed DAGs, evidence collection, and multi-agent synthesis.
"""

from revpilot.modules.investigation.domain import (
    Investigation,
    InvestigationStatus,
    InvestigationScope,
    InvestigationManifest,
    BudgetState,
    transition_investigation_state,
    InvestigationDomainError,
    InvalidStateTransitionError,
    BudgetExceededError,
    TemporalValidationException,
)
from revpilot.modules.investigation.ports import InvestigationRepository

__all__ = [
    "Investigation",
    "InvestigationStatus",
    "InvestigationScope",
    "InvestigationManifest",
    "BudgetState",
    "transition_investigation_state",
    "InvestigationDomainError",
    "InvalidStateTransitionError",
    "BudgetExceededError",
    "TemporalValidationException",
    "InvestigationRepository",
]
