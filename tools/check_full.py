"""Volles Bau-Gate (AP 7): wiederholt die Messreihe (tools/sweep.py) und vergleicht das Ergebnis MIT der
eingecheckten data/uldk_results.json.

Wie bei uld-beladeplan-demo verwendet tools/sweep.py `zlib.crc32` für die Zellen-Seeds (Hauptsweep) bzw. eine
davon abgeleitete Formel (AP-0-Zusatzmessung) - das ist über Prozesse und Python-Versionen hinweg stabil. Die
ULD-Ziehung UND der Zielwert (Gewicht) jeder CP-SAT-Lösung sind deshalb bitgleich reproduzierbar, und genau
das bestätigt dieses Gate für ALLE gewichtsbasierten Felder (mean_w_free, mean_w_seg, cost_pct, cost_kg_mean,
cost_kg_max, share_instances_with_cost, exact_optimal_rate).

**Ausnahme, beim Bauen gefunden (AP 7):** `violation_rate_free` ist NICHT bitgleich reproduzierbar. Grund:
der "freie" CP-SAT-Lauf (respect_segregation=False) optimiert nur das Gewicht und kennt die Trennvorschrift
nicht - bei mehreren gewichtsgleichen optimalen Zuordnungen (Gleichstand) ist es reiner Zufall, welche davon
der Solver zurückgibt (`num_search_workers=8`, dieselbe Klasse Nichtdeterminismus wie die CP-SAT-Gleichstand-
Flakiness in uld-beladeplan-demo, siehe `feedback_cp_sat_lexicographic_tiebreak.md`) - und OB die konkret
zurückgegebene Zuordnung die Trennvorschrift verletzt, hängt von genau dieser willkürlichen Wahl ab. Empirisch
bestätigt: bei drei aufeinanderfolgenden vollen Läufen derselben Zelle (width=1.0, dg_share=0.2, n=8) wurden
0,1167 / 0,10 / 0,1333 gemessen - der Zielwert (mean_w_free) blieb in allen drei Läufen exakt identisch. Das
Gate vergleicht `violation_rate_free` deshalb mit einer Toleranz (höchstens 3 von 60 Instanzen, 0,05) statt
bitgleich - alle anderen Felder bleiben exakt.

Aufruf (im Projektordner): _venvs/runtime/Scripts/python.exe tools/check_full.py
(Laufzeit siehe tools/sweep.py - deshalb nicht Teil der CI.)"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from sweep import run_sweep  # noqa: E402

VIOLATION_RATE_TOLERANCE = 3 / 60  # siehe Modul-Docstring: bis zu 3 von 60 Instanzen können kippen


def rows_match(got: dict, exp: dict) -> bool:
    if set(got) != set(exp):
        return False
    for key in got:
        if key == "violation_rate_free":
            if abs(got[key] - exp[key]) > VIOLATION_RATE_TOLERANCE + 1e-9:
                return False
        elif got[key] != exp[key]:
            return False
    return True


def main():
    checked = ROOT / "data" / "uldk_results.json"
    expected = json.loads(checked.read_text(encoding="utf-8"))

    out = run_sweep()

    top_mismatches = [(k, out.get(k), expected[k]) for k in expected if k != "rows" and out.get(k) != expected[k]]
    row_mismatches = []
    if len(out.get("rows", [])) == len(expected["rows"]):
        for i, (got, exp) in enumerate(zip(out["rows"], expected["rows"])):
            if not rows_match(got, exp):
                row_mismatches.append((i, got, exp))
    else:
        row_mismatches.append(("Anzahl Zeilen", len(out.get("rows", [])), len(expected["rows"])))

    ok = not top_mismatches and not row_mismatches
    print(f"Kopfdaten: {'bitgleich' if not top_mismatches else f'{len(top_mismatches)} Abweichungen'}")
    for m in top_mismatches:
        print("   ", m)
    print(f"Zeilen (54 Zellen, violation_rate_free mit Toleranz 3/60): "
          f"{'bestanden' if not row_mismatches else f'{len(row_mismatches)} Abweichungen'}")
    for m in row_mismatches[:5]:
        print("   ", m)
    print()
    print("BAU-GATE BESTANDEN" if ok else "BAU-GATE FEHLGESCHLAGEN")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
