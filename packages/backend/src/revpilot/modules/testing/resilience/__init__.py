"""
RevPilot AI — Resilience & Chaos Testing Module
Public domain models, harness, and fault injection primitives.
"""

from revpilot.modules.testing.resilience.fault_injector import FaultInjector
from revpilot.modules.testing.resilience.harness import (
    BenchmarkResult,
    BenchmarkSloBreachError,
    IsolationLeakUnderLoadError,
    KillSwitchLagExceededError,
    ResilienceTestHarness,
)

__all__ = [
    "FaultInjector",
    "BenchmarkResult",
    "BenchmarkSloBreachError",
    "KillSwitchLagExceededError",
    "IsolationLeakUnderLoadError",
    "ResilienceTestHarness",
]
