"""
RevPilot AI — Kill Switch Safety Module
"""

from revpilot.modules.safety.killswitch.domain import (
    KillSwitchScope,
    KillSwitchRecord,
    KillSwitchError,
    KillSwitchActiveError,
    AgentOverrideForbiddenError,
)
from revpilot.modules.safety.killswitch.service import (
    KillSwitchService,
    DistributedKillSwitchBus,
)

__all__ = [
    "KillSwitchScope",
    "KillSwitchRecord",
    "KillSwitchError",
    "KillSwitchActiveError",
    "AgentOverrideForbiddenError",
    "KillSwitchService",
    "DistributedKillSwitchBus",
]
