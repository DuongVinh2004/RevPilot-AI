"""
RevPilot AI — SCIM 2.0 Automated Lifecycle Provisioning Submodule
Public exports for SCIM 2.0 user/group management and rapid session revocation.
Conforms to docs/14-iam/ENTERPRISE-IDENTITY-INTEGRATION-SPEC.md §4.
"""

from revpilot.modules.iam.scim.service import (
    ScimUserRecord,
    ScimGroupRecord,
    ScimProvisioningService,
    ScimError,
    ScimConflictError,
    ScimUserNotFoundError,
)
from revpilot.modules.iam.scim.endpoints import (
    ScimEndpoints,
)

__all__ = [
    "ScimUserRecord",
    "ScimGroupRecord",
    "ScimProvisioningService",
    "ScimError",
    "ScimConflictError",
    "ScimUserNotFoundError",
    "ScimEndpoints",
]
