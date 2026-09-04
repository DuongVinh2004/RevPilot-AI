"""
RevPilot AI — Data Quality Rules and Validation Contracts (Phase 01)
Adheres to docs/07-data-platform/DATA-QUALITY-LINEAGE-SPEC.md §3 and INV-DATA-002.
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class RuleSeverity(str, Enum):
    """Severity levels for data quality rule violations."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


# Canonical Rule IDs
DQ_SCH_001 = "DQ-SCH-001"  # Schema Validation
DQ_REQ_001 = "DQ-REQ-001"  # Required Non-Null Field Check
DQ_TYP_001 = "DQ-TYP-001"  # Type and Numeric Range Check
DQ_REF_001 = "DQ-REF-001"  # Cross-Entity Referential Integrity
DQ_TEN_001 = "DQ-TEN-001"  # Tenant Ownership Validation
DQ_DUP_001 = "DQ-DUP-001"  # Idempotent Duplicate Detection
DQ_ORD_001 = "DQ-ORD-001"  # Event Ordering and Timestamp Sanity
DQ_CUR_001 = "DQ-CUR-001"  # Currency Code Consistency


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Result of evaluating a record against data quality rules."""
    is_valid: bool
    rule_id: Optional[str] = None
    error_code: Optional[str] = None
    rejection_reason: Optional[str] = None

    @classmethod
    def success(cls) -> ValidationResult:
        return cls(is_valid=True)

    @classmethod
    def failure(
        cls,
        rule_id: str,
        error_code: str,
        rejection_reason: str,
    ) -> ValidationResult:
        return cls(
            is_valid=False,
            rule_id=rule_id,
            error_code=error_code,
            rejection_reason=rejection_reason,
        )


__all__ = [
    "RuleSeverity",
    "ValidationResult",
    "DQ_SCH_001",
    "DQ_REQ_001",
    "DQ_TYP_001",
    "DQ_REF_001",
    "DQ_TEN_001",
    "DQ_DUP_001",
    "DQ_ORD_001",
    "DQ_CUR_001",
]
