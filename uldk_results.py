"""Gefahrgut-Trennung beim Beladeplan - Laden und Auswerten der vorgerechneten Messreihe
(data/uldk_results.json, kombiniert aus Hauptsweep [Standard-Trennvorschrift, 10 Positionen, 27 Zellen,
bitgleich reproduzierbar ggü. packen-planung/messreihe_uld_gefahrgut/sweep_data.json] und der
AP-0-Zusatzmessung [strenge Trennvorschrift, Positionszahl 4/6/10, 27 weitere Zellen], siehe tools/sweep.py).

Anders als bei uld-beladeplan-demo braucht die Live-Hauptansicht KEINE Zell-Suche: beide CP-SAT-Läufe (frei/
mit Trennvorschrift) laufen bei jeder Reglereinstellung frisch (app.py), die Meldung basiert auf der einen
gezeigten Instanz. Diese Datei bedient nur den vorgerechneten Kernabschnitt (Verletzungsrate über den
Gefahrgutanteil, Regime-Tabelle über Positionszahl/Trennvorschrift-Stärke)."""
from __future__ import annotations

import functools
import json
import pathlib

DATA_PATH = pathlib.Path(__file__).parent / "data" / "uldk_results.json"


@functools.lru_cache(maxsize=1)
def load_results(path: pathlib.Path | None = None) -> dict:
    p = path or DATA_PATH
    return json.loads(pathlib.Path(p).read_text(encoding="utf-8"))


def cells(data: dict) -> list[dict]:
    return data["rows"]


def find_cell(data: dict, seg: str, n_pos: int, width: float, dg_share: float, n_ulds: int) -> dict:
    for r in cells(data):
        if (r["seg"] == seg and r["n_pos"] == n_pos and abs(r["width"] - width) < 1e-9
                and abs(r["dg_share"] - dg_share) < 1e-9 and r["n_ulds"] == n_ulds):
            return r
    raise KeyError((seg, n_pos, width, dg_share, n_ulds))


def violation_rate_over_share_rows(data: dict, width: float = 0.5, n_ulds: int = 12) -> list[dict]:
    """Verletzungsrate der freien Lösung über den Gefahrgutanteil (Hauptsweep, Standard-Trennvorschrift, 10
    Positionen, feste Fensterbreite/ULD-Zahl) - Detailplan Abschnitt 1/6, Grafik 1."""
    rows = [r for r in cells(data) if r["seg"] == "standard" and r["n_pos"] == 10
            and abs(r["width"] - width) < 1e-9 and r["n_ulds"] == n_ulds]
    return sorted(rows, key=lambda r: r["dg_share"])


def regime_rows(data: dict, width: float = 0.5, dg_share: float = 0.6, n_ulds: int = 8) -> list[dict]:
    """Wirtschaftlicher Preis über Positionszahl und Trennvorschrift-Stärke bei fester Fensterbreite/
    Gefahrgutanteil/ULD-Zahl (Referenzzelle) - Standard ist nur bei 10 Positionen gemessen (Hauptsweep), streng
    bei allen drei Positionszahlen (AP-0-Zusatzmessung)."""
    rows = [r for r in cells(data) if abs(r["width"] - width) < 1e-9 and abs(r["dg_share"] - dg_share) < 1e-9
            and r["n_ulds"] == n_ulds]
    return sorted(rows, key=lambda r: (r["n_pos"], r["seg"]))


def standard_sweep_rows(data: dict) -> list[dict]:
    """Alle 27 Hauptsweep-Zellen (Standard-Trennvorschrift, 10 Positionen)."""
    return [r for r in cells(data) if r["seg"] == "standard"]


def strong_sweep_rows(data: dict) -> list[dict]:
    """Alle 27 Zellen der AP-0-Zusatzmessung (strenge Trennvorschrift, Positionszahl 4/6/10)."""
    return [r for r in cells(data) if r["seg"] == "streng"]


def mean_violation_rate(rows: list[dict]) -> float:
    return sum(r["violation_rate_free"] for r in rows) / len(rows)


def max_cell(rows: list[dict], key: str) -> dict:
    return max(rows, key=lambda r: r[key])
