"""Tests für uldk_pdf_export.py: PDF-Export baut ohne Fehler, auch mit Emoji-Meldungstext (fpdf2-Fallstrick,
siehe DEMO-PLAYBOOK Abschnitt 7 und uldk_pdf_export._pdf_safe)."""
import numpy as np

import uldk_constants as C
from uldk_model import STRONG_SEG, default_forbidden, evaluate, make_ulds, segregation_violations
from uldk_oracle import solve_exact
from uldk_pdf_export import generate_uldk_pdf, _pdf_safe


def _live():
    positions = C.make_positions(6)
    pos_by_name = {p.name: p for p in positions}
    ac = C.make_aircraft(0.5)
    forbidden = default_forbidden(positions)
    rng = np.random.default_rng(28)
    ulds = make_ulds(rng, 8, 0.6)
    a_free, _, _ = solve_exact(ulds, positions, ac, STRONG_SEG, forbidden, respect_segregation=False, time_limit_s=5.0)
    a_seg, _, _ = solve_exact(ulds, positions, ac, STRONG_SEG, forbidden, respect_segregation=True, time_limit_s=5.0)
    ev_free = evaluate(a_free, ulds, pos_by_name, ac)
    ev_seg = evaluate(a_seg, ulds, pos_by_name, ac)
    v_free = segregation_violations(a_free, ulds, pos_by_name, STRONG_SEG, forbidden)
    v_seg = segregation_violations(a_seg, ulds, pos_by_name, STRONG_SEG, forbidden)
    cost_kg = ev_free["cargo_weight"] - ev_seg["cargo_weight"]
    live = dict(ulds=ulds, ac=ac, positions=positions, pos_by_name=pos_by_name, assign_free=a_free,
                assign_seg=a_seg, ev_free=ev_free, ev_seg=ev_seg, violations_free=v_free, violations_seg=v_seg,
                cost_kg=cost_kg, cost_pct=100 * cost_kg / ev_free["cargo_weight"] if ev_free["cargo_weight"] else 0.0)
    settings = dict(n_pos=6, width=0.5, seg_label=C.SEG_LABEL[C.SEG_STRONG], dg_share=0.6, n_ulds=8, seed=28)
    return settings, live


def test_pdf_export_baut_ohne_fehler_mit_emoji_meldung():
    settings, live = _live()
    message = "⚠️ Trennvorschrift kostet hier Ladegewicht: eine Meldung mit Emoji, Umlauten (für Ladegewicht) und Sonderzeichen."
    pdf_bytes = generate_uldk_pdf(settings, live, message)
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes[:4] == b"%PDF"
    assert len(pdf_bytes) > 500


def test_pdf_export_mit_leerer_zuordnung():
    settings, live = _live()
    live = dict(live, assign_free={}, assign_seg={})
    pdf_bytes = generate_uldk_pdf(settings, live, "✅ Trennvorschrift kostet hier nichts.")
    assert pdf_bytes[:4] == b"%PDF"


def test_pdf_safe_entfernt_nur_nicht_darstellbare_zeichen_umlaute_bleiben():
    text = "Für Größe ✅ Fenster ⚠️ Verletzung 🚫 Ende"
    safe = _pdf_safe(text)
    assert "Für Größe" in safe and "Fenster" in safe and "Verletzung" in safe and "Ende" in safe
    assert "✅" not in safe and "⚠️" not in safe and "🚫" not in safe
