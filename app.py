"""
Gefahrgut-Trennung: sicher UND schwer beladen? - interaktive Fall-Demo (Weight & Balance + Segregation)
Sebastian Hanisch - Operations Research und Machine Learning

Drittes Stück der Packen-Ausbaulinie, baut auf `uld-beladeplan-demo` (Stück 2) auf. Dort kennt die Zuordnung
nur Gewicht und Schwerpunkt - hier bekommen ULDs zusätzlich eine Gefahrgutklasse, und bestimmte Klassenpaare
dürfen nicht auf benachbarten Positionen stehen (Trennvorschrift, vereinfacht nach dem Muster der
IATA-DGR-Trenntabelle). Frage: wie oft erzeugt eine gewichts-/schwerpunktoptimale Zuordnung, die die
Trennvorschrift nicht kennt, tatsächlich eine unsichere Zuordnung - und was kostet die Einhaltung an
Ladegewicht? Beide CP-SAT-Läufe (frei/mit Trennvorschrift) laufen bei jeder Einstellung live (unter 1 s).
Vorgerechnet: die Messreihe (data/uldk_results.json, 54 Zellen: 27 Hauptsweep + 27 AP-0-Zusatzmessung).

Lauffähig mit: streamlit run app.py
"""
import numpy as np
import streamlit as st

import uldk_constants as C
import uldk_results as R
import uldk_visualization as V
from uldk_format import fmt_kg, fmt_num, fmt_pct
from uldk_model import DEFAULT_SEG, STRONG_SEG, default_forbidden, evaluate, make_ulds, segregation_violations
from uldk_oracle import solve_exact
from uldk_pdf_export import generate_uldk_pdf
from uldk_presets import (SETTING_SPECS, apply_preset, bounds, init_session_state_defaults, load_permalink_settings,
                           randomize_seed, sync_query_params)

st.set_page_config(page_title="Gefahrgut-Trennung: sicher UND schwer beladen? – Sebastian Hanisch", layout="wide")

DATA = R.load_results()

SEG_SETS = {C.SEG_STANDARD: DEFAULT_SEG, C.SEG_STRONG: STRONG_SEG}


@st.cache_data(show_spinner=False, max_entries=256)
def _live(n_pos, width, dg_share, n_ulds, seg, seed):
    positions = C.make_positions(n_pos)
    pos_by_name = {p.name: p for p in positions}
    forbidden = default_forbidden(positions)
    seg_set = SEG_SETS[seg]
    ac = C.make_aircraft(width)
    rng = np.random.default_rng(seed)
    ulds = make_ulds(rng, n_ulds, dg_share)

    a_free, st_free, _ = solve_exact(ulds, positions, ac, seg_set, forbidden, respect_segregation=False, time_limit_s=3.0)
    a_seg, st_seg, _ = solve_exact(ulds, positions, ac, seg_set, forbidden, respect_segregation=True, time_limit_s=3.0)
    ev_free = evaluate(a_free, ulds, pos_by_name, ac)
    ev_seg = evaluate(a_seg, ulds, pos_by_name, ac)
    v_free = segregation_violations(a_free, ulds, pos_by_name, seg_set, forbidden)
    v_seg = segregation_violations(a_seg, ulds, pos_by_name, seg_set, forbidden)
    cost_kg = ev_free["cargo_weight"] - ev_seg["cargo_weight"]
    cost_pct = 100 * cost_kg / ev_free["cargo_weight"] if ev_free["cargo_weight"] > 0 else 0.0

    return dict(
        ulds=ulds, ac=ac, positions=positions, pos_by_name=pos_by_name,
        assign_free=a_free, assign_seg=a_seg, ev_free=ev_free, ev_seg=ev_seg,
        violations_free=v_free, violations_seg=v_seg, cost_kg=cost_kg, cost_pct=cost_pct,
        status_free=st_free, status_seg=st_seg,
    )


def judgment_message(violations_free: int, cost_kg: float, cost_pct: float) -> str:
    """Drei Zustände (Detailplan Abschnitt 6), nach Priorität: ein wirtschaftlicher Preis > 0 impliziert immer
    eine Verletzung der freien Lösung (Monotonie: 0 Verletzungen => 0 Kosten, siehe tests/test_model.py), die
    Reihenfolge unten ist deshalb eindeutig."""
    if cost_kg > 1e-6:
        return (f"⚠️ Trennvorschrift kostet hier Ladegewicht: {fmt_kg(cost_kg)} kg ({fmt_num(cost_pct, 1)} %) "
                f"weniger geladen als die freie Lösung - und die freie Lösung wäre zugleich unsicher gewesen "
                f"({violations_free} Verletzung{'en' if violations_free != 1 else ''}).")
    if violations_free > 0:
        return (f"🚫 Die freie Lösung wäre hier unsicher gewesen ({violations_free} Verletzung"
                f"{'en' if violations_free != 1 else ''} der Trennvorschrift) - die Einhaltung hätte in dieser "
                f"Instanz aber kein Ladegewicht gekostet.")
    return "✅ Trennvorschrift kostet hier nichts: die freie Lösung war in dieser Instanz bereits sicher."


st.title("☣️ Gefahrgut-Trennung: sicher UND schwer beladen?")
st.markdown(
    """
Eine gewichts- und schwerpunktoptimale Beladung ([`uld-beladeplan-demo`](https://sebastianhanisch-uld-beladeplan-demo.streamlit.app),
Stück 2 dieser Reihe) ist nicht automatisch eine **sichere**: bestimmte Gefahrgutklassen dürfen nicht auf
**benachbarten** Laderaumpositionen stehen (Trennvorschrift, vereinfacht nach dem Muster der
IATA-DGR-Trenntabelle), manche Klassen sind an bestimmten Positionen **grundsätzlich verboten**. Wie oft
widerspricht die eine der anderen - und was kostet es, beide gleichzeitig zu erfüllen? Die Demo rechnet **zwei
CP-SAT-Läufe live** (unter 1 s): 🔓 **frei** (maximiert Ladegewicht, kennt die Trennvorschrift nicht) gegen 🔒
**mit Trennvorschrift** (dieselbe Zielfunktion, zusätzlich die Trenn- und Verbotsregeln als harte
Nebenbedingung) - für **eine Instanz**, und vorgerechnet über **60 Instanzen je Zelle** (54 Zellen: Hauptsweep
plus AP-0-Zusatzmessung), die die Aussage trägt. Wie das Modell funktioniert, steht im Expander „Wie
funktioniert diese Demo?" weiter unten, die formale Beschreibung im Expander „📐 Mathematische Formulierung“.
"""
)

st.caption("🎯 Schnellstart – ein Beispielszenario laden:")
preset_names = list(C.PRESETS)
for row in (preset_names[:3], preset_names[3:]):
    cols = st.columns(len(row))
    for col, name in zip(cols, row):
        with col:
            st.button(name, width="stretch", on_click=apply_preset, args=(name,), help=C.PRESET_HELP[name])

st.caption("🔗 Die Adresszeile oben spiegelt Ihre aktuelle Konfiguration wider – einfach kopieren, um ein Szenario zu teilen.")

load_permalink_settings()
init_session_state_defaults()

with st.sidebar:
    st.header("⚙️ Einstellungen")
    st.markdown("**Laderaum**")
    n_pos = st.select_slider("Anzahl Laderaumpositionen", options=list(C.N_POS_OPTIONS), key="n_pos_slider",
                             help="Weniger Positionen = weniger Ausweichmöglichkeiten für Gefahrgut-Trennung "
                                  "(AP 0: bei 10 Positionen kostet selbst die strenge Trennvorschrift fast "
                                  "immer nichts, bei 4-6 Positionen wird der Preis real).")
    width = st.select_slider("Schwerpunktfenster ±", options=list(C.WIDTH_OPTIONS), key="width_slider",
                             help="Zulässiger Schwerpunkt-Ausschlag um die Flugzeugmitte, in Metern (wie bei "
                                  "uld-beladeplan-demo).")
    st.markdown("**Gefahrgut**")
    dg_share = st.select_slider("Gefahrgutanteil", options=list(C.DG_SHARE_OPTIONS), key="dg_share_slider",
                                format_func=lambda v: f"{int(v*100)} %",
                                help="Anteil der ULDs mit einer Gefahrgutklasse (1-3); der Rest ist Klasse 0 "
                                     "(kein Gefahrgut, nie beschränkt).")
    seg = st.selectbox("Trennvorschrift", options=list(C.SEG_OPTIONS), key="seg_select",
                       format_func=lambda v: C.SEG_LABEL[v],
                       help="Standard: nur Klasse 1/2 dürfen nicht benachbart stehen. Streng: alle drei "
                            "Klassen paarweise verboten - zeigt den wirtschaftlichen Preis auch bei mehr "
                            "Positionen sichtbar (siehe AP 0).")
    st.markdown("**Ladung**")
    n_ulds = st.select_slider("Anzahl ULDs", options=list(C.ULDS_OPTIONS), key="ulds_slider",
                              help="Gemessene Stufen der Messreihe (8 / 12 / 16).")
    st.markdown("**Gezeigte Instanz**")
    seed = st.number_input("Seed", *bounds("seed_input"), key="seed_input", step=1,
                           help="Nummer der gezeigten Instanz.")
    st.button("🎲 Neue Instanz", width="stretch", on_click=randomize_seed, help="Würfelt einen neuen Seed.")

sync_query_params({key: st.session_state[key] for key in SETTING_SPECS})
n_pos, width, dg_share, n_ulds, seg, seed = int(n_pos), float(width), float(dg_share), int(n_ulds), str(seg), int(seed)

live = _live(n_pos, width, dg_share, n_ulds, seg, seed)

# ---------------------------------------------------------------------------------------------------
# Hauptansicht (Kernabschnitt ①, live: eine Instanz)
# ---------------------------------------------------------------------------------------------------
st.markdown("## ☣️ Eine gewichts-/schwerpunktoptimale Zuordnung - sicher oder nicht?")
st.caption(f"Live-Instanz (eine Instanz): Seed {seed}, {n_ulds} ULDs ({fmt_pct(dg_share, 0)} Gefahrgutanteil), "
           f"{n_pos} Positionen, Fensterbreite ±{fmt_num(width, 2)} m, Trennvorschrift {C.SEG_LABEL[seg]}. "
           "Beide CP-SAT-Läufe laufen bei jeder Einstellung neu (unter 1 s, je Einstellung zwischengespeichert). "
           "Eine einzelne Instanz – die vorgerechnete Messreihe unten trägt die Aussage.")

st.plotly_chart(V.loading_map_figure(live["ulds"], live["assign_free"], live["assign_seg"], live["ac"],
                                      live["positions"], C.POS_MAX_WEIGHT_KG), width="stretch", key="main_loading_map")

k1, k2, k3, k4 = st.columns(4)
k1.metric("Geladenes Gewicht frei", f"{live['ev_free']['cargo_weight']:.0f} kg")
k2.metric("Geladenes Gewicht mit Trennvorschrift", f"{live['ev_seg']['cargo_weight']:.0f} kg")
k3.metric("Verletzungen der freien Lösung", str(live["violations_free"]),
          delta="unsicher" if live["violations_free"] > 0 else "sicher", delta_color="off")
k4.metric("Kostendifferenz", f"{fmt_kg(live['cost_kg'])} kg", f"{fmt_num(live['cost_pct'], 1)} %")

st.info(judgment_message(live["violations_free"], live["cost_kg"], live["cost_pct"]))
st.caption("Ehrliche Grenze: eine Instanz zeigt nur einen von 60 möglichen Zufallsfällen; die Meldung oben "
           "gilt nur für diese eine Instanz, nicht als Messreihen-Durchschnitt - der steht im Kernabschnitt "
           "unten.")

pdf_slot = st.container()

st.markdown("---")

# ---------------------------------------------------------------------------------------------------
# Kernabschnitt ② (vorgerechnet): was die Messreihe zeigt
# ---------------------------------------------------------------------------------------------------
st.markdown("### 📐 Was die Messreihe über 60 Instanzen je Zelle zeigt")
st.markdown(
    """
Kernfragen: Wie oft verletzt eine Regel ohne Gefahrgutwissen tatsächlich die Trennvorschrift, und was kostet
deren Einhaltung an Ladegewicht? Die Antwort steht auf **60 Instanzen je Zelle** (54 Zellen: 27 Hauptsweep bei
10 Positionen/milder Trennvorschrift, 27 AP-0-Zusatzmessung bei 4/6/10 Positionen/strenger Trennvorschrift -
siehe `tools/sweep.py`), vorgerechnet und **nie live** gerechnet.
"""
)

st.markdown("**1 · Verletzungsrate über den Gefahrgutanteil** (Standard-Trennvorschrift, 10 Positionen, "
            "Fensterbreite ±0,5 m, 12 ULDs)")
share_rows = R.violation_rate_over_share_rows(DATA)
st.plotly_chart(V.violation_rate_over_share_figure(share_rows), width="stretch", key="core_violation_rate")
st.caption(f"Je mehr Gefahrgut an Bord, desto häufiger widerspricht eine gewichts-/schwerpunktoptimale "
           f"Zuordnung der Trennvorschrift - im Mittel über alle 27 Hauptsweep-Zellen "
           f"{fmt_pct(R.mean_violation_rate(R.standard_sweep_rows(DATA)))}, "
           f"Maximum {fmt_pct(R.max_cell(R.standard_sweep_rows(DATA), 'violation_rate_free')['violation_rate_free'])}.")

st.markdown("**2 · Wirtschaftlicher Preis** - Regime bei Fensterbreite ±0,5 m, 60 % Gefahrgutanteil, 8 ULDs "
            "(derselben Zelle wie das Preset „Standard“)")
regime = R.regime_rows(DATA)
st.plotly_chart(V.regime_figure(regime), width="stretch", key="core_regime")
st.dataframe(
    {
        "Positionen": [r["n_pos"] for r in regime],
        "Trennvorschrift": [C.SEG_LABEL[r["seg"]] for r in regime],
        "Verletzungsrate frei": [fmt_pct(r["violation_rate_free"]) for r in regime],
        "Preis (%)": [fmt_num(r["cost_pct"], 2) + " %" for r in regime],
        "Preis (kg, Mittel)": [fmt_kg(r["cost_kg_mean"]) for r in regime],
        "Anteil Instanzen mit Preis": [fmt_pct(r["share_instances_with_cost"]) for r in regime],
    },
    width="stretch", hide_index=True,
)
st.caption("Bei 10 Positionen kostet selbst die strenge Trennvorschrift in dieser Zelle nichts - der "
           "wirtschaftliche Preis entsteht erst, wenn Positionen knapp UND die Trennvorschrift streng ist "
           "(siehe README „Befunde und Korrekturen gegenüber dem Plan“).")

with pdf_slot:
    st.download_button(
        "📄 Gefahrgut-Beladeplan als PDF herunterladen",
        data=generate_uldk_pdf(
            dict(n_pos=n_pos, width=width, seg_label=C.SEG_LABEL[seg], dg_share=dg_share, n_ulds=n_ulds, seed=seed),
            live, judgment_message(live["violations_free"], live["cost_kg"], live["cost_pct"])),
        file_name="uld_gefahrgut.pdf", mime="application/pdf", key="primary_pdf_download",
        help="Einstellungen, Kennzahlen beider Läufe und die Meldung der gezeigten Instanz.")

st.markdown("---")

# ---------------------------------------------------------------------------------------------------
# Ansichten
# ---------------------------------------------------------------------------------------------------
with st.expander("🔧 Wie wir das erreichen – vollständiger Methodenvergleich"):
    tabs = st.tabs(["🛫 Laderaumkarte", "📊 Vergleich", "📈 Messreihe"])
    with tabs[0]:
        st.markdown("Beide Zuordnungen auf derselben Hebelarm-Achse, Schwerpunktfenster als grüner Streifen, "
                     "Balken nach Gefahrgutklasse eingefärbt (grau = kein Gefahrgut).")
        st.plotly_chart(V.loading_map_figure(live["ulds"], live["assign_free"], live["assign_seg"], live["ac"],
                                              live["positions"], C.POS_MAX_WEIGHT_KG), width="stretch", key="tab_loading_map")
    with tabs[1]:
        st.markdown("Beide Läufe auf **dieser** Instanz, Kennzahlen nebeneinander:")
        st.dataframe(
            {
                "Kennzahl": ["Geladenes Gewicht (kg)", "Anzahl ULDs geladen", "Verletzungen der Trennvorschrift"],
                "Frei": [f"{live['ev_free']['cargo_weight']:.0f}", str(live['ev_free']['n_loaded']), str(live["violations_free"])],
                "Mit Trennvorschrift": [f"{live['ev_seg']['cargo_weight']:.0f}", str(live['ev_seg']['n_loaded']), str(live["violations_seg"])],
            },
            width="stretch", hide_index=True,
        )
    with tabs[2]:
        st.markdown("Alle 54 gemessenen Zellen als Tabelle (Trennvorschrift, Positionszahl, Fensterbreite, "
                     "Gefahrgutanteil, ULD-Zahl, Verletzungsrate, wirtschaftlicher Preis):")
        all_rows = R.cells(DATA)
        st.dataframe(
            {
                "Trennvorschrift": [r["seg"] for r in all_rows],
                "Positionen": [r["n_pos"] for r in all_rows],
                "Fenster ±": [f"{r['width']:g} m" for r in all_rows],
                "Gefahrgutanteil": [f"{int(r['dg_share']*100)} %" for r in all_rows],
                "ULDs": [r["n_ulds"] for r in all_rows],
                "Verletzungsrate frei": [fmt_pct(r["violation_rate_free"]) for r in all_rows],
                "Preis (%)": [fmt_num(r["cost_pct"], 2) + " %" for r in all_rows],
            },
            width="stretch", hide_index=True, height=360,
        )

with st.expander("Wie funktioniert diese Demo?"):
    st.markdown(
        f"""
**Instanz.** Flugzeug mit Leergewicht {C.EMPTY_WEIGHT_KG:.0f} kg bei Hebelarm {C.CENTER_M:.1f} m
(Referenzpunkt), Treibstoff {C.FUEL_KG:.0f} kg (Hebelarm {C.CENTER_M:.1f} m, selbst neutral),
Schwerpunktfenster [{C.CENTER_M:.1f} − Breite; {C.CENTER_M:.1f} + Breite] m. **{{n_pos}} Laderaumpositionen**
gleichmäßig verteilt von Hebelarm {C.ARM_MIN:.1f} bis {C.ARM_MAX:.1f} m, je {C.POS_MAX_WEIGHT_KG:.0f} kg
Gewichtsgrenze - die Positionszahl ist hier selbst ein Regler (4/6/10). ULDs: 8/12/16 Stück je Instanz,
Gewicht gleichverteilt zwischen 200 und 2.200 kg; ein einstellbarer Anteil bekommt eine Gefahrgutklasse
(1, 2 oder 3, gleichverteilt), der Rest ist Klasse 0 (kein Gefahrgut).

**Trennvorschrift.** Nachbarschaft = benachbarte Positionen in der Hebelarm-Reihenfolge (wie hintereinander im
Flugzeug). **Standard:** Klasse 1 und 2 dürfen nicht benachbart stehen, Klasse 3 ist an den beiden vordersten
Positionen grundsätzlich verboten. **Streng:** zusätzlich sind auch Klasse 1/3 und 2/3 benachbart verboten -
alle drei Klassen paarweise getrennt.

**Die beiden Läufe.** **🔓 Frei:** 0/1-Zuordnung ULD→Position, Kapazität und Schwerpunktfenster (beide
Zeitpunkte, wie bei `uld-beladeplan-demo`) als Nebenbedingung, maximiertes geladenes Gewicht - kennt die
Trennvorschrift nicht. **🔒 Mit Trennvorschrift:** dieselbe Zielfunktion, zusätzlich die Trenn- und
Verbotsregeln als harte Nebenbedingung. Beide Läufe sind **exakt** (CP-SAT, kein Heuristik-Vergleich wie bei
Stück 2 - die Instanzgröße erlaubt hier immer den exakten Löser für beide Seiten).

**Warum der wirtschaftliche Preis von der Positionszahl abhängt (AP-0-Befund, ehrlich erklärt).** Bei 10
Positionen gibt es fast immer genug freie Positionen, um die Trennung ohne Gewichtsverlust einzuhalten - der
Preis ist in fast allen gemessenen Zellen exakt 0,00 %, auch unter der strengen Trennvorschrift. Erst wenn
Positionen knapp werden (4-6) UND die Trennvorschrift streng ist, wird die Einhaltung real teuer, weil dann
tatsächlich ULDs abgewiesen werden müssen, um die Trennung einzuhalten (siehe README, Abschnitt "Befunde und
Korrekturen gegenüber dem Plan", für die vollständige Zahlenlage).

**Grenzen dieses Modells** (bewusst so gewählt, damit die Aussage ehrlich bleibt):

- Die Trennvorschrift ist stark vereinfacht (drei Klassen, ein bzw. drei verbotene Paare, eine
  Positionsbeschränkung) - keine Übernahme der echten, deutlich umfangreicheren IATA-DGR-Trenntabelle.
- Nachbarschaft ist eindimensional (nur die Hebelarm-Reihenfolge); reale Frachträume haben auch seitliche und
  vertikale Nachbarschaft, hier nicht modelliert.
- Flugzeug- und Positionsdaten erfunden, nicht kalibriert (wie bei `uld-beladeplan-demo`).
- **Nicht Teil dieser Demo:** eine echte IATA-DGR-Tabelle, seitliche/vertikale Nachbarschaft, mehr als drei
  Gefahrgutklassen, eine Heuristik als Kontrast zu CP-SAT (anders als Stück 2 sind hier beide Seiten exakt).
        """.replace("{n_pos}", str(n_pos))
    )

with st.expander("📐 Mathematische Formulierung"):
    st.markdown(
        r"""
**Nachbarschaft.** Positionen $j, j+1$ in Hebelarm-Reihenfolge sortiert (siehe `uldk_model.adjacent_pairs`).

**Trennvorschrift.** Für Klassenpaar $(a, b) \in \mathrm{Seg}$ und Nachbarpositionen $(j, j+1)$:
$x_{i_1,j} + x_{i_2,j+1} \le 1$ für alle $i_1, i_2$ mit Klasse$(i_1)=a$, Klasse$(i_2)=b$.

**Positionsverbot.** $x_{i,j} = 0$ für Klasse$(i) \in \mathrm{Forbidden}(j)$.

**Ziel (beide Läufe gleich).** $\max \sum_i x_i w_i$ unter $\sum_j x_{ij} \le 1$ je ULD $i$, $\sum_i x_{ij} \le 1$
je Position $j$, Positions-Gewichtsgrenze, Schwerpunktfenster an beiden Zeitpunkten (voller/leerer Tank,
linearisiert wie bei `uld-beladeplan-demo`) - der Lauf „mit Trennvorschrift“ hat zusätzlich die beiden
Nebenbedingungen oben.

Implementiert in `uldk_model.py` (Datentypen, Trennvorschrift, Bewertung) und `uldk_oracle.py` (CP-SAT, beide
Läufe).
        """
    )

st.markdown("---")

st.caption(
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). "
    "Mehr zum Thema: [Luftfracht optimieren](https://sebastianhanisch.net/luftfracht-optimierung.html)."
)
