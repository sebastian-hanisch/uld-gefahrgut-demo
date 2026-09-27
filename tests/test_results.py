"""Tests für uldk_results.py: Zell-Zuordnung, Zusammensetzung aus Hauptsweep + AP-0-Zusatzmessung."""
from __future__ import annotations

import pytest

import uldk_results as R

D = R.load_results()


def test_54_zellen_insgesamt_ohne_duplikate():
    seen = set()
    for c in R.cells(D):
        key = (c["seg"], c["n_pos"], c["width"], c["dg_share"], c["n_ulds"])
        assert key not in seen
        seen.add(key)
    assert len(seen) == 54


def test_hauptsweep_und_zusatzmessung_haben_je_27_zellen():
    assert len(R.standard_sweep_rows(D)) == 27
    assert len(R.strong_sweep_rows(D)) == 27


def test_hauptsweep_ist_immer_bei_10_positionen_und_kostet_nie_etwas():
    for r in R.standard_sweep_rows(D):
        assert r["n_pos"] == 10
        assert r["cost_pct"] == 0.0
        assert r["cost_kg_mean"] == 0.0


def test_zusatzmessung_deckt_alle_drei_positionszahlen_ab():
    n_pos_values = {r["n_pos"] for r in R.strong_sweep_rows(D)}
    assert n_pos_values == {4, 6, 10}


def test_zusatzmessung_hat_mindestens_eine_zelle_mit_echtem_preis():
    """Nullspalten-Signal umgekehrt geprüft: die AP-0-Zusatzmessung darf nicht selbst wieder überall 0 kosten -
    sonst hätte AP 0 sein Ziel verfehlt."""
    assert any(r["cost_kg_mean"] > 0.0 for r in R.strong_sweep_rows(D))
    assert any(r["cost_kg_mean"] == 0.0 for r in R.strong_sweep_rows(D))  # aber auch nicht überall


def test_find_cell_exakter_treffer():
    cell = R.find_cell(D, "streng", 4, 0.5, 0.6, 8)
    assert cell["n_pos"] == 4 and cell["seg"] == "streng"


def test_find_cell_unbekannte_kombination_wirft_key_error():
    with pytest.raises(KeyError):
        R.find_cell(D, "streng", 5, 0.5, 0.6, 8)


def test_violation_rate_over_share_rows_liefert_drei_anteile_aufsteigend():
    rows = R.violation_rate_over_share_rows(D)
    assert [r["dg_share"] for r in rows] == [0.2, 0.4, 0.6]
    assert all(r["seg"] == "standard" and r["n_pos"] == 10 for r in rows)
    # monotone Tendenz (nicht zwingend strikt, aber die Spannweite muss real sein - kein Nullspalten-Signal)
    assert rows[0]["violation_rate_free"] < rows[-1]["violation_rate_free"]


def test_regime_rows_deckt_beide_trennvorschrift_staerken_ab():
    rows = R.regime_rows(D)
    assert len(rows) == 4  # standard@10 + streng@4,6,10
    segs = {r["seg"] for r in rows}
    assert segs == {"standard", "streng"}
    n_pos_values = sorted(r["n_pos"] for r in rows)
    assert n_pos_values == [4, 6, 10, 10]


def test_regime_rows_zeigt_nicht_ueberall_denselben_preis():
    """Nullspalten-Signal: nicht alle vier Regime-Zeilen dürfen denselben Kostenwert zeigen."""
    rows = R.regime_rows(D)
    costs = {round(r["cost_pct"], 6) for r in rows}
    assert len(costs) > 1


def test_mean_violation_rate_und_max_cell():
    rows = R.standard_sweep_rows(D)
    mean = R.mean_violation_rate(rows)
    assert 0.0 < mean < 1.0
    top = R.max_cell(rows, "violation_rate_free")
    assert top["violation_rate_free"] == max(r["violation_rate_free"] for r in rows)
