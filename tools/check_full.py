"""Volles Bau-Gate (AP 7): wiederholt die Messreihe (tools/sweep.py) und vergleicht das Ergebnis MIT der
eingecheckten data/uldk_results.json.

Wie bei uld-beladeplan-demo verwendet tools/sweep.py `zlib.crc32` für die Zellen-Seeds (Hauptsweep) bzw. eine
davon abgeleitete Formel (AP-0-Zusatzmessung) - das ist über Prozesse und Python-Versionen hinweg stabil. Die
ULD-Ziehung UND der Zielwert (Gewicht) jeder CP-SAT-Lösung sind deshalb bitgleich reproduzierbar, und genau
das bestätigt dieses Gate für ALLE gewichtsbasierten Felder (mean_w_free, mean_w_seg, cost_pct, cost_kg_mean,
cost_kg_max, share_instances_with_cost, exact_optimal_rate).

**Frühere Ausnahme, jetzt behoben (AP 7 / CI-Fund):** `violation_rate_free` war ursprünglich NICHT bitgleich
reproduzierbar. Grund: der "freie" CP-SAT-Lauf (respect_segregation=False) optimiert nur das Gewicht und kennt
die Trennvorschrift nicht - bei mehreren gewichtsgleichen optimalen Zuordnungen (Gleichstand) entschied
`num_search_workers=8` (mehrere parallele Suchprozesse wetteifern um die erste gefundene Lösung) willkürlich,
welche davon zurückgegeben wird, und OB die konkret zurückgegebene Zuordnung die Trennvorschrift verletzt,
hing von genau dieser Wahl ab - reproduzierbar sogar innerhalb WIEDERHOLTER Läufe auf derselben Maschine, nicht
nur zwischen Plattformen (derselbe CI-Fund, der zum lexikografischen Zweitterm in uldk_oracle.py führte - der
Zweitterm allein reichte aber nicht, weil eine Summe über Positionsindizes keine echte lexikografische Ordnung
ist). Behoben durch `solver.parameters.num_search_workers = 1` + festen `random_seed` (uldk_oracle.py) - macht
CP-SATs Suche vollständig deterministisch, dieses Gate vergleicht `violation_rate_free` deshalb jetzt wieder
bitgleich wie alle anderen Felder, keine Toleranz mehr nötig.

Aufruf (im Projektordner): _venvs/runtime/Scripts/python.exe tools/check_full.py
(Laufzeit siehe tools/sweep.py - deshalb nicht Teil der CI.)"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from sweep import run_sweep  # noqa: E402


def rows_match(got: dict, exp: dict) -> bool:
    if set(got) != set(exp):
        return False
    for key in got:
        if got[key] != exp[key]:
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
    print(f"Zeilen (54 Zellen, alle Felder bitgleich): "
          f"{'bestanden' if not row_mismatches else f'{len(row_mismatches)} Abweichungen'}")
    for m in row_mismatches[:5]:
        print("   ", m)
    print()
    print("BAU-GATE BESTANDEN" if ok else "BAU-GATE FEHLGESCHLAGEN")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
