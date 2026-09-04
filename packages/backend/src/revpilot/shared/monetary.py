"""
RevPilot AI — Core Monetary Primitives
Immutable precision money and currency value objects preventing float inaccuracies and currency mismatch.
"""

from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum


class Currency(str, Enum):
    """ISO-4217 standard 3-letter uppercase currency codes."""
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    JPY = "JPY"
    CAD = "CAD"
    AUD = "AUD"
    CHF = "CHF"
    SGD = "SGD"

    @classmethod
    def from_str(cls, code: str) -> Currency:
        """Parse currency code case-insensitively."""
        if not isinstance(code, str):
            raise TypeError(f"Currency code must be a str, got {type(code).__name__}")
        upper = code.strip().upper()
        try:
            return cls(upper)
        except ValueError:
            raise ValueError(f"Unsupported or invalid currency code: {code!r}")


# Standard precision: 4 decimal places for sub-cent calculations, display rounded to 2
_PRECISION_EXPONENT = Decimal("0.0001")


@dataclass(frozen=True, slots=True)
class Money:
    """
    Immutable value object representing an amount in a specific currency.
    Rejects float amounts to prevent financial rounding errors.
    """
    amount: Decimal
    currency: Currency

    def __init__(self, amount: Decimal | int | str, currency: Currency | str) -> None:
        if isinstance(amount, float):
            raise TypeError(
                "Float amounts are strictly forbidden for Money to prevent precision loss. "
                "Use Decimal, int, or str."
            )
        if not isinstance(amount, Decimal):
            try:
                dec_amount = Decimal(str(amount))
            except Exception as exc:
                raise ValueError(f"Invalid monetary amount: {amount!r}") from exc
        else:
            dec_amount = amount

        if isinstance(currency, str):
            curr = Currency.from_str(currency)
        elif isinstance(currency, Currency):
            curr = currency
        else:
            raise TypeError(f"currency must be Currency or str, got {type(currency).__name__}")

        quantized = dec_amount.quantize(_PRECISION_EXPONENT, rounding=ROUND_HALF_UP)
        object.__setattr__(self, "amount", quantized)
        object.__setattr__(self, "currency", curr)

    def add(self, other: Money) -> Money:
        """Add two Money objects of the same currency."""
        if not isinstance(other, Money):
            raise TypeError(f"Cannot add Money and {type(other).__name__}")
        if self.currency != other.currency:
            raise ValueError(
                f"Currency mismatch: cannot add {self.currency.value} and {other.currency.value}"
            )
        return Money(self.amount + other.amount, self.currency)

    def subtract(self, other: Money) -> Money:
        """Subtract two Money objects of the same currency."""
        if not isinstance(other, Money):
            raise TypeError(f"Cannot subtract {type(other).__name__} from Money")
        if self.currency != other.currency:
            raise ValueError(
                f"Currency mismatch: cannot subtract {other.currency.value} from {self.currency.value}"
            )
        return Money(self.amount - other.amount, self.currency)

    def multiply(self, factor: Decimal | int | str) -> Money:
        """Multiply Money by a scalar factor."""
        if isinstance(factor, float):
            raise TypeError("Float factor is forbidden for Money multiplication. Use Decimal or int.")
        dec_factor = Decimal(str(factor))
        return Money(self.amount * dec_factor, self.currency)

    def __add__(self, other: Money) -> Money:
        return self.add(other)

    def __sub__(self, other: Money) -> Money:
        return self.subtract(other)

    def __mul__(self, factor: Decimal | int | str) -> Money:
        return self.multiply(factor)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Money):
            return False
        return self.currency == other.currency and self.amount == other.amount

    def __lt__(self, other: Money) -> bool:
        if not isinstance(other, Money):
            raise TypeError(f"'<' not supported between instances of 'Money' and '{type(other).__name__}'")
        if self.currency != other.currency:
            raise ValueError(f"Cannot compare Money in {self.currency.value} with {other.currency.value}")
        return self.amount < other.amount

    def __le__(self, other: Money) -> bool:
        if not isinstance(other, Money):
            raise TypeError(f"'<=' not supported between instances of 'Money' and '{type(other).__name__}'")
        if self.currency != other.currency:
            raise ValueError(f"Cannot compare Money in {self.currency.value} with {other.currency.value}")
        return self.amount <= other.amount

    def __gt__(self, other: Money) -> bool:
        if not isinstance(other, Money):
            raise TypeError(f"'>' not supported between instances of 'Money' and '{type(other).__name__}'")
        if self.currency != other.currency:
            raise ValueError(f"Cannot compare Money in {self.currency.value} with {other.currency.value}")
        return self.amount > other.amount

    def __ge__(self, other: Money) -> bool:
        if not isinstance(other, Money):
            raise TypeError(f"'>=' not supported between instances of 'Money' and '{type(other).__name__}'")
        if self.currency != other.currency:
            raise ValueError(f"Cannot compare Money in {self.currency.value} with {other.currency.value}")
        return self.amount >= other.amount

    def to_display_string(self) -> str:
        """Return formatted string with 2 decimal places and currency code."""
        two_dec = self.amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return f"{self.currency.value} {two_dec:,.2f}"

    def __str__(self) -> str:
        return self.to_display_string()

    def __repr__(self) -> str:
        return f"Money({self.amount!r}, {self.currency!r})"
