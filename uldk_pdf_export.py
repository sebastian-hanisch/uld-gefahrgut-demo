"""Erzeugt einen downloadbaren Gefahrgut-Beladeplan als PDF (in-memory, kein Zwischenspeichern auf Disk):
Einstellungen, Kennzahlen beider Läufe (frei/mit Trennvorschrift), die Meldung der gezeigten Instanz und die
Positionsliste beider Zuordnungen mit Gefahrgutklasse.

fpdf2-Fallstricke (siehe DEMO-PLAYBOOK Abschnitt 7): echte Umlaute sind in den Kernschriften unproblematisch,
Gedankenstrich (-) und Euro-Zeichen (EUR statt Symbol) vermeiden - hier kommt ohnehin kein Geldbetrag vor."""
import time

from uldk_format import fmt_kg, fmt_num, fmt_pct
from uldk_visualization import DG_CLASS_LABEL


def _pdf_safe(text: str) -> str:
    """fpdf2s Kernschriften (Helvetica) sind Latin-1 - echte Umlaute sind darin unproblematisch (siehe
    DEMO-PLAYBOOK Abschnitt 7), aber die Emojis der App-Meldung (z. B. ⚠️/🚫/✅) sind es nicht. Entfernt nur
    die nicht darstellbaren Zeichen, der restliche Text (inklusive Umlauten) bleibt unverändert."""
    return text.encode("latin-1", errors="ignore").decode("latin-1")


def generate_uldk_pdf(settings: dict, live: dict, message: str) -> bytes:
    from fpdf import FPDF
    from fpdf.enums import XPos, YPos

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Gefahrgut-Trennung: sicher UND schwer beladen?", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, f"Erstellt: {time.strftime('%d.%m.%Y %H:%M')} Uhr", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, "Einstellungen", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Positionen: {settings['n_pos']}, Fensterbreite +/- {fmt_num(settings['width'], 2)} m, "
                    f"Trennvorschrift: {settings['seg_label']}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 6, f"Gefahrgutanteil {fmt_pct(settings['dg_share'], 0)}, ULDs: {settings['n_ulds']}, Seed {settings['seed']}",
              new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, "Kennzahlen (diese Instanz)", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(235, 235, 235)
    headers = ["Kennzahl", "Frei", "Mit Trennvorschrift"]
    widths = [70, 55, 55]
    for h, w in zip(headers, widths):
        pdf.cell(w, 7, h, border=1, fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
    pdf.ln(7)
    pdf.set_font("Helvetica", "", 9)
    ev_free, ev_seg = live["ev_free"], live["ev_seg"]
    rows = [
        ("Geladenes Gewicht (kg)", f"{ev_free['cargo_weight']:.0f}", f"{ev_seg['cargo_weight']:.0f}"),
        ("Anzahl ULDs geladen", str(ev_free["n_loaded"]), str(ev_seg["n_loaded"])),
        ("Verletzungen der Trennvorschrift", str(live["violations_free"]), str(live["violations_seg"])),
    ]
    for row in rows:
        for val, w in zip(row, widths):
            pdf.cell(w, 6, val, border=1, new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.ln(6)
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 9)
    pdf.multi_cell(0, 5, _pdf_safe(f"Kostendifferenz: {fmt_kg(live['cost_kg'])} kg ({fmt_num(live['cost_pct'], 1)} %). {message}"))
    pdf.ln(3)

    for method_label, assign, key in (("Frei (kennt Trennvorschrift nicht)", live["assign_free"], "ev_free"),
                                       ("Mit Trennvorschrift", live["assign_seg"], "ev_seg")):
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 8, f"Positionsliste: {method_label}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_fill_color(235, 235, 235)
        headers2 = ["ULD", "Position", "Hebelarm (m)", "Gewicht (kg)", "Gefahrgutklasse"]
        widths2 = [25, 25, 30, 30, 50]
        for h, w in zip(headers2, widths2):
            pdf.cell(w, 7, h, border=1, fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
        pdf.ln(7)
        pdf.set_font("Helvetica", "", 9)
        ulds_by_name = {u.name: u for u in live["ulds"]}
        pos_by_name = live["pos_by_name"]
        for uld_name in sorted(assign, key=lambda n: pos_by_name[assign[n]].arm_m):
            pos_name = assign[uld_name]
            pos = pos_by_name[pos_name]
            uld = ulds_by_name[uld_name]
            row2 = [uld_name, pos_name, f"{pos.arm_m:.1f}", f"{uld.weight_kg:.1f}", DG_CLASS_LABEL[uld.dg_class]]
            for val, w in zip(row2, widths2):
                pdf.cell(w, 6, val, border=1, new_x=XPos.RIGHT, new_y=YPos.TOP)
            pdf.ln(6)
        if not assign:
            pdf.set_font("Helvetica", "I", 9)
            pdf.cell(0, 6, "(keine ULDs geladen)", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.ln(4)

    return bytes(pdf.output())
