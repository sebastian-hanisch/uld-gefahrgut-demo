"""Orakel-Regressionstest (Gefahrgut-Trennung): CP-SAT-Optimum beider Läufe gegen Brute Force über alle Teilzuordnungen.

Unabhängig vom Code der Demo: Zulässigkeit (Positionsgrenze, Schwerpunktfenster bei vollem und leerem Tank, Trennvorschrift) wird
hier neu geprüft, nicht über `evaluate`/`segregation_violations`, und das größte zulässige Ladegewicht per Aufzählung bestimmt.
Dazu: ein Preis > 0 darf nur entstehen, wenn KEINE gewichtsoptimale freie Zuordnung sicher ist."""
from __future__ import annotations

import itertools

import numpy as np
import pytest

import uldk_constants as C
from uldk_model import DEFAULT_SEG, STRONG_SEG, default_forbidden, make_ulds, segregation_violations
from uldk_oracle import solve_exact


def _violations(assign, ulds, positions, pairs):
    order = sorted(range(len(positions)), key=lambda j: positions[j].arm_m)
    rank = {positions[j].name: r for r, j in enumerate(order)}
    cls = {u.name: u.dg_class for u in ulds}
    at, v = {}, 0
    for u, p in assign.items():
        at[rank[p]] = cls[u]
        v += cls[u] == 3 and rank[p] < 2
    for r in range(len(order) - 1):
        a, b = at.get(r), at.get(r + 1)
        if a and b and (min(a, b), max(a, b)) in pairs:
            v += 1
    return v


def _feasible(assign, ulds, positions, ac):
    w = {u.name: u.weight_kg for u in ulds}
    arm = {p.name: p.arm_m for p in positions}
    cap = {p.name: p.max_weight_kg for p in positions}
    if any(w[u] > cap[p] for u, p in assign.items()):
        return False
    cw = sum(w[u] for u in assign)
    cm = sum(w[u] * arm[p] for u, p in assign.items())
    for w0, m0 in ((ac.empty_weight_kg + ac.fuel_kg, ac.empty_moment_kgm + ac.fuel_kg * ac.fuel_arm_m), (ac.empty_weight_kg, ac.empty_moment_kgm)):
        if not ac.cg_min_m - 1e-6 <= (m0 + cm) / (w0 + cw) <= ac.cg_max_m + 1e-6:
            return False
    return True


def _brute(ulds, positions, ac, pairs, respect):
    best, optimal = -1.0, []
    for k in range(min(len(ulds), len(positions)) + 1):
        for us in itertools.combinations(range(len(ulds)), k):
            for ps in itertools.permutations(range(len(positions)), k):
                a = {ulds[u].name: positions[p].name for u, p in zip(us, ps)}
                if not _feasible(a, ulds, positions, ac) or (respect and _violations(a, ulds, positions, pairs)):
                    continue
                w = sum(ulds[u].weight_kg for u in us)
                if w > best + 1e-6:
                    best, optimal = w, [a]
                elif abs(w - best) <= 1e-6:
                    optimal.append(a)
    return best, optimal


@pytest.mark.parametrize("strong", [False, True])
def test_both_runs_match_brute_force_and_a_price_needs_every_free_optimum_to_be_unsafe(strong):
    pytest.importorskip("ortools")
    seg, pairs = (STRONG_SEG, {(1, 2), (1, 3), (2, 3)}) if strong else (DEFAULT_SEG, {(1, 2)})
    rng = np.random.default_rng(7 + strong)
    for _ in range(18):
        n, m = int(rng.integers(3, 6)), int(rng.integers(3, 5))
        positions = C.make_positions(m)
        ac = C.make_aircraft(float(rng.choice([0.1, 0.5, 1.0])))
        ulds = make_ulds(rng, n, float(rng.choice([0.4, 0.8, 1.0])))
        forbidden = default_forbidden(positions)
        by_name = {p.name: p for p in positions}
        weights, free_optima = {}, []
        for respect in (False, True):
            a, status, _ = solve_exact(ulds, positions, ac, seg, forbidden, respect_segregation=respect, time_limit_s=10.0)
            best, optimal = _brute(ulds, positions, ac, pairs, respect)
            w = sum(u.weight_kg for u in ulds if u.name in a)
            assert status == 4 and _feasible(a, ulds, positions, ac)
            assert w == pytest.approx(best, abs=0.02)
            assert _violations(a, ulds, positions, pairs) == segregation_violations(a, ulds, by_name, seg, forbidden)
            if respect:
                assert _violations(a, ulds, positions, pairs) == 0
            else:
                free_optima = optimal
            weights[respect] = w
        assert weights[True] <= weights[False] + 0.02
        if weights[False] - weights[True] > 0.02:
            assert all(_violations(a, ulds, positions, pairs) > 0 for a in free_optima)
