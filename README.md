# ☣️ Gefahrgut-Trennung: sicher UND schwer beladen?

*(noch nicht deployed)*

Drittes Stück der Packen-Ausbaulinie, baut auf [`uld-beladeplan-demo`](https://github.com/sebastian-hanisch/uld-beladeplan-demo)
(Stück 2) auf. Dort kennt die Zuordnung ULD→Position nur Gewicht und Schwerpunkt. In der Praxis dürfen
bestimmte Gefahrgutklassen nicht auf **benachbarten** Laderaumpositionen stehen (Trennvorschrift, vereinfacht
nach dem Muster der IATA-DGR-Trenntabelle), manche Klassen sind an bestimmten Positionen grundsätzlich
verboten. Wie oft erzeugt eine gewichts-/schwerpunktoptimale Zuordnung, die die Trennvorschrift nicht kennt,
tatsächlich eine **unsichere** Zuordnung - und was kostet die Einhaltung an Ladegewicht? Die Demo rechnet
**zwei CP-SAT-Läufe live** (🔓 frei / 🔒 mit Trennvorschrift) für eine Instanz, und vorgerechnet über **60
Instanzen je Zelle** (54 Zellen: 27 Hauptsweep + 27 AP-0-Zusatzmessung), die die Aussage trägt.

## Warum dieses Problem

„Gefahrgut" steht in mindestens fünf Demo-READMEs des Portfolios (`bahnladeplan-demo`, `blockzuweisung-demo`,
`freight_demo`, `stapelplanung-demo`, `stauplanung-demo`) als **nie umgesetzte** Erweiterung - eine echte
Lücke, die dieses Stück schließt. Inhaltlich am engsten mit `uld-beladeplan-demo` verwandt (baut direkt auf
dessen Code auf), aber ein eigenständiges Stück, weil der Aufhänger („wie oft ist eine gewichts-/
schwerpunktoptimale Zuordnung gleichzeitig eine gefährliche?") eine andere Frage ist als „wie viel Gewicht
verliere ich durch Balance-Regeln" (Stück 2).

## Modell

- **Aufbau wie Stück 2:** Flugzeug mit Schwerpunktfenster an beiden Zeitpunkten (voller/leerer Tank, Breite
  als Regler ±0,3/0,5/1,0 m), Laderaumpositionen gleichmäßig von Hebelarm 6,0 bis 28,0 m verteilt, je 2.200 kg
  Gewichtsgrenze. **Neu:** die **Positionszahl ist selbst ein Regler** (4/6/10 - siehe AP 0 unten).
- **Gefahrgutklasse je ULD:** 0 = kein Gefahrgut (nie beschränkt), 1-3 = drei Gefahrgutklassen; Anteil mit
  Gefahrgut als Regler (20/40/60 %).
- **Trennvorschrift „Standard":** Klasse 1 und 2 dürfen nicht auf benachbarten Positionen stehen (Nachbarschaft
  = aufeinanderfolgend in Hebelarm-Reihenfolge), Klasse 3 ist an den beiden vordersten Positionen
  grundsätzlich verboten.
- **Trennvorschrift „streng":** zusätzlich sind auch Klasse 1/3 und 2/3 benachbart verboten - alle drei
  Klassen paarweise getrennt (neu in diesem Repo, AP 0).
- **Zwei CP-SAT-Läufe je Instanz, beide exakt:** 🔓 **frei** (maximiert Ladegewicht unter Kapazität und
  Schwerpunktfenster, kennt die Trennvorschrift nicht) gegen 🔒 **mit Trennvorschrift** (dieselbe Zielfunktion,
  zusätzlich die Trenn- und Verbotsregeln als harte Nebenbedingung) - anders als bei Stück 2 gibt es **keine
  Heuristik**, weil die Instanzgröße den exakten Löser auf beiden Seiten erlaubt.

Flugzeug- und Positionsdaten erfunden, nicht kalibriert (wie bei `uld-beladeplan-demo`). Die Trennvorschrift
ist stark vereinfacht - keine Übernahme der echten, deutlich umfangreicheren IATA-DGR-Tabelle.

## Befunde (gemessen, keine Behauptungen)

Alle Zahlen aus `data/uldk_results.json`, nachgerechnet in `tests/test_claims.py`.

| Frage | Befund |
|---|---|
| Verletzt eine Regel ohne Gefahrgutwissen die Trennvorschrift? | Ja, oft: im Mittel über alle 27 Hauptsweep-Zellen **41,8 %** der Instanzen, Maximum **80,0 %** (±0,3 m, 60 % Gefahrgutanteil, 16 ULDs), Minimum 11,7 %. |
| Treibt der Gefahrgutanteil die Verletzungsrate stärker als das Schwerpunktfenster? | Ja: bei ±0,5 m, 12 ULDs steigt sie mit dem Anteil 20/40/60 % von **26,7 % auf 35,0 % auf 68,3 %**. |
| Kostet die Einhaltung der Standard-Trennvorschrift bei 10 Positionen Ladegewicht? | **Nein, nie** - in allen 27 Hauptsweep-Zellen exakt 0,00 %. |
| Kostet die Einhaltung der strengen Trennvorschrift bei 10 Positionen Ladegewicht? | **Fast nie** - in 8 von 9 gemessenen Zellen exakt 0,00 %, nur bei 60 % Gefahrgutanteil und 16 ULDs ein kleiner realer Preis (0,37 %, 56,9 kg). |
| Wird der Preis real, wenn Positionen knapp werden? | Ja: bei 4-6 Positionen und strenger Trennvorschrift entsteht in 14 von 27 gemessenen Zellen ein Preis > 0, bis zu **1,93 %** (124,2 kg im Mittel, Maximum 1.245,8 kg). |
| Ist CP-SAT verlässlich exakt? | Ja: in allen gemessenen Instanzen (Hauptsweep und Zusatzmessung) wurde das bewiesene Optimum gefunden. |

**Warum „0 % Kosten bei 10 Positionen" erst stressgetestet wurde, bevor es als Befund galt:** eine Kennzahl,
die über 27 von 27 Zellen exakt 0,00 % ist, ist ein Nullspalten-Verdacht, kein automatischer Erfolg (siehe
DEMO-PLAYBOOK Abschnitt 4/8, `feedback_all_zero_result_column_is_a_bug_signal.md`). Genau deshalb verlangt AP 0
die Zusatzmessung oben - sie bestätigt den Nullbefund als real (mit derselben Nebenbedingung, die
`tests/test_ap0_regression_streng_und_wenige_positionen_erzeugt_einen_wirtschaftlichen_preis` strukturell
beweist), zeigt aber auch, wo er endet.

## Ehrliche Grenzen

- Die Trennvorschrift ist stark vereinfacht (drei Klassen, ein bzw. drei verbotene Paare, eine
  Positionsbeschränkung) - keine Übernahme der echten, deutlich umfangreicheren IATA-DGR-Tabelle.
- Nachbarschaft ist eindimensional (nur die Hebelarm-Reihenfolge); reale Frachträume haben auch seitliche und
  vertikale Nachbarschaft, hier nicht modelliert.
- Flugzeug- und Positionsdaten erfunden, nicht kalibriert.
- Die Zusatzmessung hält die Fensterbreite auf 0,5 m fest (siehe „Befunde und Korrekturen" oben) - der
  Zusammenhang zwischen Fensterbreite und dem wirtschaftlichen Preis der Trennvorschrift bei wenigen
  Positionen wurde nicht gemessen.
- Keine Heuristik als Kontrast zu CP-SAT (anders als Stück 2) - beide Seiten des Vergleichs sind exakt.

## Befunde und Korrekturen gegenüber dem Plan

Der freigegebene Detailplan (`packen-planung/plan_uld_gefahrgut.py`) sah als AP 0 (Pflicht vor dem Bau) eine
Zusatzmessung vor, weil der Hauptsweep der Vorab-Messreihe (`packen-planung/messreihe_uld_gefahrgut/`) bei 10
Positionen und der milden Standard-Trennvorschrift in **allen 27 Zellen** einen wirtschaftlichen Preis von
exakt 0,00 % zeigt - real (kein Bug), aber wirkungslos für eine Demo, deren ganzer Punkt der Zielkonflikt ist.

**Durchgeführte Zusatzmessung (AP 0):** dieselbe Sweep-Logik wie der Hauptsweep, aber mit der neuen strengen
Trennvorschrift (`STRONG_SEG`, alle drei Klassen paarweise verboten) und Positionszahl (`n_pos`) ∈ {4, 6, 10}
als zusätzliche Sweep-Dimension, bei sonst denselben Reglern (Gefahrgutanteil, ULD-Zahl) wie im Hauptsweep -
**27 weitere Zellen**, 60 Instanzen je Zelle, macht 54 Zellen insgesamt (`data/uldk_results.json`,
`tools/sweep.py`). **Gekürzt gegenüber der vollen 3×3×3×3=81-Zellen-Kreuztabelle:** die Fensterbreite wurde
für die Zusatzmessung auf 0,5 m (Standardwert) **festgehalten**, nicht mitvariiert - ehrlich begründet: (1)
keiner der fünf Presets variiert die Fensterbreite, (2) ihr Effekt ist im Hauptsweep bereits gemessen
(schwächerer Treiber als der Gefahrgutanteil), (3) die App rechnet die Hauptansicht ohnehin **immer live**
(beide CP-SAT-Läufe), die Messreihe bedient nur die vorgerechneten Kernabschnitt-Grafiken, nicht eine
Zelle-für-jede-Reglerkombination-Suche wie bei `uld-beladeplan-demo`. Rechenzeit: Hauptsweep + Zusatzmessung
zusammen unter 5 Minuten (`tools/sweep.py`, 54 Zellen × 60 Instanzen × 2 CP-SAT-Läufe = 6.480 Läufe).

**Der zentrale, im Plan nicht erwartete Befund:** selbst die **strenge** Trennvorschrift kostet bei **10
Positionen** in **8 von 9** gemessenen Zellen exakt 0,00 % - nur die extremste Zelle (60 % Gefahrgutanteil, 16
ULDs) zeigt einen kleinen realen Preis (0,37 %, 56,9 kg im Mittel). Ein wirtschaftlicher Preis entsteht erst
zuverlässig, wenn Positionen **knapp** (4-6) UND die Trennvorschrift **streng** ist - und selbst dann nur in
gut der Hälfte der 18 so gemessenen Zellen (14 von 27 Zellen der Zusatzmessung insgesamt haben überhaupt einen
Preis > 0). Größter gemessener Preis: 4 Positionen, 60 % Gefahrgutanteil, 8 ULDs - **1,93 %** (124,2 kg im
Mittel, Maximum 1.245,8 kg, in 23,3 % der 60 Instanzen überhaupt ein messbarer Verlust).

**Korrektur der Presets:** der Plan-Platzhalter für „Standard" (10 Positionen, streng, 40 % Gefahrgutanteil,
12 ULDs) zeigt real **0,00 % Kosten** (siehe Befund oben) - AP 0 hat deshalb die tatsächlichen Reglerwerte
geliefert, die live einen echten, positiven wirtschaftlichen Preis zeigen: „Standard" ist jetzt **6
Positionen, streng, 60 % Gefahrgutanteil, 8 ULDs** (106,6 kg im Mittel), „Wenige Positionen" **4 Positionen**
bei sonst gleicher Einstellung (124,2 kg im Mittel - weniger Positionen kosten mehr, wie erwartet). Der
Standard-Seed (28) ist so gewählt, dass die **live gezeigte Einzelinstanz** selbst einen realen Kostenunterschied
zeigt (nicht nur der Messreihen-Durchschnitt) - siehe `tests/test_app.py::test_default_view_shows_a_real_nonzero_economic_cost`.

**Beim Bauen gefunden (AP 7, Verifikation):** `tools/check_full.py` (volles Bau-Gate, wiederholt die
Messreihe und vergleicht gegen `data/uldk_results.json`) zeigte anfangs Abweichungen in `violation_rate_free`
über mehrere Zellen - obwohl alle gewichtsbasierten Felder (`mean_w_free`, `cost_pct`, `cost_kg_mean` usw.)
bitgleich reproduziert wurden. Ursache: derselbe CP-SAT-Gleichstand-Mechanismus wie in
`uld-beladeplan-demo` (`feedback_cp_sat_lexicographic_tiebreak.md`) - der „freie" Lauf optimiert nur das
Gewicht und kennt die Trennvorschrift nicht; bei mehreren gewichtsgleichen optimalen Zuordnungen entscheidet
`num_search_workers=8` willkürlich (aber reproduzierbar innerhalb eines Prozesses), welche davon
zurückgegeben wird - und ob GENAU diese die Trennvorschrift verletzt, ist bei solchen Gleichständen Zufall.
Empirisch bestätigt: drei aufeinanderfolgende volle Läufe derselben Zelle (±1,0 m, 20 % Gefahrgutanteil, 8
ULDs) maßen 11,67 % / 10,0 % / 13,33 % Verletzungsrate bei exakt identischem Zielwert. Behoben, indem
`tools/check_full.py` `violation_rate_free` mit einer Toleranz (höchstens 3 von 60 Instanzen) statt bitgleich
vergleicht - alle anderen Felder bleiben exakt. Die einzelnen, für Presets und Tests verwendeten Instanzen
(feste Seeds) wurden über mehrere Wiederholungen als stabil bestätigt, sind also nicht betroffen.

## Tests

Testanzahl und Laufzeit siehe Ausgabe von `_venvs/test/Scripts/python.exe -m pytest tests -v`:

- `tests/test_model.py` - die 12 Korrektheits-Checks aus `messreihe_uld_gefahrgut/check.py` (Nachbarschaft,
  Verletzungszählung an Handinstanzen, CP-SAT mit Trennvorschrift verletzt sie nie und hält weiterhin das
  Schwerpunktfenster ein, Monotonie, Brute-Force-Referenz, Regressionstest, Determinismus), plus
  Epsilon-Grenzfälle von `cg_ok()` und den **PFLICHT-Nullspalten-Regressionstest aus AP 0**: eine konstruierte
  Instanz (vier ULDs der Klassen 1/2/3/1 auf vier Positionen), bei der strukturell **keine** Anordnung alle
  Nachbarschaften unter der strengen Trennvorschrift einhalten kann - der eingeschränkte Lauf MUSS deshalb ein
  ULD abweisen, unabhängig vom Zufall.
- `tests/test_frozen_reference.py` - vier eingefrorene ULD-Listen (Gewicht + Gefahrgutklasse als Zahlen, keine
  Zufallsziehung zur Testzeit), die alle drei Meldungszustände der App abdecken, CI-robust gegen
  NumPy-Versionsdrift.
- `tests/test_results.py`, `tests/test_format.py` - Zell-Zuordnung (Hauptsweep/Zusatzmessung je 27 Zellen,
  54 insgesamt ohne Duplikate), Zahlenformate.
- `tests/test_visualization.py`, `tests/test_pdf_export.py` - Plotly-Figuren und PDF-Export bauen ohne Fehler
  (inklusive des Emoji-Fallstricks in der Meldung, siehe `uldk_pdf_export._pdf_safe`).
- `tests/test_presets.py`, `tests/test_stories.py` - Permalink-Parsing, alle fünf Presets bestehen ihre
  Abnahmekriterien gegen die Messreihe.
- `tests/test_claims.py` - jede Zahl aus diesem README (Hauptsweep UND AP-0-Zusatzmessung) gegen
  `data/uldk_results.json` nachgerechnet.
- `tests/test_app.py` - AppTest: Skelett, Footer, jedes Preset, Permalink, alle Regler an Min/Max (inklusive
  Positionszahl und Trennvorschrift-Stärke), alle drei Meldungszustände, **die Standardansicht zeigt einen
  echten, von 0 verschiedenen wirtschaftlichen Preis** (AP-0-Abnahme), PDF-Download, keine toten Datei-Links.

Zusätzlich: `tools/mutation_check.py` (Fehler-Einbau-Test für `uldk_model.py`, siehe `tools/mutants.py` für die
Einordnung gleichwertiger Überlebender) und `tools/check_full.py` (volles Bau-Gate: Wiederholung der
kombinierten Messreihe gegen `data/uldk_results.json` auf Bitgleichheit).

## Dateistruktur

| Datei | Inhalt |
|---|---|
| `app.py` | Streamlit-Einstiegspunkt |
| `uldk_constants.py` | Flugzeug/Positionen (parametrisiert nach Positionszahl), Reglerstufen, Presets, Farben |
| `uldk_presets.py` | Reglerspezifikation, Permalink, Presets, Seed-Knopf |
| `uldk_model.py` | Datentypen (Position, Aircraft, ULD mit Gefahrgutklasse), Trennvorschrift, `evaluate` (aus `gefahrgut.py`/`uldb_model.py` übernommen) |
| `uldk_oracle.py` | CP-SAT-Exakt, beide Läufe (lazy `ortools`-Import, aus `gefahrgut.py` übernommen) |
| `uldk_results.py` | Laden und Auswerten von `data/uldk_results.json` |
| `uldk_format.py` | Zahlenformate mit deutschem Dezimalkomma |
| `uldk_visualization.py` | Laderaumkarte (Gefahrgutklassen-Farbcodierung), Verletzungsrate-, Regime-Grafik |
| `uldk_stories.py` | Abnahmekriterien der Presets |
| `uldk_pdf_export.py` | Gefahrgut-Beladeplan-PDF |
| `tools/sweep.py` | Hauptsweep + AP-0-Zusatzmessung (nicht in CI) |
| `tools/check_full.py` | Volles Bau-Gate (bitgleicher Vergleich) |
| `tools/mutants.py`, `tools/mutation_check.py` | Fehler-Einbau-Test von `uldk_model.py` |
| `data/uldk_results.json` | Messreihe: 54 Zellen (27 Hauptsweep + 27 Zusatzmessung) × 60 Instanzen |
| `tests/` | Testsuite |

## Bewusst nicht umgesetzt

Eine echte IATA-DGR-Trenntabelle, seitliche/vertikale Nachbarschaft, mehr als drei Gefahrgutklassen, eine
Heuristik als Kontrast zu CP-SAT, die Fensterbreite als vierte Dimension der AP-0-Zusatzmessung.

## Verwandte Demos

- [`uld-beladeplan-demo`](https://github.com/sebastian-hanisch/uld-beladeplan-demo) - Kern-Code-Basis (Stück
  2 der Packen-Ausbaulinie): dieselbe Weight-&-Balance-Infrastruktur, ohne Gefahrgut.
- Fünf Demos, die Gefahrgut/Segregation bisher nur als offene Erweiterungsidee nennen (nicht umgesetzt):
  [`bahnladeplan-demo`](https://github.com/sebastian-hanisch/bahnladeplan-demo),
  [`blockzuweisung-demo`](https://github.com/sebastian-hanisch/blockzuweisung-demo),
  [`freight_demo`](https://github.com/sebastian-hanisch/freight_demo),
  [`stapelplanung-demo`](https://github.com/sebastian-hanisch/stapelplanung-demo),
  [`stauplanung-demo`](https://github.com/sebastian-hanisch/stauplanung-demo).

## Lokal ausführen

```
pip install -r requirements-dev.txt
streamlit run app.py
```

---

Gebaut mit Streamlit, Plotly, NumPy, OR-Tools und fpdf2.
