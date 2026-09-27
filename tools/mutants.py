"""Handverlesene Mutantenliste für uldk_model.py: jede alte Stelle kommt im Modul genau einmal vor. Wie bei
uld-beladeplan-demo (siehe dortiges tools/mutants.py) deckt eine handverlesene Liste bei einem einzigen,
mechanisch übernommenen Kernmodul jede Vergleichsoperation, jede Vorzeichen-/Faktor-Stelle und jede
Sortierordnung ab, ohne die Maschinerie eines Generators zu brauchen. `uldk_oracle.py` (CP-SAT) wird - wie
`uldb_oracle.py` bei der Schwesterdemo - NICHT mutiert: die Solver-Aufrufe selbst sind kein sinnvolles
Mutationsziel, ihre Korrektheit steckt in den Nebenbedingungen, die test_model.py bereits gegen eine
Brute-Force-Referenz und gegen Monotonie prüft.

EQUIVALENT_NOTES wird nach dem ersten vollen Lauf mit der tatsächlichen Einordnung der Überlebenden gefüllt."""
EQUIVALENT_NOTES = """Stand nach zwei vollen Läufen (--jobs 1, 16 handverlesene Mutanten): Lauf 1 fand 12,
4 überlebten; nach dem Schließen einer echten Testlücke (tests/test_model.py::
test_make_ulds_erzeugt_alle_drei_gefahrgutklassen_ueber_viele_ziehungen - rng.integers(1, 4) -> rng.integers(1, 3)
hätte Klasse 3 nie erzeugt, kein bisheriger Test bemerkte das) fand der zweite Lauf 13 von 16, 3 überlebten -
alle drei beweisbar/strukturell gleichwertig:

(1) `if total_weight_kg <= 0:` -> `< 0`: cg_ok() wird in diesem Modul nur aus evaluate() heraus aufgerufen,
    mit w_full/w_empty = ac.empty_weight_kg (fest 40.000 kg) + optional Fracht - total_weight_kg ist hier
    IMMER > 0, nie exakt 0. Der Unterschied zwischen `<=` und `<` ist an dieser Stelle unerreichbarer Code
    (dieselbe Klasse wie das "cg_full=... if w_full > 0"-Äquivalent in uld-beladeplan-demo/tools/mutants.py).
(2) `if ca == NORMAL or cb == NORMAL: continue` -> `and`: der Unterschied wäre nur sichtbar, wenn GENAU eine
    der beiden Nachbar-ULDs Klasse 0 (kein Gefahrgut) hat und `frozenset((0, andere_klasse))` in `seg` läge -
    aber sowohl DEFAULT_SEG als auch STRONG_SEG enthalten ausschließlich Paare aus {1, 2, 3}, nie die 0. Die
    `continue`-Abkürzung ist eine reine Falls-genau-dann-unnötige-Prüfung-vermeiden-Optimierung ohne
    beobachtbaren Effekt auf das Ergebnis - mathematisch gleichwertig zu jeder Alternative an dieser Stelle,
    solange NORMAL nie in einem Segregationspaar vorkommt (was beide Konstanten-Definitionen strukturell
    garantieren).
(3) `if rng.uniform() < dg_share:` -> `<=`: `rng.uniform()` zieht aus einer stetigen Gleichverteilung auf
    [0, 1) - die Wahrscheinlichkeit, exakt den Fließkommawert von dg_share (0.2/0.4/0.6) zu treffen, ist
    praktisch 0 (dieselbe Klasse wie die 1e-9-Rundungstoleranzen in cg_ok(), siehe uld-beladeplan-demo
    tools/mutants.py für dasselbe Muster)."""

MUTANTS = [
    # --- cg_index / cg_ok (aus uldb_model.py übernommen, identische Logik) --------------------------------
    ("uldk_model.py", "return total_moment_kgm / total_weight_kg if total_weight_kg > 0 else 0.0",
     "return total_moment_kgm / total_weight_kg if total_weight_kg >= 0 else 0.0"),
    ("uldk_model.py", "if total_weight_kg <= 0:\n        return True",
     "if total_weight_kg < 0:\n        return True"),
    ("uldk_model.py", "return cg_min - 1e-9 <= idx <= cg_max + 1e-9",
     "return cg_min - 1e-9 < idx <= cg_max + 1e-9"),
    ("uldk_model.py", "return cg_min - 1e-9 <= idx <= cg_max + 1e-9",
     "return cg_min - 1e-9 <= idx < cg_max + 1e-9"),
    # --- evaluate() -------------------------------------------------------------------------------------
    ("uldk_model.py", "w_full = ac.empty_weight_kg + ac.fuel_kg + cargo_weight",
     "w_full = ac.empty_weight_kg + cargo_weight"),
    ("uldk_model.py", "m_full = ac.empty_moment_kgm + moment_of(ac.fuel_kg, ac.fuel_arm_m) + cargo_moment",
     "m_full = ac.empty_moment_kgm + cargo_moment"),
    ("uldk_model.py", "m_empty = ac.empty_moment_kgm + cargo_moment", "m_empty = ac.empty_moment_kgm"),
    ("uldk_model.py", "cargo_weight = sum(u.weight_kg for u in ulds if u.name in assign)",
     "cargo_weight = sum(u.weight_kg for u in ulds if u.name in assign) * 1.01"),
    ("uldk_model.py", "n_loaded=len(assign),", "n_loaded=len(assign) + 1,"),
    # --- adjacent_pairs() ---------------------------------------------------------------------------------
    ("uldk_model.py", "return [(order[i], order[i + 1]) for i in range(len(order) - 1)]",
     "return [(order[i + 1], order[i]) for i in range(len(order) - 1)]"),
    # --- segregation_violations() -------------------------------------------------------------------------
    ("uldk_model.py", "if p_name in forbidden.get(u.dg_class, set()):\n            n += 1",
     "if p_name not in forbidden.get(u.dg_class, set()):\n            n += 1"),
    ("uldk_model.py", "if ca == NORMAL or cb == NORMAL:\n            continue",
     "if ca == NORMAL and cb == NORMAL:\n            continue"),
    ("uldk_model.py", "if frozenset((ca, cb)) in seg:\n            n += 1",
     "if frozenset((ca, cb)) not in seg:\n            n += 1"),
    # --- make_ulds() ---------------------------------------------------------------------------------------
    ("uldk_model.py", "if rng.uniform() < dg_share:", "if rng.uniform() <= dg_share:"),
    ("uldk_model.py", "cls = int(rng.integers(1, 4))  # drei Gefahrgutklassen 1..3",
     "cls = int(rng.integers(1, 3))  # drei Gefahrgutklassen 1..3"),
    # --- default_forbidden() --------------------------------------------------------------------------------
    ("uldk_model.py", "return {3: {order[0].name, order[1].name}}", "return {3: {order[0].name}}"),
]
