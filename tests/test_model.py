"""Die 12 Korrektheits-Checks aus packen-planung/messreihe_uld_gefahrgut/check.py als pytest, plus der
PFLICHT-Nullspalten-Regressionstest aus AP 0 (Bau-Auftrag): eine konstruierte Instanz, bei der streng +
wenige Positionen tatsächlich einen wirtschaftlichen Preis > 0 erzeugen - sonst hätte die App dieselbe Falle
wie der erste Sweep-Lauf (0,00 % Kosten in allen Zellen, siehe packen-planung/.../ERGEBNIS.md "Beim Bauen
gefunden")."""
from __future__ import annotations

import itertools

import numpy as np
import pytest

from uldk_model import (
    ULD, Aircraft, DEFAULT_SEG, NORMAL, Position, STRONG_SEG, adjacent_pairs, cg_index, cg_ok,
    default_forbidden, evaluate, make_ulds, segregation_violations,
)
from uldk_oracle import solve_exact

POS = [Position(f"p{i}", 6.0 + i * 2.44, 2200.0) for i in range(10)]
POS_BY_NAME = {p.name: p for p in POS}
CENTER = (POS[0].arm_m + POS[-1].arm_m) / 2.0
AC = Aircraft(40000.0, 40000.0 * CENTER, 8000.0, CENTER, CENTER - 0.5, CENTER + 0.5)
FORBIDDEN = default_forbidden(POS)


# --- 1. adjacent_pairs(): drei Positionen mit Hebelarm 5/10/15 -> genau die zwei Nachbarpaare -----------------
def test_check01_adjacent_pairs_zwei_nachbarpaare_in_hebelarm_reihenfolge():
    p3 = [Position("a", 10.0, 1000), Position("b", 5.0, 1000), Position("c", 15.0, 1000)]
    pairs = adjacent_pairs(p3)
    idx = {p.name: i for i, p in enumerate(p3)}
    assert pairs == [(idx["b"], idx["a"]), (idx["a"], idx["c"])]


# --- 2. Verletzungszählung an Handinstanzen --------------------------------------------------------------------
def test_check02_klasse1_neben_klasse2_auf_nachbarpositionen_ist_eine_verletzung():
    u1, u2, u3 = ULD("A", 500, 1), ULD("B", 500, 2), ULD("C", 500, NORMAL)
    assign_bad = {"A": POS[0].name, "B": POS[1].name}
    assert segregation_violations(assign_bad, [u1, u2, u3], POS_BY_NAME, DEFAULT_SEG, {}) == 1


def test_check02b_klasse1_und_2_nicht_benachbart_ist_keine_verletzung():
    u1, u2, u3 = ULD("A", 500, 1), ULD("B", 500, 2), ULD("C", 500, NORMAL)
    assign_ok = {"A": POS[0].name, "B": POS[2].name}
    assert segregation_violations(assign_ok, [u1, u2, u3], POS_BY_NAME, DEFAULT_SEG, {}) == 0


def test_check02c_klasse1_neben_klasse0_kein_gefahrgut_ist_keine_verletzung():
    u1, u2, u3 = ULD("A", 500, 1), ULD("B", 500, 2), ULD("C", 500, NORMAL)
    assign_normal_neighbor = {"A": POS[0].name, "C": POS[1].name}
    assert segregation_violations(assign_normal_neighbor, [u1, u2, u3], POS_BY_NAME, DEFAULT_SEG, {}) == 0


# --- 3. Verbotene Position ---------------------------------------------------------------------------------
def test_check03_klasse3_auf_verbotener_vorderer_position_ist_eine_verletzung():
    u4 = ULD("D", 500, 3)
    front = sorted(POS, key=lambda p: p.arm_m)[0].name
    assert segregation_violations({"D": front}, [u4], POS_BY_NAME, DEFAULT_SEG, FORBIDDEN) == 1


def test_check03b_klasse3_auf_hinterer_position_ist_keine_verletzung():
    u4 = ULD("D", 500, 3)
    back = sorted(POS, key=lambda p: p.arm_m)[-1].name
    assert segregation_violations({"D": back}, [u4], POS_BY_NAME, DEFAULT_SEG, FORBIDDEN) == 0


# --- 4. CP-SAT MIT Trennvorschrift verletzt sie nie --------------------------------------------------------
def test_check04_cp_sat_mit_trennvorschrift_verletzt_sie_nie():
    rng = np.random.default_rng(1)
    violations_found = 0
    for _ in range(40):
        ulds = make_ulds(rng, int(rng.integers(6, 14)), 0.5)
        assign, status, _ = solve_exact(ulds, POS, AC, DEFAULT_SEG, FORBIDDEN, respect_segregation=True, time_limit_s=5.0)
        v = segregation_violations(assign, ulds, POS_BY_NAME, DEFAULT_SEG, FORBIDDEN)
        violations_found += v > 0
    assert violations_found == 0


# --- 5. CP-SAT MIT Trennvorschrift hält weiterhin das Schwerpunktfenster ein --------------------------------
def test_check05_cp_sat_mit_trennvorschrift_haelt_weiterhin_das_schwerpunktfenster_ein():
    rng = np.random.default_rng(1)
    cg_ok_count = n_checked = 0
    for _ in range(40):
        ulds = make_ulds(rng, int(rng.integers(6, 14)), 0.5)
        assign, status, _ = solve_exact(ulds, POS, AC, DEFAULT_SEG, FORBIDDEN, respect_segregation=True, time_limit_s=5.0)
        ev = evaluate(assign, ulds, POS_BY_NAME, AC)
        n_checked += 1
        if ev["ok_full"] and ev["ok_empty"]:
            cg_ok_count += 1
    assert cg_ok_count == n_checked


# --- 6. Monotonie: die Trennvorschrift senkt das geladene Gewicht nie unter das freie Optimum -----------------
def test_check06_trennvorschrift_als_zusatz_nebenbedingung_senkt_das_optimum_nie():
    rng = np.random.default_rng(2)
    monotone_ok = True
    for _ in range(40):
        ulds = make_ulds(rng, int(rng.integers(6, 14)), 0.5)
        a_free, _, _ = solve_exact(ulds, POS, AC, DEFAULT_SEG, FORBIDDEN, respect_segregation=False, time_limit_s=5.0)
        a_seg, _, _ = solve_exact(ulds, POS, AC, DEFAULT_SEG, FORBIDDEN, respect_segregation=True, time_limit_s=5.0)
        w_free = evaluate(a_free, ulds, POS_BY_NAME, AC)["cargo_weight"]
        w_seg = evaluate(a_seg, ulds, POS_BY_NAME, AC)["cargo_weight"]
        if w_seg > w_free + 1e-6:
            monotone_ok = False
    assert monotone_ok


# --- 7. Brute-Force-Referenz auf einer winzigen Instanz ------------------------------------------------------
def test_check07_cp_sat_mit_trennvorschrift_trifft_die_brute_force_referenz():
    ulds_small = [ULD("A", 1200, 1), ULD("B", 900, 2), ULD("C", 1500, NORMAL), ULD("D", 700, 3), ULD("E", 1100, 1)]
    pos_small = POS[:4]
    pos_small_by_name = {p.name: p for p in pos_small}
    forbidden_small = default_forbidden(pos_small)
    names_u = [u.name for u in ulds_small]
    names_p = [p.name for p in pos_small]
    best_w = -1.0
    for k in range(0, len(ulds_small) + 1):
        for u_subset in itertools.combinations(range(len(ulds_small)), k):
            for p_perm in itertools.permutations(names_p, k):
                assign = {names_u[u_subset[i]]: p_perm[i] for i in range(k)}
                ev = evaluate(assign, ulds_small, pos_small_by_name, AC)
                v = segregation_violations(assign, ulds_small, pos_small_by_name, DEFAULT_SEG, forbidden_small)
                if ev["ok_full"] and ev["ok_empty"] and v == 0 and ev["cargo_weight"] > best_w:
                    best_w = ev["cargo_weight"]
    cp_assign, _, _ = solve_exact(ulds_small, pos_small, AC, DEFAULT_SEG, forbidden_small, respect_segregation=True, time_limit_s=5.0)
    cp_w = evaluate(cp_assign, ulds_small, pos_small_by_name, AC)["cargo_weight"]
    assert cp_w == pytest.approx(best_w, abs=1e-6)


# --- 8. Regressionstest (Nullspalten-Falle): die freie Lösung verletzt tatsächlich ---------------------------
def test_check08_regression_freie_loesung_verletzt_auf_klasse1_2_instanz_tatsaechlich():
    ulds_mixed = [ULD(f"a{i}", 1500, 1) for i in range(4)] + [ULD(f"b{i}", 1500, 2) for i in range(4)]
    assign_free, _, _ = solve_exact(ulds_mixed, POS, AC, DEFAULT_SEG, FORBIDDEN, respect_segregation=False, time_limit_s=5.0)
    v_free = segregation_violations(assign_free, ulds_mixed, POS_BY_NAME, DEFAULT_SEG, FORBIDDEN)
    assert v_free > 0


# --- 9. Determinismus -----------------------------------------------------------------------------------------
def test_check09_determinismus_gleicher_seed_gleiche_ulds():
    r1, r2 = np.random.default_rng(9), np.random.default_rng(9)
    u_a, u_b = make_ulds(r1, 8, 0.5), make_ulds(r2, 8, 0.5)
    assert all((a.weight_kg, a.dg_class) == (b.weight_kg, b.dg_class) for a, b in zip(u_a, u_b))


# --- Grenzfälle von cg_ok()/cg_index() (Vorlage: uld-beladeplan-demo/tests/test_model.py) ---------------------
def test_cg_ok_epsilon_grenzen_sind_beidseitig_zulaessig():
    assert cg_ok(1.0, 16.0 - 1e-9, 16.0, 18.0)
    assert cg_ok(1.0, 18.0 + 1e-9, 16.0, 18.0)


def test_cg_ok_knapp_ueber_oberer_grenze_ist_unzulaessig():
    assert not cg_ok(1000.0, 1000.0 * 18.001, 16.0, 18.0)


def test_cg_index_von_gewicht_null_ist_null_ohne_division_durch_null():
    assert cg_index(0.0, 0.0) == 0.0


# --- Grenzfall aus dem Fehler-Einbau-Test: make_ulds() muss wirklich alle drei Gefahrgutklassen erzeugen ------
def test_make_ulds_erzeugt_alle_drei_gefahrgutklassen_ueber_viele_ziehungen():
    """Schließt eine vom Fehler-Einbau-Test (tools/mutation_check.py) aufgedeckte Lücke: rng.integers(1, 4)
    (High-Grenze exklusiv) muss die Klassen 1, 2 UND 3 liefern - ein Off-by-one (rng.integers(1, 3)) würde
    Klasse 3 nie ziehen, ohne dass es bisher ein Test bemerkt hätte."""
    rng = np.random.default_rng(0)
    ulds = make_ulds(rng, 300, 0.9)
    assert {u.dg_class for u in ulds} == {0, 1, 2, 3}


# --- PFLICHT: Nullspalten-Regressionstest aus AP 0 -------------------------------------------------------------
def test_ap0_regression_streng_und_wenige_positionen_erzeugt_einen_wirtschaftlichen_preis():
    """Konstruierte Instanz (keine Zufallsziehung): 4 Positionen, vier ULDs mit den Klassen 1/2/3/1 - unter
    STRONG_SEG (alle drei Klassen paarweise verboten) gibt es KEINE Anordnung der vier ULDs auf vier
    sequenziellen Positionen, die alle Nachbarschaften zulässig hält (nur ein Klassenpaar - hier die beiden
    Klasse-1-ULDs - darf benachbart stehen, die Klassen 2 und 3 kommen aber je nur einmal vor und müssten an
    JEDEM ihrer beiden möglichen Nachbarn - inklusive dem freien Rand - neben einer anderen, andersartigen
    Klasse stehen). Die Trennvorschrift-Nebenbedingung MUSS deshalb mindestens ein ULD abweisen -> ein
    wirtschaftlicher Preis > 0, unabhängig vom Zufall. Genau das ist die AP-0-Lücke aus dem Hauptsweep (dort
    immer 0,00 % bei 10 Positionen/milder Trennvorschrift): dieser Test schließt sie strukturell, nicht nur
    stichprobenartig."""
    pos4 = [Position(f"p{i}", 6.0 + i * 2.0, 2200.0) for i in range(4)]
    pos4_by_name = {p.name: p for p in pos4}
    forbidden4 = default_forbidden(pos4)
    center = (pos4[0].arm_m + pos4[-1].arm_m) / 2.0
    ac_wide = Aircraft(40000.0, 40000.0 * center, 8000.0, center, center - 50.0, center + 50.0)  # CG nie bindend
    ulds = [ULD("A", 2200.0, 1), ULD("B", 2200.0, 2), ULD("C", 2200.0, 3), ULD("D", 2200.0, 1)]

    a_free, st_free, _ = solve_exact(ulds, pos4, ac_wide, STRONG_SEG, forbidden4, respect_segregation=False, time_limit_s=5.0)
    a_seg, st_seg, _ = solve_exact(ulds, pos4, ac_wide, STRONG_SEG, forbidden4, respect_segregation=True, time_limit_s=5.0)
    ev_free = evaluate(a_free, ulds, pos4_by_name, ac_wide)
    ev_seg = evaluate(a_seg, ulds, pos4_by_name, ac_wide)

    assert ev_free["n_loaded"] == 4  # frei: alle vier passen (Gewicht und CG unbindend)
    assert ev_seg["n_loaded"] < 4  # mit Trennvorschrift: mindestens eins muss draußen bleiben
    assert ev_free["cargo_weight"] - ev_seg["cargo_weight"] > 0.0
    assert segregation_violations(a_seg, ulds, pos4_by_name, STRONG_SEG, forbidden4) == 0
