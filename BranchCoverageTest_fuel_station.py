"""
Lab 6 - Branch coverage tests for fuel_station.py

Run:
    coverage run --branch -m pytest BranchCoverageTest_fuel_station.py
    coverage report -m

Goal: every decision in fuel_station.py is evaluated to BOTH True and False,
including the exact boundary values (==, one above, one below).
Expected values are worked out by hand from the business rules.

Rules recap
  fuel_bill:  covered litres  regular 10 / premium 15 / diesel 20
              gold tier gets +5 covered litres (NOT on diesel)
              base rate: diesel 90, others 105
              if extra > 30 litres: rate -6, and a further -4 for gold
  pump_allowed: fleet -> litres <= 200
                otherwise litres <= 60 and containers <= 1
  session_status: cutoff = 60 (card) or 30 (cash), +30 at night
                  >= cutoff active | >= cutoff-15 warning | else timed_out
"""
import pytest
from fuel_station import fuel_bill, pump_allowed, session_status


# ---------------------------------------------------------------- starter tests
def test_within_covered_litres():
    assert fuel_bill("regular", 8, "silver") == 0


def test_pump_allowed():
    assert pump_allowed(30, 1, False) is True


# ============================================================ fuel_bill: guards
@pytest.mark.parametrize("grade", ["kerosene", "Regular", "", "DIESEL"])
def test_unknown_grade_raises(grade):
    # `grade not in VOUCHER_LITRES` -> True branch
    with pytest.raises(ValueError, match="unknown fuel grade"):
        fuel_bill(grade, 10, "silver")


def test_unknown_grade_checked_before_litres():
    # both inputs invalid -> the grade error wins (it is checked first)
    with pytest.raises(ValueError, match="unknown fuel grade"):
        fuel_bill("kerosene", -1, "silver")


@pytest.mark.parametrize("litres", [-1, -0.5, -100])
def test_negative_litres_raises(litres):
    # `litres < 0` -> True branch
    with pytest.raises(ValueError, match="invalid litres"):
        fuel_bill("regular", litres, "silver")


def test_zero_litres_is_valid_and_free():
    # `litres < 0` -> False branch at the boundary (0 is NOT invalid)
    assert fuel_bill("regular", 0, "silver") == 0


# ================================================ fuel_bill: voucher / free zone
@pytest.mark.parametrize(
    "grade, litres, tier, expected",
    [
        # extra <= 0  -> returns 0 (exactly at the voucher limit and below it)
        ("regular", 10, "silver", 0),
        ("premium", 15, "silver", 0),
        ("diesel", 20, "silver", 0),
        ("regular", 9, "silver", 0),
        # one litre over the limit -> first chargeable litre (extra == 1)
        ("regular", 11, "silver", 105),
        ("premium", 16, "silver", 105),
        ("diesel", 21, "silver", 90),
    ],
)
def test_voucher_boundary(grade, litres, tier, expected):
    assert fuel_bill(grade, litres, tier) == expected


# ================================== fuel_bill: gold bonus (+5, never on diesel)
@pytest.mark.parametrize(
    "grade, litres, expected",
    [
        ("regular", 15, 0),      # 10 + 5 = 15 covered, extra 0
        ("regular", 16, 105),    # extra 1 * 105
        ("premium", 20, 0),      # 15 + 5 = 20 covered
        ("premium", 21, 105),
        ("diesel", 20, 0),       # diesel: no bonus, 20 covered
        ("diesel", 21, 90),      # extra 1 * 90  (a bonus would have made it 0)
    ],
)
def test_gold_bonus_rules(grade, litres, expected):
    assert fuel_bill(grade, litres, "gold") == expected


@pytest.mark.parametrize("tier", ["silver", "bronze", "GOLD", "", None])
def test_non_gold_tiers_get_no_bonus(tier):
    # `loyalty_tier == "gold"` -> False branch (regular covers only 10)
    assert fuel_bill("regular", 15, tier) == 525  # extra 5 * 105


# ================================================ fuel_bill: rate (diesel vs not)
def test_diesel_rate_is_90():
    # `grade == "diesel"` -> True branch
    assert fuel_bill("diesel", 30, "silver") == 900   # extra 10 * 90


@pytest.mark.parametrize("grade, litres, expected",
                         [("regular", 20, 1050),      # extra 10 * 105
                          ("premium", 25, 1050)])     # extra 10 * 105
def test_non_diesel_rate_is_105(grade, litres, expected):
    # `grade == "diesel"` -> False branch
    assert fuel_bill(grade, litres, "silver") == expected


# ====================================== fuel_bill: bulk discount (extra > 30)
@pytest.mark.parametrize(
    "grade, litres, tier, expected",
    [
        # extra == 30 -> boundary, NO discount (condition is strictly > 30)
        ("regular", 40, "silver", 3150),   # 30 * 105
        ("diesel", 50, "silver", 2700),    # 30 * 90
        ("regular", 45, "gold", 3150),     # covered 15, extra 30 * 105
    ],
)
def test_bulk_threshold_not_reached(grade, litres, tier, expected):
    assert fuel_bill(grade, litres, tier) == expected


@pytest.mark.parametrize(
    "grade, litres, tier, expected",
    [
        # extra == 31 -> discount applies, NON-gold  (rate - 6 only)
        ("regular", 41, "silver", 3069),   # 31 * 99
        ("premium", 46, "silver", 3069),   # covered 15, extra 31 * 99
        ("diesel", 51, "silver", 2604),    # covered 20, extra 31 * 84
        # extra == 31 -> discount applies, GOLD (rate - 6 - 4)
        ("regular", 46, "gold", 2945),     # covered 15, extra 31 * 95
        ("premium", 51, "gold", 2945),     # covered 20, extra 31 * 95
        ("diesel", 51, "gold", 2480),      # covered 20 (no bonus), 31 * 80
        # large order
        ("regular", 60, "gold", 4275),     # extra 45 * 95
    ],
)
def test_bulk_discount_applies(grade, litres, tier, expected):
    assert fuel_bill(grade, litres, tier) == expected


# ======================================================== pump_allowed
@pytest.mark.parametrize(
    "litres, containers, expected",
    [
        (200, 0, True),     # fleet, exactly at the 200 L limit
        (199, 5, True),     # fleet ignores container count
        (0, 0, True),
        (201, 0, False),    # fleet, one litre over
        (500, 1, False),
    ],
)
def test_pump_allowed_fleet(litres, containers, expected):
    assert pump_allowed(litres, containers, True) is expected


@pytest.mark.parametrize(
    "litres, containers, expected",
    [
        (30, 1, True),      # normal request
        (60, 1, True),      # exactly 60 L, exactly 1 container
        (60, 0, True),      # no containers
        (0, 0, True),
        (61, 1, False),     # one litre over -> rejected by litre rule
        (100, 0, False),    # litre rule rejects regardless of containers
        (60, 2, False),     # litres OK but two containers
        (30, 5, False),
        (61, 2, False),     # both rules violated
    ],
)
def test_pump_allowed_non_fleet(litres, containers, expected):
    assert pump_allowed(litres, containers, False) is expected


# ======================================================== session_status
@pytest.mark.parametrize(
    "seconds, card, night, expected",
    [
        # --- card, daytime: cutoff 60 (warning from 45) -----------------
        (61, True, False, "active"),
        (60, True, False, "active"),        # == cutoff
        (59, True, False, "warning"),       # cutoff - 1
        (45, True, False, "warning"),       # == cutoff - 15
        (44, True, False, "timed_out"),
        (0, True, False, "timed_out"),
        # --- cash, daytime: cutoff 30 (warning from 15) -----------------
        (31, False, False, "active"),
        (30, False, False, "active"),
        (29, False, False, "warning"),
        (15, False, False, "warning"),
        (14, False, False, "timed_out"),
        (0, False, False, "timed_out"),
        # --- card, night: cutoff 90 (warning from 75) -------------------
        (90, True, True, "active"),
        (89, True, True, "warning"),
        (75, True, True, "warning"),
        (74, True, True, "timed_out"),
        # --- cash, night: cutoff 60 (warning from 45) -------------------
        (60, False, True, "active"),
        (59, False, True, "warning"),
        (45, False, True, "warning"),
        (44, False, True, "timed_out"),
    ],
)
def test_session_status(seconds, card, night, expected):
    assert session_status(seconds, card, night) == expected
