"""
RevPilot AI — Safety Kill Switch Domain Contracts
Specification: docs/16-tool-gateway/APPROVAL-ACTION-LOOP-SPEC.md §5
Specification: docs/16-tool-gateway/TOOL-GATEWAY-SPEC.md §7.4
Conforms to INV-REL-001, INV-ACT-003, and NFR-COST-001.
"""

from __future__ import annotations
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field

from revpilot.shared.identifiers import UUIDv7
from revpilot.shared.temporal import UtcDateTime
from revpilot.shared.errors import DomainError


class KillSwitchScope(str, Enum):
    """
    Multi-tier operational scope for safety kill switches.
    """
    GLOBAL = "GLOBAL"
    TENANT = "TENANT"
    CAPABILITY = "CAPABILITY"
    PROVIDER = "PROVIDER"
    INVESTIGATION = "INVESTIGATION"


class KillSwitchError(DomainError):
    """Base exception for kill switch operations."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(code="ERR_KILL_SWITCH_ERROR", message=message, details=details, retryable=False)


class KillSwitchActiveError(DomainError):
    """Execution aborted due to active safety kill switch."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(code="ERR_KILL_SWITCH_ACTIVE", message=message, details=details, retryable=False)


class AgentOverrideForbiddenError(DomainError):
    """AI agents are strictly forbidden from modifying or bypassing kill switches (INV-ACT-003)."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(code="ERR_AGENT_OVERRIDE_FORBIDDEN", message=message, details=details, retryable=False)


class KillSwitchRecord(BaseModel):
    """
    Authoritative state record for an operational kill switch.
    """
    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    switch_id: UUIDv7
    scope: KillSwitchScope
    target_id: Optional[str] = None
    is_active: bool = True
    reason: str = Field(min_length=1)
    activated_by: str = Field(min_length=1)
    activated_at: UtcDateTime
    deactivated_by: Optional[str] = None
    deactivated_at: Optional[UtcDateTime] = None
