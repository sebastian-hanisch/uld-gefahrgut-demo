"""Jede Zahl aus dem README wird hier gegen data/uldk_results.json nachgerechnet (DEMO-PLAYBOOK Abschnitt 4:
erst messen, dann Text schreiben - keine Behauptung ohne Test). Deckt sowohl den Hauptsweep (27 Zellen,
Standard-Trennvorschrift, 10 Positionen) als auch die AP-0-Zusatzmessung (27 Zellen, strenge Trennvorschrift,
Positionszahl 4/6/10) ab."""
import pytest

import uldk_results as R

D = R.load_results()
STD = R.standard_sweep_rows(D)
STRONG = R.strong_sweep_rows(D)


# --- Hauptsweep (Standard-Trennvorschrift, 10 Positionen) -----------------------------------------------------
def test_befund_regel_ohne_gefahrgutwissen_verletzt_oft():
    mean_vio = R.mean_violation_rate(STD)
    assert mean_vio == pytest.approx(0.41790123456790124, rel=1e-9)
    top = R.max_cell(STD, "violation_rate_free")
    assert top["violation_rate_free"] == pytest.approx(0.8, rel=1e-9)
    assert top["width"] == pytest.approx(0.3) and top["dg_share"] == pytest.approx(0.6) and top["n_ulds"] == 16


def test_befund_gefahrgutanteil_treibt_die_verletzungsrate():
    rows = R.violation_rate_over_share_rows(D)  # width=0.5, n_ulds=12
    assert [r["violation_rate_free"] for r in rows] == pytest.approx(
        [0.26666666666666666, 0.35, 0.6833333333333333], rel=1e-9)


def test_befund_hauptsweep_kostet_in_allen_27_zellen_exakt_nichts():
    assert all(r["cost_pct"] == 0.0 for r in STD)
    assert all(r["cost_kg_mean"] == 0.0 for r in STD)


def test_befund_cp_sat_immer_optimal():
    assert all(r["exact_optimal_rate"] == 1.0 for r in R.cells(D))


# --- AP-0-Zusatzmessung (strenge Trennvorschrift, Positionszahl 4/6/10) ---------------------------------------
def test_befund_zusatzmessung_kostet_nicht_ueberall_nichts():
    n_nonzero = sum(1 for r in STRONG if r["cost_kg_mean"] > 0.0)
    assert n_nonzero == 14
    assert len(STRONG) == 27


def test_befund_groesster_gemessener_preis():
    top = R.max_cell(STRONG, "cost_kg_mean")
    assert top["n_pos"] == 4 and top["dg_share"] == pytest.approx(0.6) and top["n_ulds"] == 8
    assert top["cost_pct"] == pytest.approx(1.9279913591750453, rel=1e-9)
    assert top["cost_kg_mean"] == pytest.approx(124.20398992040973, rel=1e-9)
    assert top["cost_kg_max"] == pytest.approx(1245.7633907592153, rel=1e-9)
    assert top["share_instances_with_cost"] == pytest.approx(0.23333333333333334, rel=1e-9)


def test_befund_10_positionen_kostet_fast_immer_nichts_selbst_bei_strenger_trennvorschrift():
    """Der zentrale, im Plan nicht erwartete AP-0-Befund: selbst die strenge Trennvorschrift kostet bei 10
    Positionen in 8 von 9 gemessenen Zellen exakt 0,00 % - nur die extremste Zelle (60 % Gefahrgut, 16 ULDs)
    zeigt einen kleinen realen Preis."""
    n_pos_10 = [r for r in STRONG if r["n_pos"] == 10]
    assert len(n_pos_10) == 9
    zero_cells = [r for r in n_pos_10 if r["cost_pct"] == 0.0]
    assert len(zero_cells) == 8
    exception = next(r for r in n_pos_10 if r["cost_pct"] > 0.0)
    assert exception["dg_share"] == pytest.approx(0.6) and exception["n_ulds"] == 16
    assert exception["cost_pct"] == pytest.approx(0.3671577915869046, rel=1e-9)
    assert exception["cost_kg_mean"] == pytest.approx(56.93307631281562, rel=1e-9)


# --- Presets (Referenzzellen aus uldk_constants.PRESETS) -------------------------------------------------------
def test_preset_standard_zahlen():
    cell = R.find_cell(D, "streng", 6, 0.5, 0.6, 8)
    assert cell["violation_rate_free"] == pytest.approx(0.7833333333333333, rel=1e-9)
    assert cell["cost_pct"] == pytest.approx(1.2486489492332458, rel=1e-9)
    assert cell["cost_kg_mean"] == pytest.approx(106.57141651324135, rel=1e-9)


def test_preset_lockere_trennung_zahlen():
    cell = R.find_cell(D, "standard", 10, 0.5, 0.4, 12)
    assert cell["violation_rate_free"] == pytest.approx(0.35, rel=1e-9)
    assert cell["cost_pct"] == 0.0


def test_preset_viel_gefahrgut_zahlen():
    cell = R.find_cell(D, "streng", 10, 0.5, 0.6, 16)
    assert cell["violation_rate_free"] == pytest.approx(0.8833333333333333, rel=1e-9)
    assert cell["cost_pct"] == pytest.approx(0.3671577915869046, rel=1e-9)


def test_preset_wenig_gefahrgut_zahlen():
    cell = R.find_cell(D, "standard", 10, 0.5, 0.2, 8)
    assert cell["violation_rate_free"] == pytest.approx(0.18333333333333332, rel=1e-9)
    assert cell["cost_pct"] == 0.0
