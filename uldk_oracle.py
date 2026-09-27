"""Gefahrgut-Trennung beim Beladeplan - der exakte Löser (CP-SAT).

Mechanisch aus `packen-planung/messreihe_uld_gefahrgut/gefahrgut.py` übernommen (dort gegen 12 Checks
verifiziert, siehe ERGEBNIS.md), unverändert. `ortools` wird LAZY importiert (erst beim Aufruf von
`solve_exact`), wie in `uldb_oracle.py` - hier aber ohnehin immer gerechnet (beide Läufe, frei und mit
Trennvorschrift, laufen bei jeder Einstellung live, kein separater Exakt-Tab, siehe app.py)."""
from __future__ import annotations

from uldk_model import Aircraft, Position, ULD, moment_of

SCALE = 100
ARM_SCALE = 1000


def solve_exact(ulds: list[ULD], positions: list[Position], ac: Aircraft,
                 seg: set[frozenset[int]], forbidden: dict[int, set[str]],
                 respect_segregation: bool, time_limit_s: float = 10.0):
    """CP-SAT wie in uldb_oracle.solve_exact, optional mit Trennvorschrift als Nebenbedingung."""
    from ortools.sat.python import cp_model

    model = cp_model.CpModel()
    n, m = len(ulds), len(positions)
    x = {(i, j): model.NewBoolVar(f"x_{i}_{j}") for i in range(n) for j in range(m)}

    for i in range(n):
        model.Add(sum(x[i, j] for j in range(m)) <= 1)
    for j in range(m):
        model.Add(sum(x[i, j] for i in range(n)) <= 1)
        model.Add(sum(x[i, j] * int(round(ulds[i].weight_kg * SCALE)) for i in range(n))
                   <= int(round(positions[j].max_weight_kg * SCALE)))
        if respect_segregation:
            for i in range(n):
                if positions[j].name in forbidden.get(ulds[i].dg_class, set()):
                    model.Add(x[i, j] == 0)

    def add_cg_constraints(W0: float, M0: float):
        lhs_min = sum(x[i, j] * int(round(ulds[i].weight_kg * (positions[j].arm_m - ac.cg_min_m) * ARM_SCALE))
                       for i in range(n) for j in range(m))
        rhs_min = int(round((ac.cg_min_m * W0 - M0) * ARM_SCALE))
        model.Add(lhs_min >= rhs_min)
        lhs_max = sum(x[i, j] * int(round(ulds[i].weight_kg * (ac.cg_max_m - positions[j].arm_m) * ARM_SCALE))
                       for i in range(n) for j in range(m))
        rhs_max = int(round((M0 - ac.cg_max_m * W0) * ARM_SCALE))
        model.Add(lhs_max >= rhs_max)

    W0_full = ac.empty_weight_kg + ac.fuel_kg
    M0_full = ac.empty_moment_kgm + moment_of(ac.fuel_kg, ac.fuel_arm_m)
    add_cg_constraints(W0_full, M0_full)
    add_cg_constraints(ac.empty_weight_kg, ac.empty_moment_kgm)

    if respect_segregation:
        order = sorted(range(m), key=lambda j: positions[j].arm_m)
        for a_idx in range(len(order) - 1):
            jA, jB = order[a_idx], order[a_idx + 1]
            for i1 in range(n):
                for i2 in range(n):
                    if i1 == i2:
                        continue
                    if frozenset((ulds[i1].dg_class, ulds[i2].dg_class)) in seg:
                        model.Add(x[i1, jA] + x[i2, jB] <= 1)

    # Lexikografischer Zweitterm: bei mehreren gewichtsgleich optimalen Zuordnungen entscheidet CP-SAT mit
    # einem einzelnen Zielterm nicht deterministisch zwischen Prozessen/Plattformen (Ties werden je nach
    # Thread-Zeitplan unterschiedlich aufgelöst - beim ersten CI-Lauf gefunden: derselbe Zielwert, aber eine
    # andere Zuordnung, wodurch eine auf einer bestimmten Instanz erwartete Meldung je nach Umgebung
    # unterschiedlich ausfiel). PRIMARY_SCALE ist größer als der maximal mögliche Primärwert, damit der
    # Zweitterm niemals eine Gewichtsentscheidung verändert, nur unter gleich guten Zuordnungen wählt.
    PRIMARY_SCALE = 1000
    primary = sum(x[i, j] * int(round(ulds[i].weight_kg * SCALE)) for i in range(n) for j in range(m))
    tiebreak = sum(x[i, j] * (i * m + j) for i in range(n) for j in range(m))
    model.Maximize(primary * PRIMARY_SCALE - tiebreak)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_s
    # Einzelner Suchprozess + fester random_seed: der lexikografische Zweitterm oben verkleinert die
    # Gleichstands-Klasse, hebt sie aber nicht vollständig auf (eine Summe über Positionsindizes ist keine
    # echte lexikografische Ordnung - verschiedene Zuordnungen können dieselbe Summe ergeben). Mit
    # num_search_workers=8 wettlaufen mehrere Suchprozesse parallel um den ersten gefundenen optimalen Wert;
    # bei echtem Gleichstand im Zweitterm entscheidet dann die Thread-Ankunftsreihenfolge, die von Lauf zu Lauf
    # variiert (durch wiederholte Läufe auf DERSELBEN Maschine nachgewiesen, nicht nur zwischen Plattformen -
    # betraf z. B. den eingefrorenen Fall seed=3 in tests/data/uldk_frozen.json und den App-Zustand seed=24 in
    # tests/test_app.py). Ein einzelner Suchprozess mit festem Seed macht CP-SATs Suche vollständig
    # reproduzierbar (dieselbe Eingabe -> derselbe Suchpfad -> dieselbe Lösung, unabhängig von Plattform/
    # Threadplanung), ohne den Zweitterm selbst zu verändern.
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = 12345
    status = solver.Solve(model)
    assign = {}
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for i in range(n):
            for j in range(m):
                if solver.Value(x[i, j]):
                    assign[ulds[i].name] = positions[j].name
    return assign, status, solver
