# -*- coding: utf-8 -*-
"""Ecriture des nombres a l'ecran, selon la langue du rendu.

Les scenes n'ecrivent aucun mot, mais elles ecrivent des chiffres : un nombre
se lit dans les deux langues, sa typographie non (4,3 / 4.3 ; 14 057 / 14,057 ;
5 % / 5%). La langue est un parametre de rendu, fixe une fois pour toutes par
`build.py --locale` : une version anglaise se re-rend sans toucher au script.
"""

NNBSP = " "      # espace fine insecable
NBSP = "\u00a0"       # espace insecable, de la largeur d'une espace ordinaire

# Un nombre ne se coupe jamais en fin de ligne (regle du 17/11/2026) : ni
# entre ses groupes de chiffres (« 1 590 »), ni avant son unite - un signe
# (« 16 860 EUR », « 8,33 % ») ou le nom qui le suit (« 1 590 essais »,
# « 20 ans »). Les mots de liaison ne sont pas des unites : « 1 118 contre
# 472 » peut passer a la ligne avant « contre ».
_LIAISONS = {"a", "à", "au", "aux", "avant", "apres", "après", "avec", "contre", "dans", "de",
             "depuis", "des", "du", "en", "et", "ou", "par", "pour", "puis", "sans", "soit",
             "sur", "vs", "le", "la", "les", "un", "une", "est", "sont", "dont", "que", "qui"}
_ESPACES = " " + NBSP + NNBSP


def insecables(s):
    """`s`, les espaces qu'une fin de ligne ne doit pas couper remplacees par
    des espaces insecables (meme largeur a l'ecran : le rendu d'une ligne ne
    change pas). Une espace fine insecable deja ecrite reste telle quelle."""
    import re
    esp = "[" + _ESPACES + "]"

    def lie(m):
        return m.group(0) if m.group(0) == NNBSP else NBSP

    # Groupes de chiffres : « 1 590 », « 574 534 ».
    s = re.sub(r"(?<=\d)" + esp + r"(?=\d{3}(?!\d))", lie, s)
    # Unite en signe : « 8,33 % », « 16 860 EUR », « 1 $ ».
    s = re.sub(r"(?<=\d)" + esp + r"(?=[%€$‰])", lie, s)

    # Unite en toutes lettres : le nom qui suit le nombre.
    def mot(m):
        return (m.group(1) if m.group(2).casefold() in _LIAISONS
                else lie(re.match(esp, m.group(1)))) + m.group(2)

    return re.sub(r"(?<=\d)(" + esp + r")([^\W\d_]+)", mot, s)


def coupures(texte):
    """Les nombres qu'un retour a la ligne coupe dans `texte` (lignes separees
    par « \n ») : [(fin de ligne, debut de la suivante)]. Pour make check."""
    lignes = [l.strip() for l in str(texte).split("\n")]
    out = []
    for a, b in zip(lignes, lignes[1:]):
        if a and b and insecables(a + " " + b)[len(a)] != " ":
            out.append((a.split(" ")[-1], b.split(" ")[0]))
    return out

_LOCALES = {
    "fr": {"dec": ",", "mil": NNBSP, "pct": NNBSP + "%", "euro": ("", NNBSP + "€"),
           "dollar": ("", NNBSP + "$")},
    "en": {"dec": ".", "mil": ",", "pct": "%", "euro": ("€", ""), "dollar": ("$", "")},
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


def dollar(v, decimals=None):
    # Decimales par defaut : celles de la valeur (1 $, 1,16 $), comme un nombre.
    pre, post = _LOCALES[LOCALE]["dollar"]
    return pre + num(v, decimals) + post


def facteur(v, decimals=None):
    return "×" + num(v, decimals)


FORMATS = {"nombre": num, "pct": pct, "euro": euro, "dollar": dollar, "facteur": facteur}


def fmt(v, kind="nombre", decimals=None):
    if kind not in FORMATS:
        raise SystemExit(f"format de nombre inconnu : {kind!r} ({', '.join(FORMATS)})")
    return FORMATS[kind](v, decimals)
