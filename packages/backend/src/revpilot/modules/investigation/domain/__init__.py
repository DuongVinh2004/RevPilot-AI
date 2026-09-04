"""
RevPilot AI — Investigation Domain Module
Exports entities, value objects, manifest models, lifecycle state machine, and errors.
"""

from revpilot.modules.investigation.domain.errors import (
    InvestigationDomainError,
    InvalidStateTransitionError,
    BudgetExceededError,
    TemporalValidationException,
)
from revpilot.modules.investigation.domain.models import (
    InvestigationStatus,
    BudgetState,
    InvestigationScope,
    Investigation,
    InvestigationManifest,
)
from revpilot.modules.investigation.domain.state_machine import (
    transition_investigation_state,
)

__all__ = [
    "InvestigationDomainError",
    "InvalidStateTransitionError",
    "BudgetExceededError",
    "TemporalValidationException",
    "InvestigationStatus",
    "BudgetState",
    "InvestigationScope",
    "Investigation",
    "InvestigationManifest",
    "transition_investigation_state",
]
