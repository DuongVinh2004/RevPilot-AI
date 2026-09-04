"""
RevPilot AI — Benchmark Module (Phase 01)
Public exports for synthetic dataset generation, manifest contracts, and profiles.
Conforms to SYNTHETIC-DATASET-SPEC.md and TASK-P01-003.
"""

from revpilot.modules.benchmark.manifest import (
    BenchmarkManifest,
    ConfigValidationError,
    NonDeterministicDriftError,
    BenchmarkVerificationFailureError,
)
from revpilot.modules.benchmark.generator import (
    DatasetProfile,
    GeneratorConfig,
    GeneratedDatasetBundle,
    SyntheticDataGenerator,
)
from revpilot.modules.benchmark.ground_truth import (
    AccessDeniedError,
    ScenarioInjectionError,
    EvaluatorAuthToken,
    GroundTruthIncident,
    EvaluationGroundTruthStore,
)
from revpilot.modules.benchmark.scenarios import (
    TruckCapacityScenarioInjector,
)

__all__ = [
    "BenchmarkManifest",
    "ConfigValidationError",
    "NonDeterministicDriftError",
    "BenchmarkVerificationFailureError",
    "DatasetProfile",
    "GeneratorConfig",
    "GeneratedDatasetBundle",
    "SyntheticDataGenerator",
    "AccessDeniedError",
    "ScenarioInjectionError",
    "EvaluatorAuthToken",
    "GroundTruthIncident",
    "EvaluationGroundTruthStore",
    "TruckCapacityScenarioInjector",
]
