"""Gefahrgut-Trennung beim Beladeplan - feste Annahmen, Reglerstufen, Presets, Farben.

Flugzeug- und Positionsdaten wie bei uld-beladeplan-demo (Stück 2, erfunden, nicht kalibriert). Neu
gegenüber Stück 2: die Positionszahl ist hier selbst ein Regler (4/6/10, siehe AP 0/ERGEBNIS der
Zusatzmessung in data/uldk_results.json) - die Positionen werden deshalb über make_positions(n_pos) erzeugt,
nicht als feste Liste."""
from uldk_model import Aircraft, Position

# --- Flugzeug und Positionen -------------------------------------------------------------------------------
ARM_MIN, ARM_MAX = 6.0, 28.0
POS_MAX_WEIGHT_KG = 2200.0
CENTER_M = (ARM_MIN + ARM_MAX) / 2.0  # 17.0

EMPTY_WEIGHT_KG = 40000.0
FUEL_KG = 8000.0


def make_positions(n_pos: int) -> list[Position]:
    return [Position(f"p{i}", ARM_MIN + i * (ARM_MAX - ARM_MIN) / (n_pos - 1), POS_MAX_WEIGHT_KG) for i in range(n_pos)]


def make_aircraft(width_m: float) -> Aircraft:
    """Treibstoff hat denselben Hebelarm wie das Leergewicht (neutral) - wie bei uld-beladeplan-demo."""
    return Aircraft(
        empty_weight_kg=EMPTY_WEIGHT_KG, empty_moment_kgm=EMPTY_WEIGHT_KG * CENTER_M,
        fuel_kg=FUEL_KG, fuel_arm_m=CENTER_M,
        cg_min_m=CENTER_M - width_m, cg_max_m=CENTER_M + width_m,
    )


# --- Reglerstufen (die vier Sweep-Dimensionen der Messreihe, siehe AP 0 / tools/sweep.py) -------------------
WIDTH_OPTIONS = (1.0, 0.5, 0.3)
WIDTH_DEFAULT = 0.5

DG_SHARE_OPTIONS = (0.2, 0.4, 0.6)
DG_SHARE_DEFAULT = 0.6

ULDS_OPTIONS = (8, 12, 16)
ULDS_DEFAULT = 8

N_POS_OPTIONS = (4, 6, 10)
N_POS_DEFAULT = 6

SEG_STANDARD = "standard"
SEG_STRONG = "streng"
SEG_OPTIONS = (SEG_STANDARD, SEG_STRONG)
SEG_DEFAULT = SEG_STRONG
SEG_LABEL = {
    SEG_STANDARD: "Standard (Klasse 1/2 verboten)",
    SEG_STRONG: "streng (alle drei Klassen paarweise verboten)",
}

SEED_RANGE = (0, 59)  # N_INSTANCES der Messreihe (60 Instanzen je Zelle)
SEED_DEFAULT = 28  # zeigt bei Standard UND Wenige Positionen live einen echten Kostenunterschied > 0 (AP 0)

COLOR_FREE = "#2a6fb0"
COLOR_SEG = "#3d8b5f"

# Presets (Detailplan Abschnitt 7, Zahlen aus der AP-0-Zusatzmessung, siehe README "Befunde und Korrekturen
# gegenüber dem Plan" - der Plan-Platzhalter "10 Positionen, streng, Anteil 40 %, 12 ULDs" für "Standard"
# zeigt real 0,00 % Kosten (siehe data/uldk_results.json), AP 0 hat deshalb die tatsächlichen Regler-Werte
# geliefert, die live einen echten Preis zeigen).
PRESETS = {
    "Standard": dict(width=0.5, dg_share=0.6, n_ulds=8, n_pos=6, seg=SEG_STRONG, seed=28),
    "Lockere Trennung": dict(width=0.5, dg_share=0.4, n_ulds=12, n_pos=10, seg=SEG_STANDARD, seed=0),
    "Wenige Positionen": dict(width=0.5, dg_share=0.6, n_ulds=8, n_pos=4, seg=SEG_STRONG, seed=28),
    "Viel Gefahrgut": dict(width=0.5, dg_share=0.6, n_ulds=16, n_pos=10, seg=SEG_STRONG, seed=57),
    "Wenig Gefahrgut": dict(width=0.5, dg_share=0.2, n_ulds=8, n_pos=10, seg=SEG_STANDARD, seed=1),
}

PRESET_HELP = {
    "Standard": "6 Positionen, strenge Trennvorschrift, 60 % Gefahrgutanteil, 8 ULDs: eine gewichts-/schwerpunktoptimale Zuordnung ist oft unsicher, und die Einhaltung kostet hier real Ladegewicht (im Mittel 106,6 kg, gemessen).",
    "Lockere Trennung": "Standard-Trennvorschrift (nur Klasse 1/2 verboten), 10 Positionen, 40 % Gefahrgutanteil, 12 ULDs: bei genug Positionen und milder Trennung ist Sicherheit kostenlos.",
    "Wenige Positionen": "nur 4 Positionen (weniger als bei Standard), sonst gleiche Einstellung: der wirtschaftliche Preis der Trennvorschrift wächst mit sinkender Positionszahl (im Mittel 124,2 kg, gemessen).",
    "Viel Gefahrgut": "60 % Gefahrgutanteil, 16 ULDs, strenge Trennvorschrift, 10 Positionen: die freie Lösung ist hier fast immer unsicher - und selbst bei 10 Positionen entsteht ein kleiner realer Preis.",
    "Wenig Gefahrgut": "20 % Gefahrgutanteil, 8 ULDs, Standard-Trennvorschrift, 10 Positionen: der Konflikt ist selten, aber nicht null.",
}
