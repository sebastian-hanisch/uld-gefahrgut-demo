"""Abnahmekriterien der fünf Presets (Detailplan Abschnitt 7, Zahlen aus der AP-0-Zusatzmessung) - jedes
einzeln gegen die vorgerechnete Messreihe (data/uldk_results.json) prüfbar, damit ein Preset nie eine
Geschichte erzählt, die die Zahlen nicht tragen."""
from __future__ import annotations

import uldk_constants as C
import uldk_results as R
from uldk_format import fmt_kg, fmt_num, fmt_pct


def _cell_for(name: str, data: dict) -> dict:
    p = C.PRESETS[name]
    return R.find_cell(data, p["seg"], p["n_pos"], p["width"], p["dg_share"], p["n_ulds"])


def check_standard(data: dict) -> tuple[bool, str]:
    cell = _cell_for("Standard", data)
    vio, cost_kg = cell["violation_rate_free"], cell["cost_kg_mean"]
    ok = vio >= 0.50 and cost_kg > 0.0
    return ok, (f"Verletzungsrate frei {fmt_pct(vio)} (>= 50 % erwartet), wirtschaftlicher Preis "
                f"{fmt_kg(cost_kg)} kg im Mittel (> 0 kg erwartet)")


def check_lockere_trennung(data: dict) -> tuple[bool, str]:
    cell = _cell_for("Lockere Trennung", data)
    ok = cell["cost_pct"] == 0.0
    return ok, f"wirtschaftlicher Preis {fmt_num(cell['cost_pct'], 2)} % (== 0,00 % erwartet: milde Trennvorschrift bei 10 Positionen ist kostenlos)"


def check_wenige_positionen(data: dict) -> tuple[bool, str]:
    cell = _cell_for("Wenige Positionen", data)
    standard_cell = _cell_for("Standard", data)
    ok = cell["cost_kg_mean"] > 0.0 and cell["cost_kg_mean"] > standard_cell["cost_kg_mean"]
    return ok, (f"wirtschaftlicher Preis {fmt_kg(cell['cost_kg_mean'])} kg im Mittel bei 4 Positionen "
                f"(> {fmt_kg(standard_cell['cost_kg_mean'])} kg bei 6 Positionen erwartet: weniger Positionen kosten mehr)")


def check_viel_gefahrgut(data: dict) -> tuple[bool, str]:
    cell = _cell_for("Viel Gefahrgut", data)
    vio = cell["violation_rate_free"]
    ok = vio >= 0.80 and cell["cost_pct"] > 0.0
    return ok, f"Verletzungsrate frei {fmt_pct(vio)} (>= 80 % erwartet: die freie Lösung ist hier fast immer unsicher)"


def check_wenig_gefahrgut(data: dict) -> tuple[bool, str]:
    cell = _cell_for("Wenig Gefahrgut", data)
    vio = cell["violation_rate_free"]
    ok = 0.0 < vio <= 0.25
    return ok, f"Verletzungsrate frei {fmt_pct(vio)} (0 % < x <= 25 % erwartet: der Konflikt ist selten, aber nicht null)"


CHECKS = {
    "Standard": check_standard,
    "Lockere Trennung": check_lockere_trennung,
    "Wenige Positionen": check_wenige_positionen,
    "Viel Gefahrgut": check_viel_gefahrgut,
    "Wenig Gefahrgut": check_wenig_gefahrgut,
}


def check_all(data: dict) -> dict[str, tuple[bool, str]]:
    return {name: fn(data) for name, fn in CHECKS.items()}
