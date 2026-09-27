"""Gefahrgut-Trennung beim Beladeplan - Plotly-Figuren.

Laderaumkarte mit Gefahrgutklassen-Farbcodierung, "frei" gegen "mit Trennvorschrift" nebeneinander (zwei
Subplots, dieselbe Hebelarm-Achse - anders als bei uldb_visualization.loading_map_figure, wo alle Verfahren in
EINEM Diagramm gruppiert werden: hier stehen die beiden Zuordnungen für unterschiedliche ULDs an unterschied-
lichen Positionen, ein gruppierter Balken würde das verdecken). Plus die vorgerechneten Grafiken (Verletzungs-
rate über den Gefahrgutanteil, Regime über Positionszahl/Trennvorschrift-Stärke). Alle Achsen `fixedrange`
(Touch-Scrollen soll nicht am Chart hängen bleiben, siehe DEMO-PLAYBOOK Abschnitt 3)."""
from __future__ import annotations

import plotly.graph_objects as go
from plotly.subplots import make_subplots

DG_CLASS_LABEL = {0: "kein Gefahrgut", 1: "Klasse 1", 2: "Klasse 2", 3: "Klasse 3"}
DG_CLASS_COLOR = {0: "#b7bec9", 1: "#c0392b", 2: "#e0822a", 3: "#8e44ad"}

COLOR_FREE = "#2a6fb0"
COLOR_SEG = "#3d8b5f"


def _bars_for(assign: dict[str, str], ulds: list, positions: list):
    """Ein Balken je Position (Hebelarm), gefärbt nach der Gefahrgutklasse des dort geladenen ULDs (leer,
    wenn keins geladen ist)."""
    ulds_by_name = {u.name: u for u in ulds}
    pos_of = {p_name: u_name for u_name, p_name in assign.items()}
    arms, weights, colors, labels = [], [], [], []
    for p in positions:
        arms.append(p.arm_m)
        u_name = pos_of.get(p.name)
        if u_name is None:
            weights.append(0.0)
            colors.append("#eceff2")
            labels.append(f"{p.name}: frei")
        else:
            u = ulds_by_name[u_name]
            weights.append(u.weight_kg)
            colors.append(DG_CLASS_COLOR[u.dg_class])
            labels.append(f"{p.name}: {u.name}, {u.weight_kg:.0f} kg, {DG_CLASS_LABEL[u.dg_class]}")
    return arms, weights, colors, labels


def loading_map_figure(ulds: list, assign_free: dict, assign_seg: dict, ac, positions: list, max_weight_kg: float):
    """Zwei Subplots (frei / mit Trennvorschrift) auf derselben Hebelarm-Achse, Schwerpunktfenster als grüner
    Streifen in beiden, Balken nach Gefahrgutklasse eingefärbt."""
    fig = make_subplots(rows=1, cols=2, subplot_titles=("🔓 Frei (kennt Trennvorschrift nicht)", "🔒 Mit Trennvorschrift"),
                         shared_yaxes=True, horizontal_spacing=0.06)
    max_y = max_weight_kg * 1.15
    seen_classes = set()
    for col, assign in ((1, assign_free), (2, assign_seg)):
        arms, weights, colors, labels = _bars_for(assign, ulds, positions)
        fig.add_vrect(x0=ac.cg_min_m, x1=ac.cg_max_m, fillcolor="rgba(61,139,95,0.12)", line_width=0,
                       row=1, col=col)
        fig.add_trace(go.Bar(x=arms, y=weights, marker_color=colors, hovertext=labels, hoverinfo="text",
                              showlegend=False), row=1, col=col)
    # Legende: eine unsichtbare Spur je vorkommender Gefahrgutklasse (0..3), damit die Farben erklärt sind.
    classes_present = {0} | {u.dg_class for u in ulds}
    for cls in sorted(classes_present):
        fig.add_trace(go.Bar(x=[None], y=[None], marker_color=DG_CLASS_COLOR[cls], name=DG_CLASS_LABEL[cls],
                              showlegend=True), row=1, col=1)
    fig.update_xaxes(title_text="Hebelarm (m)", fixedrange=True)
    fig.update_yaxes(title_text="Geladenes Gewicht je Position (kg)", range=[0, max_y], fixedrange=True, col=1)
    fig.update_yaxes(range=[0, max_y], fixedrange=True, col=2)
    fig.update_layout(height=380, margin=dict(l=10, r=10, t=40, b=10), barmode="overlay",
                       legend=dict(orientation="h", yanchor="bottom", y=1.12, xanchor="left", x=0))
    return fig


def violation_rate_over_share_figure(rows: list[dict]):
    """Verletzungsrate der freien Lösung über den Gefahrgutanteil (Hauptsweep, Standard-Trennvorschrift,
    Fensterbreite 0,5 m, 12 ULDs) - Detailplan Abschnitt 1/6."""
    xs = [f"{int(r['dg_share']*100)} %" for r in rows]
    ys = [100 * r["violation_rate_free"] for r in rows]
    fig = go.Figure(go.Bar(x=xs, y=ys, marker_color=COLOR_FREE,
                            text=[f"{y:.1f} %" for y in ys], textposition="outside"))
    fig.update_layout(
        height=300, margin=dict(l=10, r=10, t=20, b=10),
        xaxis=dict(title="Gefahrgutanteil", fixedrange=True),
        yaxis=dict(title="Anteil Instanzen mit Verletzung (frei, %)", range=[0, 100], fixedrange=True),
        showlegend=False,
    )
    return fig


def regime_figure(rows: list[dict]):
    """Wirtschaftlicher Preis (Prozent) über Positionszahl und Trennvorschrift-Stärke, gefärbt danach, ob ein
    Preis überhaupt gemessen wurde - zeigt den AP-0-Befund: 0 % bei 10 Positionen/Standard, real ab strenger
    Trennvorschrift und wenigen Positionen."""
    xs = [f"{r['n_pos']} Pos./{'streng' if r['seg'] == 'streng' else 'Standard'}" for r in rows]
    ys = [r["cost_pct"] for r in rows]
    colors = ["#c0392b" if r["cost_pct"] > 0.05 else "#7a7a7a" for r in rows]
    fig = go.Figure(go.Bar(x=xs, y=ys, marker_color=colors,
                            hovertext=[f"{r['n_pos']} Positionen, {r['seg']}: {r['cost_pct']:.2f} % "
                                       f"({r['cost_kg_mean']:.0f} kg im Mittel)" for r in rows],
                            hoverinfo="text"))
    fig.update_layout(
        height=320, margin=dict(l=10, r=10, t=20, b=60),
        xaxis=dict(title="Positionszahl / Trennvorschrift-Stärke", tickangle=45, fixedrange=True, tickfont=dict(size=9)),
        yaxis=dict(title="Wirtschaftlicher Preis (%)", fixedrange=True),
        showlegend=False,
    )
    return fig
