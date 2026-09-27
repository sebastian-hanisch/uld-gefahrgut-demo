"""Eingefrorene Instanzen (tests/data/uldk_frozen.json): 4 feste ULD-Listen (Gewicht + Gefahrgutklasse, keine
Zufallsziehung zur Testzeit) über verschiedene Positionszahlen/Fensterbreiten/Gefahrgutanteile/
Trennvorschrift-Stärken, mit denen beide CP-SAT-Läufe reproduzierbare Kennzahlen liefern müssen.

Nach DEMO-PLAYBOOK Abschnitt 4 (NumPy-Version-Drift) hängt kein Test hier von `np.random.default_rng` zur
Testzeit ab: Gewicht und Gefahrgutklasse sind als Zahlen im JSON eingefroren, nur die CP-SAT-Läufe selbst
laufen bei jedem Testlauf neu. Die vier Fälle decken alle drei Meldungszustände ab (siehe app.judgment_message):
Fall 1 (10 Pos./Standard) hat eine Verletzung, aber 0 Kosten; Fälle 2-3 (wenige Positionen/streng) haben
Verletzung UND Kosten; Fall 4 (10 Pos./Standard, wenig Gefahrgut) hat weder Verletzung noch Kosten."""
from __future__ import annotations

import json
import pathlib

import pytest

from uldk_model import Aircraft, DEFAULT_SEG, ULD, Position, STRONG_SEG, default_forbidden, evaluate, segregation_violations
from uldk_oracle import solve_exact

DATA = json.loads((pathlib.Path(__file__).parent / "data" / "uldk_frozen.json").read_text(encoding="utf-8"))
ARM_MIN, ARM_MAX = 6.0, 28.0
SEG_SETS = {"standard": DEFAULT_SEG, "streng": STRONG_SEG}


def make_positions(n_pos: int) -> list[Position]:
    return [Position(f"p{i}", ARM_MIN + i * (ARM_MAX - ARM_MIN) / (n_pos - 1), 2200.0) for i in range(n_pos)]


def _ids():
    return [f"pos{c['n_pos']}-w{c['width']}-{c['seg']}-n{c['n_ulds']}-seed{c['seed']}" for c in DATA]


@pytest.mark.parametrize("case", DATA, ids=_ids())
def test_frozen_instance_reproduces_measured_metrics(case):
    positions = make_positions(case["n_pos"])
    pos_by_name = {p.name: p for p in positions}
    forbidden = default_forbidden(positions)
    seg_set = SEG_SETS[case["seg"]]
    center = (ARM_MIN + ARM_MAX) / 2.0
    ac = Aircraft(40000.0, 40000.0 * center, 8000.0, center, center - case["width"], center + case["width"])
    ulds = [ULD(f"u{i}", w, c) for i, (w, c) in enumerate(zip(case["weights"], case["dg_classes"]))]

    a_free, st_free, _ = solve_exact(ulds, positions, ac, seg_set, forbidden, respect_segregation=False, time_limit_s=5.0)
    a_seg, st_seg, _ = solve_exact(ulds, positions, ac, seg_set, forbidden, respect_segregation=True, time_limit_s=5.0)
    ev_free = evaluate(a_free, ulds, pos_by_name, ac)
    ev_seg = evaluate(a_seg, ulds, pos_by_name, ac)
    v_free = segregation_violations(a_free, ulds, pos_by_name, seg_set, forbidden)
    v_seg = segregation_violations(a_seg, ulds, pos_by_name, seg_set, forbidden)

    # NUR den Zielwert (cargo_weight), n_loaded und die Verletzungszahl vergleichen, NICHT die konkrete
    # Zuordnung - bei mehreren gleich guten Zuordnungen (gleiche Positions-Gewichtsgrenze an allen Positionen)
    # löst CP-SAT mit einzelnem Zielterm Gleichstände nicht deterministisch auf (siehe DEMO-PLAYBOOK Abschnitt
    # 4, feedback_cp_sat_lexicographic_tiebreak.md, und uld-beladeplan-demo/tests/test_frozen_reference.py für
    # dieselbe Ursache).
    exp_free, exp_seg = case["free"], case["seg_result"]
    assert ev_free["cargo_weight"] == pytest.approx(exp_free["cargo_weight"], rel=1e-9, abs=1e-6)
    assert ev_free["n_loaded"] == exp_free["n_loaded"]
    assert v_free == exp_free["violations"]
    assert int(st_free) == exp_free["status"]

    assert ev_seg["cargo_weight"] == pytest.approx(exp_seg["cargo_weight"], rel=1e-9, abs=1e-6)
    assert ev_seg["n_loaded"] == exp_seg["n_loaded"]
    assert v_seg == exp_seg["violations"]
    assert int(st_seg) == exp_seg["status"]


def test_the_frozen_set_covers_n_pos_and_seg_stages():
    n_pos_values = {c["n_pos"] for c in DATA}
    seg_values = {c["seg"] for c in DATA}
    assert n_pos_values >= {4, 6, 10}
    assert seg_values == {"standard", "streng"}
    assert len(DATA) == 4


def test_the_frozen_set_covers_all_three_judgment_states():
    """Nullspalten-Signal: die vier eingefrorenen Fälle decken alle drei Meldungszustände ab (siehe
    app.judgment_message) - sonst könnte ein Fehler in einem Zustand unbemerkt bleiben."""
    states = set()
    for c in DATA:
        cost = c["free"]["cargo_weight"] - c["seg_result"]["cargo_weight"]
        if cost > 1e-6:
            states.add("kostet")
        elif c["free"]["violations"] > 0:
            states.add("unsicher_kostenlos")
        else:
            states.add("kostet_nichts")
    assert states == {"kostet", "unsicher_kostenlos", "kostet_nichts"}
