"""
RevPilot AI — Functional Result Types
Encapsulates success or failure without uncontrolled exception bubbling.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Generic, TypeVar, Callable, Any

T = TypeVar("T")
E = TypeVar("E")
U = TypeVar("U")
F = TypeVar("F")


class Result(Generic[T, E]):
    """Abstract base container for functional operation results."""

    @property
    def is_success(self) -> bool:
        raise NotImplementedError

    @property
    def is_failure(self) -> bool:
        raise NotImplementedError

    def unwrap(self) -> T:
        """Return encapsulated value if Success, otherwise raise wrapped error."""
        raise NotImplementedError

    def unwrap_error(self) -> E:
        """Return encapsulated error if Failure, otherwise raise ValueError."""
        raise NotImplementedError

    def map(self, fn: Callable[[T], U]) -> Result[U, E]:
        """Transform Success value with fn, propagate Failure unchanged."""
        raise NotImplementedError

    def map_err(self, fn: Callable[[E], F]) -> Result[T, F]:
        """Transform Failure error with fn, propagate Success unchanged."""
        raise NotImplementedError

    def and_then(self, fn: Callable[[T], Result[U, E]]) -> Result[U, E]:
        """Chain another Result-returning function on Success."""
        raise NotImplementedError


@dataclass(frozen=True, slots=True)
class Success(Result[T, Any]):
    """Successful operation result."""
    value: T

    @property
    def is_success(self) -> bool:
        return True

    @property
    def is_failure(self) -> bool:
        return False

    def unwrap(self) -> T:
        return self.value

    def unwrap_error(self) -> Any:
        raise ValueError("Cannot unwrap_error on Success")

    def map(self, fn: Callable[[T], U]) -> Result[U, Any]:
        return Success(fn(self.value))

    def map_err(self, fn: Callable[[Any], F]) -> Result[T, F]:
        return Success(self.value)

    def and_then(self, fn: Callable[[T], Result[U, Any]]) -> Result[U, Any]:
        return fn(self.value)

    def __repr__(self) -> str:
        return f"Success({self.value!r})"


@dataclass(frozen=True, slots=True)
class Failure(Result[Any, E]):
    """Failed operation result."""
    error: E

    @property
    def is_success(self) -> bool:
        return False

    @property
    def is_failure(self) -> bool:
        return True

    def unwrap(self) -> Any:
        if isinstance(self.error, Exception):
            raise self.error
        raise ValueError(f"Operation failed with error: {self.error!r}")

    def unwrap_error(self) -> E:
        return self.error

    def map(self, fn: Callable[[Any], U]) -> Result[U, E]:
        return Failure(self.error)

    def map_err(self, fn: Callable[[E], F]) -> Result[Any, F]:
        return Failure(fn(self.error))

    def and_then(self, fn: Callable[[Any], Result[U, E]]) -> Result[U, E]:
        return Failure(self.error)

    def __repr__(self) -> str:
        return f"Failure({self.error!r})"
