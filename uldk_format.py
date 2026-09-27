"""Zahlenformate mit deutschem Dezimalkomma (wie in den anderen Fall-Demos, z. B. uldb_format.py)."""


def fmt_num(v: float, digits: int = 1, signed: bool = False) -> str:
    text = f"{v:+.{digits}f}" if signed else f"{v:.{digits}f}"
    return text.replace(".", ",")


def fmt_pct(v: float, digits: int = 1, signed: bool = False) -> str:
    """Anteil (0..1) als Prozentzahl mit Dezimalkomma: 0.745 -> '74,5 %'."""
    return f"{fmt_num(100.0 * v, digits, signed)} %"


def fmt_kg(v: float, digits: int = 0, signed: bool = False) -> str:
    """Kilogramm mit deutschem Dezimalkomma und Tausendertrennzeichen."""
    text = f"{v:+,.{digits}f}" if signed else f"{v:,.{digits}f}"
    return text.replace(",", "X").replace(".", ",").replace("X", ".")
