"""
Lab 6 - Code (line) coverage tests for fuel_station.py

Run:
    coverage run -m pytest CodeCoverageTest_fuel_station.py
    coverage report -m

Goal: execute (almost) every line of fuel_station.py at least once.
Expected values are worked out by hand from the business rules, not copied
from the program output.
"""
import pytest
from fuel_station import fuel_bill, pump_allowed, session_status


# ---------------------------------------------------------------- starter tests
def test_within_covered_litres():
    assert fuel_bill("regular", 8, "silver") == 0


def test_pump_allowed():
    assert pump_allowed(30, 1, False) is True


# ------------------------------------------------------------------- fuel_bill
def test_unknown_grade_raises():
    # line 5-6: grade not in VOUCHER_LITRES
    with pytest.raises(ValueError, match="unknown fuel grade"):
        fuel_bill("kerosene", 10, "silver")


def test_negative_litres_raises():
    # line 7-8: litres < 0
    with pytest.raises(ValueError, match="invalid litres"):
        fuel_bill("regular", -5, "silver")


def test_gold_regular_gets_bonus_litres():
    # regular covers 10, gold bonus +5 -> 15 covered; extra = 40 - 15 = 25
    # rate 105 (non-diesel), extra <= 30 so no discount -> 25 * 105
    assert fuel_bill("regular", 40, "gold") == 2625


def test_diesel_small_extra():
    # diesel covers 20; extra = 25 - 20 = 5; rate 90 -> 450
    assert fuel_bill("diesel", 25, "silver") == 450


def test_bulk_discount_gold_member():
    # regular gold: covered 15, extra = 60 - 15 = 45 (> 30)
    # rate = 105 - 6 (bulk) - 4 (gold) = 95 -> 45 * 95
    assert fuel_bill("regular", 60, "gold") == 4275


# ---------------------------------------------------------------- pump_allowed
def test_fleet_pump_allowed():
    assert pump_allowed(150, 3, True) is True


def test_non_fleet_over_60_litres_rejected():
    assert pump_allowed(80, 1, False) is False


def test_non_fleet_two_containers_rejected():
    assert pump_allowed(40, 2, False) is False


# -------------------------------------------------------------- session_status
def test_card_payment_active():
    assert session_status(100, True, False) == "active"


def test_cash_payment_warning():
    # cash cutoff 30 -> 20 s is in [15, 30)
    assert session_status(20, False, False) == "warning"


def test_cash_payment_timed_out():
    assert session_status(5, False, False) == "timed_out"


def test_night_extends_cutoff():
    # card + night -> cutoff 90; 100 s is still active
    assert session_status(100, True, True) == "active"
