"""
RevPilot AI — Governed SQL Capability Executor
Specification: docs/06-agent-platform/SQL-CAPABILITY-CATALOG.md §4, §5
Enforces deny-by-default execution, anti-leakage, statement timeouts, and budget guards.
"""

from __future__ import annotations
import asyncio
import inspect
import time
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from revpilot.shared.context import TenantContext, PrincipalContext
from revpilot.shared.errors import DomainError
from revpilot.shared.results import Result, Success, Failure
from revpilot.shared.temporal import UtcDateTime
from revpilot.modules.analytics.capabilities.catalog import (
    SqlCapabilityDefinition,
    REGISTERED_SQL_CAPABILITIES,
    get_capability,
)
from revpilot.modules.analytics.capabilities.templates import (
    build_sql_for_capability,
    canonicalize_query_digest,
    detect_prohibited_sql,
)


class CapabilityError(DomainError):
    """Domain error raised or returned during SQL capability execution."""

    def __init__(
        self,
        code: str,
        message: str,
        http_status: int = 400,
        details: dict[str, Any] | None = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(code=code, message=message, details=details, retryable=retryable)
        self.http_status = http_status


@dataclass(frozen=True, slots=True)
class CapabilityRequest:
    """Input payload requesting execution of a registered SQL analytical capability."""

    capability_id: str
    tenant_context: TenantContext
    principal_context: PrincipalContext
    investigation_id: Any
    as_of_time: UtcDateTime | str
    parameters: dict[str, Any] = field(default_factory=dict)
    budget_remaining_usd: Decimal = Decimal("2.00")


@dataclass(frozen=True, slots=True)
class CapabilityResult:
    """Output envelope returned from SQL capability execution."""

    capability_id: str
    rows: list[dict[str, Any]]
    row_count: int
    execution_time_ms: float
    query_digest: str
    cost_usd: Decimal
    is_truncated: bool = False
    status: str = "SUCCESS"
    error_code: str | None = None
    error_message: str | None = None


def _normalize_utc_string(val: Any) -> str:
    """Normalize UtcDateTime, string, or datetime to ISO string."""
    if isinstance(val, UtcDateTime):
        return val.isoformat()
    if hasattr(val, "isoformat"):
        return val.isoformat()
    return str(val)


def _execute_raw_sql(db_session: Any, sql: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    """Execute SQL query against connection or session synchronously and return row dicts."""
    # Check if session is a DB-API connection (e.g. sqlite3)
    if hasattr(db_session, "cursor"):
        cursor = db_session.cursor()
        try:
            cursor.execute(sql, params)
            col_names = [d[0] for d in cursor.description] if cursor.description else []
            rows = cursor.fetchall()
            result: list[dict[str, Any]] = []
            for r in rows:
                if isinstance(r, dict):
                    result.append(r)
                elif hasattr(r, "keys"):
                    result.append(dict(r))
                else:
                    result.append(dict(zip(col_names, r)))
            return result
        finally:
            if hasattr(cursor, "close"):
                cursor.close()

    # Check for execute method (e.g. SQLAlchemy connection / session)
    if hasattr(db_session, "execute"):
        res = db_session.execute(sql, params)
        if hasattr(res, "mappings"):
            return [dict(m) for m in res.mappings().all()]
        if hasattr(res, "fetchall"):
            rows = res.fetchall()
            col_names = list(res.keys()) if hasattr(res, "keys") else []
            return [dict(zip(col_names, r)) for r in rows]
        return []

    raise TypeError(f"Unsupported db_session type: {type(db_session).__name__}")


class SqlCapabilityExecutor:
    """Authoritative execution boundary for registered SQL capabilities."""

    def _validate_request(
        self, request: CapabilityRequest
    ) -> Result[SqlCapabilityDefinition, CapabilityError]:
        # 1. TenantContext verification (INV-TEN-001, INV-TEN-002)
        if not isinstance(request.tenant_context, TenantContext):
            return Failure(
                CapabilityError(
                    code="ERR_TENANT_CONTEXT_INVALID",
                    message="Valid TenantContext required for capability execution",
                    http_status=403,
                )
            )
        if not getattr(request.tenant_context, "is_active", True):
            return Failure(
                CapabilityError(
                    code="ERR_TENANT_CONTEXT_INVALID",
                    message=f"Tenant '{request.tenant_context.tenant_id}' is inactive",
                    http_status=403,
                )
            )

        # 2. Capability registration check (FR-INV-004)
        capability = get_capability(request.capability_id)
        if capability is None:
            return Failure(
                CapabilityError(
                    code="ERR_UNREGISTERED_CAPABILITY",
                    message=f"Capability '{request.capability_id}' not found in registry",
                    http_status=404,
                )
            )

        # 3. PrincipalContext & IAM permission check (INV-IAM-001)
        if not isinstance(request.principal_context, PrincipalContext):
            return Failure(
                CapabilityError(
                    code="ERR_UNAUTHORIZED_PERMISSION",
                    message="Valid PrincipalContext required for capability execution",
                    http_status=403,
                )
            )
        if not request.principal_context.has_permission(capability.required_permission):
            return Failure(
                CapabilityError(
                    code="ERR_UNAUTHORIZED_PERMISSION",
                    message=f"Principal '{request.principal_context.principal_id}' lacks permission '{capability.required_permission}'",
                    http_status=403,
                )
            )

        # 4. Budget check
        if (
            request.budget_remaining_usd is not None
            and request.budget_remaining_usd < capability.cost_estimate_usd
        ):
            return Failure(
                CapabilityError(
                    code="ERR_INSUFFICIENT_BUDGET",
                    message=f"Insufficient budget for capability {capability.capability_id}: "
                    f"remaining {request.budget_remaining_usd} < required {capability.cost_estimate_usd}",
                    http_status=402,
                )
            )

        # 5. DDL/DML injection check across all parameters (INV-ACT-001)
        for k, v in request.parameters.items():
            if detect_prohibited_sql(str(k)) or detect_prohibited_sql(str(v)):
                return Failure(
                    CapabilityError(
                        code="ERR_PROHIBITED_SQL_OPERATION",
                        message=f"Operation forbidden by read-only policy: prohibited keyword or character in parameter '{k}'",
                        http_status=403,
                    )
                )

        # 6. Temporal boundary check (INV-DATA-001)
        as_of_str = _normalize_utc_string(request.as_of_time)
        end_time_str = request.parameters.get("end_time")
        if end_time_str is not None:
            end_time_norm = _normalize_utc_string(end_time_str)
            if end_time_norm > as_of_str:
                return Failure(
                    CapabilityError(
                        code="ERR_TEMPORAL_LEAKAGE",
                        message=f"Temporal leakage detected: end_time ({end_time_norm}) exceeds as_of_time ({as_of_str})",
                        http_status=400,
                    )
                )

        # 7. Dimension allowlist check
        if capability.allowed_dimensions and "dimension" in request.parameters:
            requested_dim = request.parameters["dimension"]
            if requested_dim not in capability.allowed_dimensions:
                return Failure(
                    CapabilityError(
                        code="ERR_DISALLOWED_DIMENSION",
                        message=f"Dimension '{requested_dim}' not permitted for capability '{capability.capability_id}'",
                        http_status=400,
                    )
                )

        return Success(capability)

    async def execute(
        self, request: CapabilityRequest, db_session: Any
    ) -> Result[CapabilityResult, CapabilityError]:
        """
        Execute registered capability asynchronously with strict safety controls.
        """
        val_res = self._validate_request(request)
        if val_res.is_failure:
            return Failure(val_res.error)

        capability = val_res.value

        # Enforce server-derived tenant_id (INV-TEN-002)
        exec_params = dict(request.parameters)
        exec_params["tenant_id"] = str(request.tenant_context.tenant_id)
        exec_params["as_of_time"] = _normalize_utc_string(request.as_of_time)
        if "start_time" in exec_params:
            exec_params["start_time"] = _normalize_utc_string(exec_params["start_time"])
        if "end_time" in exec_params:
            exec_params["end_time"] = _normalize_utc_string(exec_params["end_time"])

        # Detect SQL dialect
        dialect = "sqlite"
        if hasattr(db_session, "bind") and hasattr(db_session.bind, "dialect"):
            dialect = getattr(db_session.bind.dialect, "name", "sqlite")

        try:
            sql, bound_params = build_sql_for_capability(capability, exec_params, dialect=dialect)
        except Exception as exc:
            return Failure(
                CapabilityError(
                    code="ERR_DISALLOWED_DIMENSION" if "dimension" in str(exc).lower() else "ERR_PROHIBITED_SQL_OPERATION",
                    message=str(exc),
                    http_status=400,
                )
            )

        query_digest = canonicalize_query_digest(sql, bound_params)
        timeout_sec = capability.timeout_ms / 1000.0
        start_mono = time.monotonic()

        try:
            # Run query with timeout enforcement (NFR-AI-004)
            if inspect.iscoroutinefunction(getattr(db_session, "execute", None)):
                raw_rows = await asyncio.wait_for(
                    db_session.execute(sql, bound_params),
                    timeout=timeout_sec,
                )
            else:
                raw_rows = _execute_raw_sql(db_session, sql, bound_params)
        except asyncio.TimeoutError:
            return Failure(
                CapabilityError(
                    code="ERR_QUERY_TIMEOUT",
                    message=f"Capability '{capability.capability_id}' exceeded timeout limit of {capability.timeout_ms} ms",
                    http_status=504,
                )
            )
        except Exception as exc:
            err_msg = str(exc)
            if "timeout" in err_msg.lower() or "canceling statement" in err_msg.lower():
                return Failure(
                    CapabilityError(
                        code="ERR_QUERY_TIMEOUT",
                        message=f"Statement timeout exceeded: {err_msg}",
                        http_status=504,
                    )
                )
            return Failure(
                CapabilityError(
                    code="ERR_PROHIBITED_SQL_OPERATION",
                    message=f"Database execution error: {err_msg}",
                    http_status=403,
                )
            )

        exec_ms = round((time.monotonic() - start_mono) * 1000.0, 2)
        is_truncated = len(raw_rows) > capability.max_rows
        final_rows = raw_rows[: capability.max_rows]

        return Success(
            CapabilityResult(
                capability_id=capability.capability_id,
                rows=final_rows,
                row_count=len(final_rows),
                execution_time_ms=exec_ms,
                query_digest=query_digest,
                cost_usd=capability.cost_estimate_usd,
                is_truncated=is_truncated,
                status="SUCCESS",
            )
        )

    def execute_sync(
        self, request: CapabilityRequest, db_session: Any
    ) -> Result[CapabilityResult, CapabilityError]:
        """Synchronous wrapper for test execution and synchronous workers."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    return pool.submit(asyncio.run, self.execute(request, db_session)).result()
            return loop.run_until_complete(self.execute(request, db_session))
        except RuntimeError:
            return asyncio.run(self.execute(request, db_session))
