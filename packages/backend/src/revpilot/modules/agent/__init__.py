"""
RevPilot AI — Agent Platform Module
Conforms to docs/06-agent-platform/MULTI-AGENT-SPEC.md §1–§7, ADR-0003, and TASK-P03-006.
Exports typed agent planner, DAG validation engine, hypothesis synthesizer, and verifier.
"""

from revpilot.modules.agent.dag_validator import (
    DagValidationError,
    validate_investigation_dag,
)
from revpilot.modules.agent.planner import (
    AgentTask,
    InvestigationPlanner,
    Plan,
    PlannerError,
    TaskType,
)
from revpilot.modules.agent.synthesizer import (
    Hypothesis,
    HypothesisSynthesizer,
    SynthesizerError,
)
from revpilot.modules.agent.verifier import (
    InvestigationVerifier,
    VerificationResult,
    VerificationStatus,
)

__all__ = [
    "AgentTask",
    "DagValidationError",
    "Hypothesis",
    "HypothesisSynthesizer",
    "InvestigationPlanner",
    "InvestigationVerifier",
    "Plan",
    "PlannerError",
    "SynthesizerError",
    "TaskType",
    "VerificationResult",
    "VerificationStatus",
    "validate_investigation_dag",
]
