"""
RevPilot AI — Analytics SQL Capability Module
Authoritative exports for registered SQL capabilities, templates, and execution engine.
Conforms to SQL-CAPABILITY-CATALOG.md, INV-TEN-001..003, INV-DATA-001, and INV-ACT-001.
"""

from revpilot.modules.analytics.capabilities.catalog import (
    SqlCapabilityDefinition,
    REGISTERED_SQL_CAPABILITIES,
    get_capability,
)
from revpilot.modules.analytics.capabilities.templates import (
    canonicalize_query_digest,
    build_sql_for_capability,
    detect_prohibited_sql,
)
from revpilot.modules.analytics.capabilities.executor import (
    CapabilityError,
    CapabilityRequest,
    CapabilityResult,
    SqlCapabilityExecutor,
)

__all__ = [
    "SqlCapabilityDefinition",
    "REGISTERED_SQL_CAPABILITIES",
    "get_capability",
    "canonicalize_query_digest",
    "build_sql_for_capability",
    "detect_prohibited_sql",
    "CapabilityError",
    "CapabilityRequest",
    "CapabilityResult",
    "SqlCapabilityExecutor",
]
