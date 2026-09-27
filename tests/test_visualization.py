"""Tests für uldk_visualization.py: Plotly-Figuren bauen ohne Fehler, mit den erwarteten Spuren."""
import numpy as np

import uldk_constants as C
import uldk_results as R
import uldk_visualization as V
from uldk_model import ULD, STRONG_SEG, default_forbidden, make_ulds
from uldk_oracle import solve_exact

D = R.load_results()


def _live_instance():
    positions = C.make_positions(6)
    ac = C.make_aircraft(0.5)
    forbidden = default_forbidden(positions)
    rng = np.random.default_rng(28)
    ulds = make_ulds(rng, 8, 0.6)
    a_free, _, _ = solve_exact(ulds, positions, ac, STRONG_SEG, forbidden, respect_segregation=False, time_limit_s=5.0)
    a_seg, _, _ = solve_exact(ulds, positions, ac, STRONG_SEG, forbidden, respect_segregation=True, time_limit_s=5.0)
    return ulds, a_free, a_seg, ac, positions


def test_loading_map_figure_baut_ohne_fehler():
    ulds, a_free, a_seg, ac, positions = _live_instance()
    fig = V.loading_map_figure(ulds, a_free, a_seg, ac, positions, C.POS_MAX_WEIGHT_KG)
    assert fig is not None
    assert len(fig.data) > 0


def test_loading_map_figure_mit_leerer_zuordnung():
    ulds, _, _, ac, positions = _live_instance()
    fig = V.loading_map_figure(ulds, {}, {}, ac, positions, C.POS_MAX_WEIGHT_KG)
    assert fig is not None


def test_violation_rate_over_share_figure_baut_ohne_fehler():
    rows = R.violation_rate_over_share_rows(D)
    fig = V.violation_rate_over_share_figure(rows)
    assert len(fig.data) == 1
    assert len(fig.data[0].x) == 3


def test_regime_figure_baut_ohne_fehler():
    rows = R.regime_rows(D)
    fig = V.regime_figure(rows)
    assert len(fig.data) == 1
    assert len(fig.data[0].x) == 4


def test_dg_class_colors_und_labels_decken_alle_vier_klassen_ab():
    assert set(V.DG_CLASS_COLOR) == {0, 1, 2, 3}
    assert set(V.DG_CLASS_LABEL) == {0, 1, 2, 3}
    assert len(set(V.DG_CLASS_COLOR.values())) == 4  # vier unterschiedliche Farben
