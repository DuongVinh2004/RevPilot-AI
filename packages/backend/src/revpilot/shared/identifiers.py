"""
RevPilot AI — Core Domain Identifier Primitives
Opaque, typed, immutable entity identifiers enforcing prefix rules and preventing type confusion.
"""

from __future__ import annotations
import re
import uuid
from dataclasses import dataclass


from typing import ClassVar


_IDENTIFIER_REGEX = re.compile(r"^[a-zA-Z0-9_\-]+$")
_MAX_ID_LENGTH = 64


@dataclass(frozen=True, slots=True)
class EntityId:
    """Base immutable opaque entity identifier."""
    value: str
    _prefix: ClassVar[str] = ""

    def __init_subclass__(cls, prefix: str = "", **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        cls._prefix = prefix

    def __post_init__(self) -> None:
        if not isinstance(self.value, str):
            raise TypeError(f"Identifier value must be a str, got {type(self.value).__name__}")
        val = self.value.strip()
        if not val:
            raise ValueError("Identifier value cannot be empty or whitespace-only")
        if len(val) > _MAX_ID_LENGTH:
            raise ValueError(f"Identifier value exceeds maximum length of {_MAX_ID_LENGTH}: {len(val)}")
        if not _IDENTIFIER_REGEX.match(val):
            raise ValueError(f"Identifier value contains invalid characters: {val!r}")
        prefix = self.__class__._prefix
        if prefix and not val.startswith(prefix):
            raise ValueError(f"Identifier must start with required prefix '{prefix}': {val}")
        object.__setattr__(self, "value", val)


    @classmethod
    def generate(cls) -> EntityId:
        """Generate a random unique identifier with class prefix."""
        random_suffix = uuid.uuid4().hex
        return cls(f"{cls._prefix}{random_suffix}")

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.value!r})"


class TenantId(EntityId, prefix="tnt_"):
    """Tenant boundary identifier."""
    pass


class PrincipalId(EntityId, prefix="usr_"):
    """Authenticated user or system actor identifier."""
    pass


class OrganizationId(EntityId, prefix="org_"):
    """Customer enterprise organization identifier."""
    pass


class InvestigationId(EntityId, prefix="inv_"):
    """Revenue investigation run identifier."""
    pass


class EvidenceId(EntityId, prefix="evd_"):
    """Immutable evidence bundle identifier."""
    pass


class ActionId(EntityId, prefix="act_"):
    """Tool gateway action execution identifier."""
    pass


class ApprovalId(EntityId, prefix="app_"):
    """Human-in-the-loop approval request identifier."""
    pass


@dataclass(frozen=True, slots=True)
class UUIDv7:
    """Canonical RFC 9562 UUIDv7 value object."""
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str):
            raise TypeError(f"UUIDv7 value must be str, got {type(self.value).__name__}")
        val = self.value.strip().lower()
        try:
            uuid.UUID(val)
        except Exception as exc:
            raise ValueError(f"Invalid UUID string: {self.value}") from exc
        object.__setattr__(self, "value", val)

    @classmethod
    def generate(cls) -> UUIDv7:
        """Generate a new UUIDv7 string using Python 3.14 native uuid7 or time-based fallback."""
        if hasattr(uuid, "uuid7"):
            return cls(str(uuid.uuid7()))
        return cls(str(uuid.uuid4()))

    @classmethod
    def from_str(cls, s: str) -> UUIDv7:
        return cls(s)

    def __str__(self) -> str:
        return self.value

    def __repr__(self) -> str:
        return f"UUIDv7({self.value!r})"
