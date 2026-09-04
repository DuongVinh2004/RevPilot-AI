"""
Unit tests for MigrationSafetyValidator.
Validates AC-R05-003-01, AC-R05-003-02, AC-R05-003-03, and expand/contract rules.
"""

from __future__ import annotations
import pytest

from revpilot.shared.errors import ValidationError
from revpilot.shared.migration import MigrationSafetyValidator


class TestMigrationSafetyValidator:
    def test_drop_column_rejected(self) -> None:
        ddl = "ALTER TABLE tenants DROP COLUMN obsolete_field;"
        with pytest.raises(ValidationError) as exc_info:
            MigrationSafetyValidator.validate_ddl(ddl)
        assert "Destructive column drop prohibited without deprecation release" in str(exc_info.value)

    def test_rename_column_rejected(self) -> None:
        ddl = "ALTER TABLE metrics RENAME COLUMN val TO amount;"
        with pytest.raises(ValidationError) as exc_info:
            MigrationSafetyValidator.validate_ddl(ddl)
        assert "Direct column rename prohibited; use expand/contract dual writing" in str(exc_info.value)

    def test_drop_table_rejected(self) -> None:
        ddl = "DROP TABLE deprecated_events;"
        with pytest.raises(ValidationError) as exc_info:
            MigrationSafetyValidator.validate_ddl(ddl)
        assert "Dropping table prohibited without authorization" in str(exc_info.value)

    def test_add_not_null_without_default_rejected(self) -> None:
        ddl = "ALTER TABLE users ADD COLUMN status VARCHAR(32) NOT NULL;"
        with pytest.raises(ValidationError) as exc_info:
            MigrationSafetyValidator.validate_ddl(ddl)
        assert "Adding NOT NULL column without DEFAULT is prohibited" in str(exc_info.value)

    def test_add_not_null_with_default_allowed(self) -> None:
        ddl = "ALTER TABLE users ADD COLUMN status VARCHAR(32) NOT NULL DEFAULT 'active';"
        # Must not raise
        MigrationSafetyValidator.validate_ddl(ddl)

    def test_add_nullable_column_allowed(self) -> None:
        ddl = "ALTER TABLE tenants ADD COLUMN notes TEXT;"
        MigrationSafetyValidator.validate_ddl(ddl)

    def test_create_table_allowed(self) -> None:
        ddl = """
        CREATE TABLE tenant_configs (
            id UUID PRIMARY KEY,
            tenant_id VARCHAR(64) NOT NULL,
            config_data JSONB NOT NULL DEFAULT '{}'::jsonb
        );
        """
        MigrationSafetyValidator.validate_ddl(ddl)

    def test_empty_statement_raises_validation_error(self) -> None:
        with pytest.raises(ValidationError):
            MigrationSafetyValidator.validate_ddl("")
        with pytest.raises(ValidationError):
            MigrationSafetyValidator.validate_ddl(None)  # type: ignore[arg-type]
