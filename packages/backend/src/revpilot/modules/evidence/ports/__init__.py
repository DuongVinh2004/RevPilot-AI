"""
RevPilot AI — Evidence Ports Submodule
Authoritative repository protocols and persistence adapters.
"""

from revpilot.modules.evidence.ports.repository import (
    EvidenceRepositoryPort,
    InMemoryEvidenceRepository,
)

__all__ = [
    "EvidenceRepositoryPort",
    "InMemoryEvidenceRepository",
]
