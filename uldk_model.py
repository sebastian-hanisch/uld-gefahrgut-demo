"""Gefahrgut-Trennung beim Beladeplan - Datentypen und Bewertung.

Mechanisch übernommen aus zwei Quellen (unverändert in der Logik, nur zusammengeführt, weil dieses Repo
eigenständig ist und zur Laufzeit nicht aus `uld-beladeplan-demo` importieren kann):
  - `packen-planung/messreihe_uld_beladeplan/beladeplan.py` (über `uld-beladeplan-demo/uldb_model.py`, dort
    bereits als eigenständiges Modul aufbereitet): `Position`, `Aircraft`, `moment_of`, `cg_index`, `cg_ok`.
  - `packen-planung/messreihe_uld_gefahrgut/gefahrgut.py` (Vorab-Messreihe, 12 Checks bestanden, siehe
    ERGEBNIS.md): `ULD` (mit Gefahrgutklasse), `adjacent_pairs`, `segregation_violations`, `evaluate`,
    `make_ulds`, `DEFAULT_SEG`, `default_forbidden`.

Zusätzlich `STRONG_SEG` (neu, AP 0 dieses Repos): eine strengere Trennvorschrift, bei der alle drei
Gefahrgutklassen paarweise nicht benachbart stehen dürfen (nicht nur Klasse 1/2 wie bei `DEFAULT_SEG`) - siehe
`tools/sweep.py` für die Zusatzmessung, die zeigt, dass der wirtschaftliche Preis der Trennvorschrift erst mit
`STRONG_SEG` und wenigen Positionen sichtbar wird (README, Abschnitt "Befunde und Korrekturen gegenüber dem
Plan").
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Position:
    name: str
    arm_m: float       # Hebelarm ab Referenzpunkt (Datum), m
    max_weight_kg: float


@dataclass
class Aircraft:
    empty_weight_kg: float
    empty_moment_kgm: float   # empty_weight_kg * empty_arm_m, vorab zusammengefasst
    fuel_kg: float
    fuel_arm_m: float
    cg_min_m: float
    cg_max_m: float


def moment_of(weight_kg: float, arm_m: float) -> float:
    return weight_kg * arm_m


def cg_index(total_weight_kg: float, total_moment_kgm: float) -> float:
    return total_moment_kgm / total_weight_kg if total_weight_kg > 0 else 0.0


def cg_ok(total_weight_kg: float, total_moment_kgm: float, cg_min: float, cg_max: float) -> bool:
    if total_weight_kg <= 0:
        return True
    idx = cg_index(total_weight_kg, total_moment_kgm)
    return cg_min - 1e-9 <= idx <= cg_max + 1e-9


NORMAL = 0  # Klasse 0 = kein Gefahrgut, nie beschränkt


@dataclass
class ULD:
    name: str
    weight_kg: float
    dg_class: int = NORMAL


def adjacent_pairs(positions: list[Position]) -> list[tuple[int, int]]:
    """Nachbarschaft = benachbarte Positionen in der Hebelarm-Reihenfolge (wie im Flugzeug hintereinander)."""
    order = sorted(range(len(positions)), key=lambda i: positions[i].arm_m)
    return [(order[i], order[i + 1]) for i in range(len(order) - 1)]


def segregation_violations(assign: dict[str, str], ulds: list[ULD], positions: dict[str, Position],
                            seg: set[frozenset[int]], forbidden: dict[int, set[str]]) -> int:
    """Zählt Verletzungen: verbotene Positionen (je 1) + verbotene Nachbarschaften (je 1)."""
    n = 0
    uld_by_name = {u.name: u for u in ulds}
    pos_of_uld = {p_name: u_name for u_name, p_name in assign.items()}
    for u_name, p_name in assign.items():
        u = uld_by_name[u_name]
        if p_name in forbidden.get(u.dg_class, set()):
            n += 1
    order = sorted(positions.values(), key=lambda p: p.arm_m)
    for i in range(len(order) - 1):
        a_name = pos_of_uld.get(order[i].name)
        b_name = pos_of_uld.get(order[i + 1].name)
        if a_name is None or b_name is None:
            continue
        ca, cb = uld_by_name[a_name].dg_class, uld_by_name[b_name].dg_class
        if ca == NORMAL or cb == NORMAL:
            continue
        if frozenset((ca, cb)) in seg:
            n += 1
    return n


def evaluate(assign: dict[str, str], ulds: list[ULD], positions: dict[str, Position], ac: Aircraft) -> dict:
    cargo_weight = sum(u.weight_kg for u in ulds if u.name in assign)
    cargo_moment = sum(u.weight_kg * positions[assign[u.name]].arm_m for u in ulds if u.name in assign)
    w_full = ac.empty_weight_kg + ac.fuel_kg + cargo_weight
    m_full = ac.empty_moment_kgm + moment_of(ac.fuel_kg, ac.fuel_arm_m) + cargo_moment
    w_empty = ac.empty_weight_kg + cargo_weight
    m_empty = ac.empty_moment_kgm + cargo_moment
    return dict(
        cargo_weight=cargo_weight, n_loaded=len(assign),
        ok_full=cg_ok(w_full, m_full, ac.cg_min_m, ac.cg_max_m),
        ok_empty=cg_ok(w_empty, m_empty, ac.cg_min_m, ac.cg_max_m),
    )


def make_ulds(rng, n: int, dg_share: float, weight_range=(200.0, 2200.0)) -> list[ULD]:
    ulds = []
    for i in range(n):
        w = float(rng.uniform(*weight_range))
        cls = NORMAL
        if rng.uniform() < dg_share:
            cls = int(rng.integers(1, 4))  # drei Gefahrgutklassen 1..3
        ulds.append(ULD(f"u{i}", w, cls))
    return ulds


# Trennvorschrift (vereinfacht, dem Muster der IATA-DGR-Segregationstabelle nachempfunden): Klasse 1 und 2
# dürfen nicht benachbart stehen (z. B. oxidierend/entzündlich), Klasse 3 ist an den beiden vordersten
# Positionen grundsätzlich verboten (Nähe Cockpit/Crew).
DEFAULT_SEG = {frozenset((1, 2))}

# Strengere Trennvorschrift (AP 0, neu in diesem Repo): alle drei Klassen paarweise nicht benachbart - zeigt
# den wirtschaftlichen Preis der Trennvorschrift auch bei zehn Positionen sichtbar, siehe tools/sweep.py und
# README ("Befunde und Korrekturen gegenüber dem Plan").
STRONG_SEG = {frozenset((1, 2)), frozenset((1, 3)), frozenset((2, 3))}


def default_forbidden(positions: list[Position]) -> dict[int, set[str]]:
    order = sorted(positions, key=lambda p: p.arm_m)
    return {3: {order[0].name, order[1].name}}
