"""Messreihe für uld-gefahrgut-demo: kombiniert den Hauptsweep (bitgleich reproduzierbar gegenüber
packen-planung/messreihe_uld_gefahrgut/sweep_data.json, DEFAULT_SEG, n_pos=10, 27 Zellen) mit der
AP-0-Zusatzmessung (STRONG_SEG, n_pos in {4,6,10}, 27 weitere Zellen). Schreibt data/uldk_results.json.

AP 0 (siehe Bau-Auftrag, Detailplan Abschnitt 14): der Hauptsweep zeigt bei n_pos=10 und der milden
Standard-Trennvorschrift in ALLEN 27 Zellen einen wirtschaftlichen Preis von 0,00 % - real (kein Bug, siehe
packen-planung/.../ERGEBNIS.md), macht die Demo in dieser Einstellung aber wirkungslos. Die Zusatzmessung
misst deshalb dieselben drei Sweep-Dimensionen (Gefahrgutanteil, ULD-Zahl - PLUS jetzt Positionszahl als
vierte Dimension) unter der strengen Trennvorschrift (alle drei Klassen paarweise verboten).

Gekürzt gegenüber der vollen 3x3x3x3=81-Zellen-Kreuztabelle (siehe Bau-Auftrag): die Fensterbreite wird für
die Zusatzmessung auf 0,5 m (Standardwert) FESTGEHALTEN, nicht mitvariiert. Begründung: (1) keiner der fünf
Presets (uldk_constants.PRESETS) variiert die Fensterbreite - alle nutzen den Standardwert 0,5 m; (2) der
Effekt der Fensterbreite auf die Verletzungsrate ist im Hauptsweep bereits gemessen (ERGEBNIS.md Befund 2:
schwächerer Treiber als der Gefahrgutanteil) und muss für die neue Positionszahl-Dimension nicht wiederholt
werden; (3) die App-Hauptansicht rechnet ohnehin IMMER live (beide CP-SAT-Läufe), die Messreihe dient nur den
vorgerechneten Kernabschnitt-Grafiken/Tabellen, nicht einer Zelle-für-jede-Reglerkombination-Suche wie bei
uld-beladeplan-demo. Damit bleibt die Zusatzmessung bei 3 Positionszahlen x 3 Gefahrgutanteile x 3 ULD-Zahlen
= 27 Zellen - derselbe Umfang wie der Hauptsweep, mit denselben 60 Instanzen je Zelle.

Aufruf (im Projektordner): _venvs/runtime/Scripts/python.exe tools/sweep.py
"""
from __future__ import annotations

import json
import pathlib
import sys
import time
import zlib

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from uldk_model import (  # noqa: E402
    Aircraft, Position, DEFAULT_SEG, STRONG_SEG, default_forbidden, make_ulds, segregation_violations,
)
from uldk_oracle import solve_exact  # noqa: E402


def cell_seed(*parts) -> int:
    return zlib.crc32(repr(parts).encode("utf-8")) % (2**31)


ARM_MIN, ARM_MAX = 6.0, 28.0
POS_MAX_WEIGHT_KG = 2200.0
CENTER = (ARM_MIN + ARM_MAX) / 2.0

WIDTHS = [1.0, 0.5, 0.3]
DG_SHARES = [0.2, 0.4, 0.6]
N_ULDS = [8, 12, 16]
N_POS_LEVELS = [4, 6, 10]
STRONG_WIDTH = 0.5  # siehe Modul-Docstring: Fensterbreite in der Zusatzmessung festgehalten
N_INSTANCES = 60
# 8.0 statt 3.0 s (CI-Fund-Korrektur): mit dem deterministischen Einzel-Suchprozess (uldk_oracle.py,
# num_search_workers=1) braucht der Solver gelegentlich länger, um ein bereits gefundenes Optimum zu BEWEISEN
# (Portfolio-Suche mit mehreren Threads schließt die Optimalitätslücke schneller) - bei 3,0 s blieb eine von
# 3.240 Zellen-Instanzen (standard, n_pos=10, width=1,0 m, dg_share=0,4, n=8) unbewiesen (exact_optimal_rate
# 0,9833 statt 1,0), bei 8,0 s bewiesen alle. Alle anderen Felder dieser Zelle blieben dabei bitgleich.
TIME_LIMIT = 8.0


def make_positions(n_pos: int) -> list[Position]:
    return [Position(f"p{i}", ARM_MIN + i * (ARM_MAX - ARM_MIN) / (n_pos - 1), POS_MAX_WEIGHT_KG) for i in range(n_pos)]


def run_cell(width, dg_share, n_ulds, n_pos, seg, seg_label, seed_parts, n_instances=N_INSTANCES, time_limit=TIME_LIMIT):
    positions = make_positions(n_pos)
    pos_by_name = {p.name: p for p in positions}
    forbidden = default_forbidden(positions)
    ac = Aircraft(40000.0, 40000.0 * CENTER, 8000.0, CENTER, CENTER - width, CENTER + width)
    rng = np.random.default_rng(cell_seed(*seed_parts))

    n_vio_free = 0
    w_free_list, w_seg_list = [], []
    n_exact_optimal = 0
    for _ in range(n_instances):
        ulds = make_ulds(rng, n_ulds, dg_share)
        a_free, st_free, _ = solve_exact(ulds, positions, ac, seg, forbidden, respect_segregation=False, time_limit_s=time_limit)
        v = segregation_violations(a_free, ulds, pos_by_name, seg, forbidden)
        n_vio_free += v > 0
        w_free = sum(u.weight_kg for u in ulds if u.name in a_free)
        w_free_list.append(w_free)
        a_seg, st_seg, _ = solve_exact(ulds, positions, ac, seg, forbidden, respect_segregation=True, time_limit_s=time_limit)
        w_seg = sum(u.weight_kg for u in ulds if u.name in a_seg)
        w_seg_list.append(w_seg)
        n_exact_optimal += (int(st_free) == 4) and (int(st_seg) == 4)

    w_free_arr = np.array(w_free_list)
    w_seg_arr = np.array(w_seg_list)
    cost_kg = w_free_arr - w_seg_arr
    mean_w_free = float(w_free_arr.mean())
    return dict(
        seg=seg_label, n_pos=n_pos, width=width, dg_share=dg_share, n_ulds=n_ulds,
        violation_rate_free=n_vio_free / n_instances,
        mean_w_free=mean_w_free, mean_w_seg=float(w_seg_arr.mean()),
        cost_pct=float(100 * cost_kg.mean() / mean_w_free) if mean_w_free > 0 else 0.0,
        cost_pct_se=float(100 * cost_kg.std(ddof=1) / np.sqrt(n_instances) / mean_w_free) if mean_w_free > 0 else 0.0,
        cost_kg_mean=float(cost_kg.mean()), cost_kg_max=float(cost_kg.max()),
        share_instances_with_cost=float((cost_kg > 1e-6).mean()),
        exact_optimal_rate=n_exact_optimal / n_instances,
    )


def run_sweep(n_instances=N_INSTANCES, time_limit=TIME_LIMIT):
    t0 = time.time()
    rows = []
    # --- Hauptsweep: DEFAULT_SEG, n_pos=10 (bitgleich reproduzierbar ggü. packen-planung/.../sweep_data.json,
    # weil hier dieselbe cell_seed(width, dg_share, n)-Formel wie im Original verwendet wird) -----------------
    for width in WIDTHS:
        for dg_share in DG_SHARES:
            for n in N_ULDS:
                row = run_cell(width, dg_share, n, n_pos=10, seg=DEFAULT_SEG, seg_label="standard",
                                seed_parts=(width, dg_share, n), n_instances=n_instances, time_limit=time_limit)
                rows.append(row)
                print(f"[standard] width={width} dg_share={dg_share} n={n:2d} n_pos=10  "
                      f"vio_free={row['violation_rate_free']:.2f}  cost={row['cost_pct']:.2f}%  ({time.time()-t0:.0f}s)")
    # --- AP-0-Zusatzmessung: STRONG_SEG, Fensterbreite fest 0,5 m, n_pos in {4,6,10} -----------------------
    for n_pos in N_POS_LEVELS:
        for dg_share in DG_SHARES:
            for n in N_ULDS:
                row = run_cell(STRONG_WIDTH, dg_share, n, n_pos=n_pos, seg=STRONG_SEG, seg_label="streng",
                                seed_parts=(STRONG_WIDTH, dg_share, n, n_pos, "strong"),
                                n_instances=n_instances, time_limit=time_limit)
                rows.append(row)
                print(f"[streng]   n_pos={n_pos:2d} dg_share={dg_share} n={n:2d} width={STRONG_WIDTH}  "
                      f"vio_free={row['violation_rate_free']:.2f}  cost={row['cost_pct']:.2f}%  "
                      f"cost_kg_mean={row['cost_kg_mean']:.1f}  ({time.time()-t0:.0f}s)")
    return dict(arm_min=ARM_MIN, arm_max=ARM_MAX, n_instances=n_instances, strong_width=STRONG_WIDTH, rows=rows)


if __name__ == "__main__":
    t0 = time.time()
    out = run_sweep()
    out_path = ROOT / "data" / "uldk_results.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"\n{len(out['rows'])} Zellen, {time.time()-t0:.0f}s gesamt -> {out_path}")
