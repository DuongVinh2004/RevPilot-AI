"""
RevPilot AI — Benchmark Manifest & Verification Contracts (Phase 01)
Conforms to SYNTHETIC-DATASET-SPEC.md §3.2 and TASK-P01-003.
"""

from __future__ import annotations
import json
from dataclasses import dataclass, field
from typing import Any

from revpilot.shared.errors import DomainError


class ConfigValidationError(DomainError):
    """Raised when generator configuration is invalid or missing required values."""

    def __init__(self, message: str = "Invalid generator configuration", details: dict[str, Any] | None = None) -> None:
        super().__init__(code="CONFIG_VALIDATION_ERROR", message=message, details=details, retryable=False)


class NonDeterministicDriftError(DomainError):
    """Raised when generation with identical seed yields divergent artifact hashes."""

    def __init__(self, message: str = "Generator output drifted", details: dict[str, Any] | None = None) -> None:
        super().__init__(code="NON_DETERMINISTIC_DRIFT", message=message, details=details, retryable=False)


class BenchmarkVerificationFailureError(DomainError):
    """Raised when generated dataset verification against manifest fails."""

    def __init__(self, message: str = "Benchmark verification failed", details: dict[str, Any] | None = None) -> None:
        super().__init__(code="BENCHMARK_VERIFICATION_FAILURE", message=message, details=details, retryable=False)


@dataclass(frozen=True, slots=True)
class BenchmarkManifest:
    """
    Cryptographically verifiable manifest schema for synthetic benchmark runs.
    Conforms to SYNTHETIC-DATASET-SPEC.md §3.2.
    """
    manifest_id: str
    profile: str
    seed: int
    generated_at_utc: str
    scenario_window: dict[str, str]
    tenants: list[str]
    entity_counts: dict[str, int]
    artifact_hashes: dict[str, str]
    generator_version: str = "1.0.0"
    schema_version: str = "1.0.0"
    scenario_version: str = "1.0.0"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "$schema": "https://revpilot.ai/schemas/benchmark-manifest.v1.json",
            "manifest_id": self.manifest_id,
            "generator_version": self.generator_version,
            "schema_version": self.schema_version,
            "scenario_version": self.scenario_version,
            "profile": self.profile,
            "seed": self.seed,
            "generated_at_utc": self.generated_at_utc,
            "scenario_window": self.scenario_window,
            "tenants": self.tenants,
            "entity_counts": self.entity_counts,
            "artifact_hashes": self.artifact_hashes,
            "metadata": self.metadata,
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BenchmarkManifest:
        d = dict(data)
        d.pop("$schema", None)
        return cls(**d)

    @classmethod
    def from_json(cls, json_str: str) -> BenchmarkManifest:
        data = json.loads(json_str)
        return cls.from_dict(data)


__all__ = [
    "ConfigValidationError",
    "NonDeterministicDriftError",
    "BenchmarkVerificationFailureError",
    "BenchmarkManifest",
]
