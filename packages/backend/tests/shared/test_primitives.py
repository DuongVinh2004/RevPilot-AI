"""
Unit tests for Core Domain Value Primitives (TASK-R01-001).
Tests EntityId, UtcDateTime, TimeWindow, Currency, and Money.
"""

from datetime import datetime, timezone, timedelta
from decimal import Decimal
import pytest

from revpilot.shared.identifiers import (
    EntityId,
    TenantId,
    PrincipalId,
    OrganizationId,
    InvestigationId,
    EvidenceId,
    ActionId,
    ApprovalId,
)
from revpilot.shared.temporal import UtcDateTime, TimeWindow
from revpilot.shared.monetary import Currency, Money


# ==========================================
# 1. Identifier Primitive Tests
# ==========================================

def test_entity_id_valid():
    eid = EntityId("custom_id_123")
    assert str(eid) == "custom_id_123"
    assert eid.value == "custom_id_123"


def test_entity_id_empty_rejected():
    with pytest.raises(ValueError, match="cannot be empty"):
        EntityId("")
    with pytest.raises(ValueError, match="cannot be empty"):
        EntityId("   ")


def test_entity_id_invalid_chars_rejected():
    with pytest.raises(ValueError, match="invalid characters"):
        EntityId("bad id with spaces!")
    with pytest.raises(ValueError, match="invalid characters"):
        EntityId("id;DROP TABLE;")


def test_entity_id_type_error():
    with pytest.raises(TypeError):
        EntityId(123)  # type: ignore


def test_typed_id_prefixes():
    t = TenantId.generate()
    assert str(t).startswith("tnt_")

    p = PrincipalId.generate()
    assert str(p).startswith("usr_")

    o = OrganizationId.generate()
    assert str(o).startswith("org_")

    inv = InvestigationId.generate()
    assert str(inv).startswith("inv_")

    evd = EvidenceId.generate()
    assert str(evd).startswith("evd_")

    act = ActionId.generate()
    assert str(act).startswith("act_")

    app = ApprovalId.generate()
    assert str(app).startswith("app_")


def test_typed_id_prefix_enforcement():
    TenantId("tnt_correct_prefix_01")
    with pytest.raises(ValueError, match="must start with required prefix 'tnt_'"):
        TenantId("wrong_prefix_01")


def test_entity_id_equality_and_hash():
    e1 = EntityId("shared_value")
    e2 = EntityId("shared_value")
    e3 = EntityId("different_value")

    assert e1 == e2
    assert e1 != e3
    assert hash(e1) == hash(e2)

    s = {e1, e2, e3}
    assert len(s) == 2


# ==========================================
# 2. Temporal Primitive Tests
# ==========================================

def test_utc_datetime_now():
    now = UtcDateTime.now()
    assert now.value.tzinfo == timezone.utc
    assert isinstance(str(now), str)
    assert str(now).endswith("Z")


def test_utc_datetime_rejects_naive():
    naive = datetime(2026, 1, 1, 12, 0, 0)
    with pytest.raises(ValueError, match="requires timezone-aware datetime"):
        UtcDateTime(naive)


def test_utc_datetime_normalizes_aware():
    # Eastern hemisphere offset +05:00
    tz5 = timezone(timedelta(hours=5))
    dt_tz5 = datetime(2026, 1, 1, 17, 0, 0, tzinfo=tz5)
    utc = UtcDateTime(dt_tz5)
    assert utc.value.tzinfo == timezone.utc
    assert utc.value.hour == 12  # 17:00 at +05:00 is 12:00 UTC


def test_utc_datetime_from_iso():
    utc = UtcDateTime.from_iso("2026-06-15T14:30:00Z")
    assert utc.value.year == 2026
    assert utc.value.month == 6
    assert utc.value.day == 15
    assert utc.value.hour == 14
    assert utc.value.minute == 30

    with pytest.raises(ValueError, match="timezone offset"):
        UtcDateTime.from_iso("2026-06-15T14:30:00")


def test_utc_datetime_comparisons():
    t1 = UtcDateTime.from_iso("2026-01-01T00:00:00Z")
    t2 = UtcDateTime.from_iso("2026-01-02T00:00:00Z")
    assert t1 < t2
    assert t1 <= t2
    assert t2 > t1
    assert t1 != t2


def test_time_window_valid():
    start = UtcDateTime.from_iso("2026-01-01T00:00:00Z")
    end = UtcDateTime.from_iso("2026-01-02T00:00:00Z")
    window = TimeWindow(start=start, end=end)
    assert window.duration_seconds() == 86400.0

    mid = UtcDateTime.from_iso("2026-01-01T12:00:00Z")
    assert window.contains(mid)

    outside = UtcDateTime.from_iso("2026-01-03T00:00:00Z")
    assert not window.contains(outside)


def test_time_window_invalid_order():
    start = UtcDateTime.from_iso("2026-01-02T00:00:00Z")
    end = UtcDateTime.from_iso("2026-01-01T00:00:00Z")
    with pytest.raises(ValueError, match="must precede or equal end"):
        TimeWindow(start=start, end=end)


# ==========================================
# 3. Monetary Primitive Tests
# ==========================================

def test_currency_parsing():
    assert Currency.from_str("usd") == Currency.USD
    assert Currency.from_str("EUR") == Currency.EUR
    with pytest.raises(ValueError, match="Unsupported or invalid currency"):
        Currency.from_str("INVALID")


def test_money_rejects_float():
    with pytest.raises(TypeError, match="Float amounts are strictly forbidden"):
        Money(19.99, Currency.USD)


def test_money_valid_initialization():
    m1 = Money("100.50", Currency.USD)
    assert m1.amount == Decimal("100.5000")
    assert m1.currency == Currency.USD

    m2 = Money(50, "eur")
    assert m2.amount == Decimal("50.0000")
    assert m2.currency == Currency.EUR


def test_money_addition_and_subtraction():
    m1 = Money("100.25", Currency.USD)
    m2 = Money("50.50", Currency.USD)

    res_add = m1 + m2
    assert res_add.amount == Decimal("150.7500")
    assert res_add.currency == Currency.USD

    res_sub = m1 - m2
    assert res_sub.amount == Decimal("49.7500")


def test_money_multiplication():
    m = Money("25.00", Currency.USD)
    res = m * 3
    assert res.amount == Decimal("75.0000")

    res_dec = m * Decimal("1.5")
    assert res_dec.amount == Decimal("37.5000")

    with pytest.raises(TypeError, match="Float factor is forbidden"):
        _ = m * 2.5


def test_money_mismatched_currency_rejected():
    m_usd = Money("100.00", Currency.USD)
    m_eur = Money("100.00", Currency.EUR)

    with pytest.raises(ValueError, match="Currency mismatch: cannot add"):
        _ = m_usd + m_eur

    with pytest.raises(ValueError, match="Currency mismatch: cannot subtract"):
        _ = m_usd - m_eur

    with pytest.raises(ValueError, match="Cannot compare Money in USD with EUR"):
        _ = m_usd < m_eur


def test_money_comparisons():
    m1 = Money("50.00", Currency.USD)
    m2 = Money("100.00", Currency.USD)
    assert m1 < m2
    assert m1 <= m2
    assert m2 > m1
    assert m2 >= m1
    assert m1 != m2


def test_money_display_string():
    m = Money("1234567.8912", Currency.USD)
    assert str(m) == "USD 1,234,567.89"
