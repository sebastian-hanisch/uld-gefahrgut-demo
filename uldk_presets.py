"""Reglerspezifikation, Permalink, Presets, Seed-Knopf - Standardmuster aus dem OR-Demo-Portfolio (siehe
uldb_presets.py). Fünf Regler sind feste Stufen (Fensterbreite, Gefahrgutanteil, ULD-Zahl, Positionszahl,
Trennvorschrift-Stärke - die vier Sweep-Dimensionen der Messreihe plus die Trennvorschrift-Auswahl selbst),
einer ist ein Zahlenbereich (Seed): beim Permalink wird jeder Wert auf den Bereich begrenzt bzw. auf die
nächste Stufe eingerastet, damit die Adresszeile nie einen Wert außerhalb des Rasters in den Regler
schreibt."""
import math
import random
from dataclasses import dataclass
from typing import Callable, Optional

import streamlit as st

import uldk_constants as C


def _text(value):
    return str(value)


def _num(value):
    return f"{value:g}"


@dataclass(frozen=True)
class SettingSpec:
    url_param: str
    caster: Callable
    default: object
    lo: Optional[float] = None
    hi: Optional[float] = None
    options: Optional[tuple] = None
    encoder: Callable = _text


SETTING_SPECS = {
    "width_slider": SettingSpec("width", float, C.WIDTH_DEFAULT, options=C.WIDTH_OPTIONS, encoder=_num),
    "dg_share_slider": SettingSpec("share", float, C.DG_SHARE_DEFAULT, options=C.DG_SHARE_OPTIONS, encoder=_num),
    "ulds_slider": SettingSpec("n", int, C.ULDS_DEFAULT, options=C.ULDS_OPTIONS),
    "n_pos_slider": SettingSpec("pos", int, C.N_POS_DEFAULT, options=C.N_POS_OPTIONS),
    "seg_select": SettingSpec("seg", str, C.SEG_DEFAULT, options=C.SEG_OPTIONS),
    "seed_input": SettingSpec("seed", int, C.SEED_DEFAULT, *C.SEED_RANGE),
}

PRESET_STATE_KEYS = {
    "width": "width_slider", "dg_share": "dg_share_slider", "n_ulds": "ulds_slider",
    "n_pos": "n_pos_slider", "seg": "seg_select", "seed": "seed_input",
}


def bounds(state_key):
    spec = SETTING_SPECS[state_key]
    return spec.lo, spec.hi


def parse_setting(spec, raw):
    """Wert aus der Adresszeile: umwandeln, auf den Bereich begrenzen bzw. auf die nächste Stufe einrasten.
    None, wenn er sich nicht auswerten lässt."""
    if spec.caster is str:
        return raw if raw in spec.options else None
    try:
        value = float(raw)
    except (ValueError, TypeError):
        return None
    if not math.isfinite(value):
        return None
    if spec.options:
        return min(spec.options, key=lambda o: (abs(o - value), o))
    return int(round(max(spec.lo, min(spec.hi, value))))


def init_session_state_defaults():
    for state_key, spec in SETTING_SPECS.items():
        if state_key not in st.session_state:
            st.session_state[state_key] = spec.default


def load_permalink_settings():
    if "permalink_loaded" in st.session_state:
        return
    qp = st.query_params
    for state_key, spec in SETTING_SPECS.items():
        if spec.url_param in qp:
            value = parse_setting(spec, qp[spec.url_param])
            if value is not None:
                st.session_state[state_key] = value
    st.session_state["permalink_loaded"] = True


def sync_query_params(values):
    """values: dict state_key -> aktueller Wert (aus den Widgets)."""
    try:
        for state_key, value in values.items():
            st.query_params[SETTING_SPECS[state_key].url_param] = SETTING_SPECS[state_key].encoder(value)
    except Exception:
        pass


def apply_preset(name):
    for field, state_key in PRESET_STATE_KEYS.items():
        st.session_state[state_key] = C.PRESETS[name][field]


def randomize_seed():
    st.session_state["seed_input"] = random.randint(*C.SEED_RANGE)
