"""
RevPilot AI — Platform Safety and Containment Module
"""

from revpilot.modules.safety.blast_radius import (
    BlastRadiusLimiter,
    BlastRadiusExceededError,
    MAX_AFFECTED_ENTITIES,
    TIER_SPEND_CEILINGS,
)
from revpilot.modules.safety.killswitch import (
    KillSwitchScope,
    KillSwitchRecord,
    KillSwitchError,
    KillSwitchActiveError,
    AgentOverrideForbiddenError,
    KillSwitchService,
    DistributedKillSwitchBus,
)

__all__ = [
    "BlastRadiusLimiter",
    "BlastRadiusExceededError",
    "MAX_AFFECTED_ENTITIES",
    "TIER_SPEND_CEILINGS",
    "KillSwitchScope",
    "KillSwitchRecord",
    "KillSwitchError",
    "KillSwitchActiveError",
    "AgentOverrideForbiddenError",
    "KillSwitchService",
    "DistributedKillSwitchBus",
]
