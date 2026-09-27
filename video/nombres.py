# -*- coding: utf-8 -*-
"""Ecriture des nombres a l'ecran, selon la langue du rendu.

Les scenes n'ecrivent aucun mot, mais elles ecrivent des chiffres : un nombre
se lit dans les deux langues, sa typographie non (4,3 / 4.3 ; 14 057 / 14,057 ;
5 % / 5%). La langue est un parametre de rendu, fixe une fois pour toutes par
`build.py --locale` : une version anglaise se re-rend sans toucher au script.
"""

NNBSP = " "      # espace fine insecable

_LOCALES = {
    "fr": {"dec": ",", "mil": NNBSP, "pct": NNBSP + "%", "euro": ("", NNBSP + "€")},
    "en": {"dec": ".", "mil": ",", "pct": "%", "euro": ("€", "")},
}

LOCALE = "fr"


def set_locale(code):
    global LOCALE
    if code not in _LOCALES:
        raise SystemExit(f"locale inconnue : {code!r} ({', '.join(_LOCALES)})")
    LOCALE = code


def _auto(v):
    """Decimales par defaut : juste ce qu'il faut pour ecrire la valeur telle
    qu'elle est (8,81 reste 8,81), deux au plus. Arrondir une valeur sourcee
    serait la modifier."""
    for d in (0, 1):
        if abs(v - round(v, d)) < 1e-9:
            return d
    return 2


def num(v, decimals=None, group=True):
    L = _LOCALES[LOCALE]
    d = _auto(v) if decimals is None else decimals
    s = f"{v:,.{d}f}" if group else f"{v:.{d}f}"
    return s.replace(",", "\0").replace(".", L["dec"]).replace("\0", L["mil"])


def pct(v, decimals=None):
    # Pas de separateur de milliers : un pourcentage a quatre chiffres reste
    # d'un bloc, comme l'ecrivait deja style.pct.
    return num(v, decimals, group=False) + _LOCALES[LOCALE]["pct"]


def euro(v, decimals=0):
    pre, post = _LOCALES[LOCALE]["euro"]
    return pre + num(v, decimals) + post


def facteur(v, decimals=None):
    return "×" + num(v, decimals)


FORMATS = {"nombre": num, "pct": pct, "euro": euro, "facteur": facteur}


def fmt(v, kind="nombre", decimals=None):
    if kind not in FORMATS:
        raise SystemExit(f"format de nombre inconnu : {kind!r} ({', '.join(FORMATS)})")
    return FORMATS[kind](v, decimals)
