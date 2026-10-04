"""AppTest: Skelett und Footer, jedes Preset, Permalink, alle Regler an Min und Max, alle drei
Meldungszustände, keine wirkungslosen Regler, PDF, Texte. Deckt DEMO-PLAYBOOK Abschnitt 5 (Browser-
Verifikation reicht AppTest allein nicht, ergänzt in AP 7 mit einem echten Browser-Durchlauf)."""
import pathlib
import re

import pytest
from streamlit.testing.v1 import AppTest

import uldk_constants as C
import uldk_results as R
from uldk_presets import PRESET_STATE_KEYS, SETTING_SPECS

APP = str(pathlib.Path(__file__).resolve().parent.parent / "app.py")
DATA = R.load_results()
FOOTER = (
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning ([Über mich](https://sebastianhanisch.net/ueber-mich.html)). "
    "Mehr zum Thema: [Luftfracht optimieren](https://sebastianhanisch.net/luftfracht-optimierung.html)."
)


def fresh(**query):
    at = AppTest.from_file(APP, default_timeout=180)
    for k, v in query.items():
        at.query_params[k] = v
    at.run()
    assert not at.exception, at.exception
    return at


def set_and_run(at, **values):
    for key, value in values.items():
        if key == "seed_input":
            at.number_input(key=key).set_value(value)
        elif key == "seg_select":
            at.selectbox(key=key).set_value(value)
        else:
            at.select_slider(key=key).set_value(value)
    at.run()
    assert not at.exception, at.exception
    return at


def click(at, label):
    next(b for b in at.button if b.label == label).click().run()
    assert not at.exception, at.exception
    return at


def state_values(at):
    return {key: at.session_state[key] for key in SETTING_SPECS}


# ---------------------------------------------------------------------------------------------------
# Skelett
# ---------------------------------------------------------------------------------------------------
def test_skeleton_and_footer():
    at = fresh()
    assert [h.value for h in at.sidebar.header] == ["⚙️ Einstellungen"]
    assert len(at.title) == 1 and at.title[0].value == "☣️ Gefahrgut-Trennung: sicher UND schwer beladen?"
    assert any(v.value.startswith("## ☣️ Eine gewichts-/schwerpunktoptimale Zuordnung") for v in at.markdown)
    assert any(v.value.startswith("### 📐 Was die Messreihe über 60 Instanzen") for v in at.markdown)
    assert [e.label for e in at.expander] == ["🔧 Wie wir das erreichen – vollständiger Methodenvergleich",
                                                "Wie funktioniert diese Demo?", "📐 Mathematische Formulierung"]
    assert any(c.value == FOOTER for c in at.caption)
    presets = [b.label for b in at.button if b.label in C.PRESETS]
    assert presets == list(C.PRESETS)
    assert len(at.sidebar.header) == 1 and len(at.sidebar.subheader) == 0


def test_preset_buttons_have_help_text():
    at = fresh()
    buttons = [b for b in at.button if b.label in C.PRESETS]
    assert all(b.help and len(b.help) > 15 for b in buttons)
    assert [b.help for b in buttons] == [C.PRESET_HELP[n] for n in C.PRESETS]


def test_no_dead_controls():
    at = fresh()
    assert not at.sidebar.checkbox and not at.sidebar.toggle and not at.checkbox and not at.toggle
    assert not at.slider  # nur select_slider/selectbox/number_input


def test_sliders_have_the_measured_stages_and_seed_bounds():
    at = fresh()
    assert list(at.select_slider(key="n_pos_slider").options) == [str(v) for v in C.N_POS_OPTIONS]
    assert list(at.select_slider(key="width_slider").options) == [str(v) for v in C.WIDTH_OPTIONS]
    assert list(at.select_slider(key="dg_share_slider").options) == [f"{int(v*100)} %" for v in C.DG_SHARE_OPTIONS]
    assert list(at.select_slider(key="ulds_slider").options) == [str(v) for v in C.ULDS_OPTIONS]
    assert list(at.selectbox(key="seg_select").options) == [C.SEG_LABEL[v] for v in C.SEG_OPTIONS]
    seed = at.number_input(key="seed_input")
    assert (seed.min, seed.max, seed.step, seed.value) == (C.SEED_RANGE[0], C.SEED_RANGE[1], 1, C.SEED_DEFAULT)


def test_default_state_and_permalink_written_to_the_address_bar():
    at = fresh()
    assert state_values(at) == dict(n_pos_slider=C.N_POS_DEFAULT, width_slider=C.WIDTH_DEFAULT,
                                     dg_share_slider=C.DG_SHARE_DEFAULT, ulds_slider=C.ULDS_DEFAULT,
                                     seg_select=C.SEG_DEFAULT, seed_input=C.SEED_DEFAULT)
    qp = {k: (v[0] if isinstance(v, list) else v) for k, v in dict(at.query_params).items()}
    assert qp["seg"] == C.SEG_DEFAULT and qp["seed"] == str(C.SEED_DEFAULT)


def test_default_view_shows_a_real_nonzero_economic_cost():
    """AP 0, PFLICHT: die Standardansicht (kein Preset geklickt) muss selbst einen echten, von 0
    verschiedenen wirtschaftlichen Preis zeigen - sonst hätte die Demo den Hauptsweep-Fehler wiederholt."""
    at = fresh()
    text = " ".join(i.value for i in at.info)
    assert "kostet hier Ladegewicht" in text
    metrics = {m.label: m.value for m in at.metric}
    assert "0 kg" not in metrics["Kostendifferenz"]


# ---------------------------------------------------------------------------------------------------
# Presets, Permalink, Regler
# ---------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("name", list(C.PRESETS))
def test_every_preset_sets_all_controls_and_runs_without_exception(name):
    at = fresh()
    click(at, name)
    p = C.PRESETS[name]
    assert state_values(at) == {PRESET_STATE_KEYS[k]: v for k, v in p.items()}


def test_permalink_sets_the_controls_and_snaps_to_stages():
    at = fresh(pos="4", width="0.3", share="0.6", n="16", seg="streng", seed="17")
    assert state_values(at) == dict(n_pos_slider=4, width_slider=0.3, dg_share_slider=0.6, ulds_slider=16,
                                     seg_select="streng", seed_input=17)
    at = fresh(pos="5", width="0.4", share="0.5", n="15", seg="mittel", seed="-4")
    vals = state_values(at)
    assert vals["seg_select"] == C.SEG_DEFAULT  # ungültiger Text: Standard
    assert vals["n_pos_slider"] in C.N_POS_OPTIONS and vals["width_slider"] in C.WIDTH_OPTIONS
    assert vals["dg_share_slider"] in C.DG_SHARE_OPTIONS and vals["ulds_slider"] in C.ULDS_OPTIONS
    assert vals["seed_input"] == C.SEED_RANGE[0]  # -4 wird auf die Untergrenze begrenzt


def test_all_controls_at_min_and_max_run_without_exception():
    at = fresh()
    for key, options in (("n_pos_slider", C.N_POS_OPTIONS), ("width_slider", C.WIDTH_OPTIONS),
                          ("dg_share_slider", C.DG_SHARE_OPTIONS), ("ulds_slider", C.ULDS_OPTIONS)):
        for v in (options[0], options[-1]):
            set_and_run(at, **{key: v})
            assert state_values(at)[key] == v
    for v in C.SEG_OPTIONS:
        set_and_run(at, seg_select=v)
        assert state_values(at)["seg_select"] == v
    for v in C.SEED_RANGE:
        set_and_run(at, seed_input=v)
        assert state_values(at)["seed_input"] == v


def test_new_instance_button_rolls_a_new_seed(monkeypatch):
    import uldk_presets as P
    frozen = iter([3, 5, C.SEED_DEFAULT, 3])
    monkeypatch.setattr(P.random, "randint", lambda lo, hi: next(frozen))
    at = fresh()
    seen = {at.session_state["seed_input"]}
    for _ in range(3):
        click(at, "🎲 Neue Instanz")
        seen.add(at.session_state["seed_input"])
        assert C.SEED_RANGE[0] <= at.session_state["seed_input"] <= C.SEED_RANGE[1]
    assert seen == {C.SEED_DEFAULT, 3, 5}


# ---------------------------------------------------------------------------------------------------
# Meldungszustände, Kennzahlen, Texte
# ---------------------------------------------------------------------------------------------------
def test_all_three_message_states_are_reachable_through_the_controls():
    at = fresh(pos="6", width="0.5", share="0.6", n="8", seg="streng", seed="28")  # Standard: kostet
    assert "kostet hier Ladegewicht" in " ".join(i.value for i in at.info)
    at = fresh(pos="10", width="0.5", share="0.4", n="12", seg="standard", seed="0")  # Lockere Trennung: nichts
    assert "kostet hier nichts" in " ".join(i.value for i in at.info)
    at = fresh(pos="10", width="0.5", share="0.2", n="8", seg="standard", seed="1")  # unsicher, aber kostenlos
    assert "unsicher gewesen" in " ".join(i.value for i in at.info)


def test_main_metrics_are_present():
    at = fresh()
    assert len(at.metric) >= 4


def test_pdf_download_button_is_present_and_named():
    at = fresh()
    buttons = at.get("download_button")
    assert len(buttons) == 1 and buttons[0].proto.label == "📄 Gefahrgut-Beladeplan als PDF herunterladen"


def test_all_plotly_charts_render_with_unique_keys():
    at = fresh()
    charts = at.get("plotly_chart")
    assert len(charts) >= 3
    ids = [c.proto.id for c in charts]
    assert len(set(ids)) == len(ids)


def test_no_dead_file_links_in_markdown():
    at = fresh()
    for md in list(at.markdown) + list(at.caption):
        for target in re.findall(r"\]\(([^)]+)\)", md.value):
            assert target.startswith("https://"), (target, md.value[:80])


def test_real_umlauts_present():
    at = fresh()
    text = " ".join(m.value for m in at.markdown) + " ".join(c.value for c in at.caption)
    assert "Schwerpunktfenster" in text and "für" in text and "Gewichtsgrenze" in text


def test_regime_table_is_not_a_dead_column():
    """Nullspalten-Signal: keine Spalte der Regime-Tabelle ist überall gleich."""
    at = fresh()
    regime_frame = next(d.value for d in at.dataframe if "Preis (kg, Mittel)" in d.value.columns)
    assert len(regime_frame) == 4
    for col in ("Preis (%)", "Preis (kg, Mittel)"):
        assert regime_frame[col].astype(str).nunique() > 1


def test_expander_texts_state_the_limits():
    at = fresh()
    how = next(m.value for m in at.markdown if "Nicht Teil dieser Demo" in m.value)
    for needle in ("IATA-DGR", "uld-beladeplan-demo", "erfunden, nicht kalibriert", "streng"):
        assert needle in how, needle
    math = next(m.value for m in at.markdown if "Implementiert in" in m.value)
    for needle in ("uldk_model.py", "uldk_oracle.py"):
        assert needle in math, needle
