"""
RevPilot AI — Schema Drift Classifier
Specification: docs/17-connectors/CONNECTOR-PLATFORM-SPEC.md §5
Conforms to INV-DATA-002, INV-REL-001, and TC-P07-021.
"""

from __future__ import annotations

from enum import Enum
from typing import Any
from pydantic import BaseModel, ConfigDict

from revpilot.shared.identifiers import UUIDv7


class DriftClassification(str, Enum):
    COMPATIBLE = "COMPATIBLE"
    BENIGN = "BENIGN"
    BREAKING = "BREAKING"


class DriftEvaluationResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    connector_id: UUIDv7
    classification: DriftClassification
    reasons: list[str]
    missing_fields: list[str]
    type_mismatches: list[str]
    extra_fields: list[str]


class SchemaDriftClassifier:
    """
    Classifies payload compatibility against canonical schema definitions.
    Strictly flags missing mandatory fields or semantic type collisions as BREAKING,
    while permitting non-destructive additive attributes as BENIGN.
    """

    def evaluate_payload(
        self,
        connector_id: UUIDv7,
        payload: dict[str, Any],
        expected_schema: dict[str, Any],
    ) -> DriftEvaluationResult:
        """
        Evaluate incoming event against expected schema.
        Expected schema format:
        {
            "required_fields": {"field_name": (type, ...)},
            "optional_fields": {"field_name": (type, ...)}
        }
        """
        req_specs = expected_schema.get("required_fields", {})
        opt_specs = expected_schema.get("optional_fields", {})

        missing_fields: list[str] = []
        type_mismatches: list[str] = []
        reasons: list[str] = []

        # 1. Verify Required Fields & Types
        for field_name, expected_type in req_specs.items():
            if field_name not in payload:
                missing_fields.append(field_name)
                reasons.append(f"Missing mandatory field '{field_name}'")
                continue

            val = payload[field_name]
            if val is None:
                missing_fields.append(field_name)
                reasons.append(f"Mandatory field '{field_name}' is None")
                continue

            # Check expected type
            types_tuple = expected_type if isinstance(expected_type, tuple) else (expected_type,)
            if not isinstance(val, types_tuple):
                mismatch_msg = f"Field '{field_name}' type mismatch: expected {types_tuple}, got {type(val).__name__}"
                type_mismatches.append(mismatch_msg)
                reasons.append(mismatch_msg)

        # 2. Verify Optional Field Types if present
        for field_name, expected_type in opt_specs.items():
            if field_name in payload and payload[field_name] is not None:
                val = payload[field_name]
                types_tuple = expected_type if isinstance(expected_type, tuple) else (expected_type,)
                if not isinstance(val, types_tuple):
                    mismatch_msg = f"Optional field '{field_name}' type mismatch: expected {types_tuple}, got {type(val).__name__}"
                    type_mismatches.append(mismatch_msg)
                    reasons.append(mismatch_msg)

        # 3. Detect Additive (Extra) Fields
        all_expected = set(req_specs.keys()) | set(opt_specs.keys())
        extra_fields = [k for k in payload if k not in all_expected]

        # 4. Determine Classification
        if missing_fields or type_mismatches:
            classification = DriftClassification.BREAKING
        elif extra_fields:
            classification = DriftClassification.BENIGN
            reasons.append(f"Additive fields detected: {sorted(extra_fields)}")
        else:
            classification = DriftClassification.COMPATIBLE

        return DriftEvaluationResult(
            connector_id=connector_id,
            classification=classification,
            reasons=reasons,
            missing_fields=missing_fields,
            type_mismatches=type_mismatches,
            extra_fields=extra_fields,
        )
