"""
RevPilot AI — Schema Migration Safety Validator
Enforces zero-downtime expand/contract schema evolution and prevents destructive DDL.
Conforms to ADR-0004, ADR-0005, and DATABASE-SCHEMA.md §8.
"""

from __future__ import annotations
import re
from revpilot.shared.errors import ValidationError


class MigrationSafetyValidator:
    """
    Validates SQL DDL statements against expand/contract schema evolution rules.
    Rejects destructive migrations such as direct column drops, column renames,
    table drops, and adding NOT NULL columns without DEFAULT values.
    """

    _DROP_COLUMN_REGEX = re.compile(r"\bDROP\s+COLUMN\b", re.IGNORECASE)
    _RENAME_COLUMN_REGEX = re.compile(r"\bRENAME\s+COLUMN\b", re.IGNORECASE)
    _DROP_TABLE_REGEX = re.compile(r"\bDROP\s+TABLE\b", re.IGNORECASE)
    _ADD_NOT_NULL_REGEX = re.compile(
        r"\bADD\s+(?:COLUMN\s+)?[a-zA-Z0-9_]+\s+[^;]*\bNOT\s+NULL\b",
        re.IGNORECASE,
    )
    _DEFAULT_REGEX = re.compile(r"\bDEFAULT\b", re.IGNORECASE)

    @classmethod
    def validate_ddl(cls, ddl_statement: str) -> None:
        """
        Validate single or multi-statement DDL string.
        Raises ValidationError with specific client message on prohibited operations.
        """
        if not ddl_statement or not isinstance(ddl_statement, str):
            raise ValidationError("DDL statement must be a non-empty string.")

        stmt = ddl_statement.strip()

        if cls._DROP_COLUMN_REGEX.search(stmt):
            raise ValidationError("Destructive column drop prohibited without deprecation release")

        if cls._RENAME_COLUMN_REGEX.search(stmt):
            raise ValidationError("Direct column rename prohibited; use expand/contract dual writing")

        if cls._DROP_TABLE_REGEX.search(stmt):
            raise ValidationError("Dropping table prohibited without authorization")

        if cls._ADD_NOT_NULL_REGEX.search(stmt) and not cls._DEFAULT_REGEX.search(stmt):
            raise ValidationError("Adding NOT NULL column without DEFAULT is prohibited")
