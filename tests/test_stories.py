"""Tests für uldk_stories.py: jedes der fünf Presets besteht sein Abnahmekriterium gegen data/uldk_results.json."""
import uldk_results as R
import uldk_stories as S

D = R.load_results()


def test_alle_presets_bestehen_ihr_abnahmekriterium():
    results = S.check_all(D)
    assert set(results) == set(S.CHECKS)
    for name, (ok, msg) in results.items():
        assert ok, f"{name}: {msg}"


def test_wenige_positionen_kostet_mehr_als_standard():
    """Der zentrale AP-0-Befund als eigener Test: weniger Positionen (4 statt 6) bei sonst gleicher
    Einstellung erhöht den gemessenen wirtschaftlichen Preis."""
    ok, msg = S.check_wenige_positionen(D)
    assert ok, msg


def test_lockere_trennung_kostet_exakt_null():
    ok, msg = S.check_lockere_trennung(D)
    assert ok, msg
