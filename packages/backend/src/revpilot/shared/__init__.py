"""
RevPilot AI — Shared Kernel Package
Authoritative public exports of core domain primitives, value objects, error hierarchy, results, and context.
Conforms to REPOSITORY-TOPOLOGY.md §shared-kernel-limits.
"""

from revpilot.shared.identifiers import (
    EntityId,
    TenantId,
    PrincipalId,
    OrganizationId,
    InvestigationId,
    EvidenceId,
    ActionId,
    ApprovalId,
)
from revpilot.shared.temporal import UtcDateTime, TimeWindow
from revpilot.shared.monetary import Currency, Money
from revpilot.shared.errors import (
    DomainError,
    NotFoundError,
    ValidationError,
    ConflictError,
    AuthorizationError,
    AuthenticationError,
    TenancyViolationError,
    ConcurrencyError,
    RateLimitExceededError,
)
from revpilot.shared.results import Result, Success, Failure
from revpilot.shared.correlation import CorrelationContext
from revpilot.shared.context import TenantContext, PrincipalContext, SecurityContext

__all__ = [
    # Identifiers
    "EntityId",
    "TenantId",
    "PrincipalId",
    "OrganizationId",
    "InvestigationId",
    "EvidenceId",
    "ActionId",
    "ApprovalId",
    # Temporal
    "UtcDateTime",
    "TimeWindow",
    # Monetary
    "Currency",
    "Money",
    # Errors
    "DomainError",
    "NotFoundError",
    "ValidationError",
    "ConflictError",
    "AuthorizationError",
    "AuthenticationError",
    "TenancyViolationError",
    "ConcurrencyError",
    "RateLimitExceededError",
    # Results
    "Result",
    "Success",
    "Failure",
    # Correlation
    "CorrelationContext",
    # Context
    "TenantContext",
    "PrincipalContext",
    "SecurityContext",
]
