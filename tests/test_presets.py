"""Tests für uldk_presets.py: Permalink-Parsing, Einrasten auf Stufen, Presets."""
import uldk_constants as C
import uldk_presets as P


def test_alle_presets_haben_gueltige_werte():
    for name, p in C.PRESETS.items():
        assert p["width"] in C.WIDTH_OPTIONS
        assert p["dg_share"] in C.DG_SHARE_OPTIONS
        assert p["n_ulds"] in C.ULDS_OPTIONS
        assert p["n_pos"] in C.N_POS_OPTIONS
        assert p["seg"] in C.SEG_OPTIONS
        assert C.SEED_RANGE[0] <= p["seed"] <= C.SEED_RANGE[1]


def test_settings_specs_deckt_alle_fuenf_stufen_regler_plus_seed_ab():
    assert set(P.SETTING_SPECS) == {"width_slider", "dg_share_slider", "ulds_slider", "n_pos_slider",
                                     "seg_select", "seed_input"}


def test_parse_setting_rastet_zahl_auf_naechste_stufe_ein():
    spec = P.SETTING_SPECS["width_slider"]
    assert P.parse_setting(spec, "0.9") == 1.0
    assert P.parse_setting(spec, "0.4") == 0.5

    spec_pos = P.SETTING_SPECS["n_pos_slider"]
    assert P.parse_setting(spec_pos, "5") == 4
    assert P.parse_setting(spec_pos, "8") == 10 or P.parse_setting(spec_pos, "8") == 6  # nächstliegend


def test_parse_setting_text_nur_bei_exaktem_treffer():
    spec = P.SETTING_SPECS["seg_select"]
    assert P.parse_setting(spec, "streng") == "streng"
    assert P.parse_setting(spec, "sehr_streng") is None


def test_parse_setting_seed_wird_begrenzt():
    spec = P.SETTING_SPECS["seed_input"]
    assert P.parse_setting(spec, "500") == C.SEED_RANGE[1]
    assert P.parse_setting(spec, "-5") == C.SEED_RANGE[0]


def test_parse_setting_ungueltige_zahl_gibt_none():
    spec = P.SETTING_SPECS["width_slider"]
    assert P.parse_setting(spec, "abc") is None
    assert P.parse_setting(spec, "nan") is None
    assert P.parse_setting(spec, "inf") is None


def test_bounds_liefert_lo_hi_fuer_seed():
    lo, hi = P.bounds("seed_input")
    assert (lo, hi) == C.SEED_RANGE


def test_preset_state_keys_deckt_alle_preset_felder_ab():
    any_preset = next(iter(C.PRESETS.values()))
    assert set(P.PRESET_STATE_KEYS) == set(any_preset)
