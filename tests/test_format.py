"""Tests für uldk_format.py: Zahlenformate mit deutschem Dezimalkomma."""
from uldk_format import fmt_kg, fmt_num, fmt_pct


def test_fmt_num_verwendet_komma():
    assert fmt_num(3.14159, 2) == "3,14"
    assert fmt_num(-1.5, 1) == "-1,5"


def test_fmt_num_signed():
    assert fmt_num(3.0, 1, signed=True) == "+3,0"
    assert fmt_num(-3.0, 1, signed=True) == "-3,0"


def test_fmt_pct_multipliziert_mit_100():
    assert fmt_pct(0.745, 1) == "74,5 %"
    assert fmt_pct(0.0, 0) == "0 %"


def test_fmt_kg_tausendertrennzeichen():
    assert fmt_kg(1234.0) == "1.234"
    assert fmt_kg(124.2, digits=1) == "124,2"
    assert fmt_kg(-500.0) == "-500"
