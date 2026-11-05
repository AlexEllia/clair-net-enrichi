# -*- coding: utf-8 -*-
"""Identite de chaine - Clair net enrichi : pistes de logo.

Chaque piste est une fonction qui dessine dans un carre unite (0..1, y vers
le bas) avec un contexte cairo. Le meme dessin sort en SVG (traces purs, texte
vectorise) et en PNG a n'importe quelle taille : une seule geometrie, aucun
ecart entre le maitre et les exports.

Couleurs : lues dans video/style.py (source unique de la charte).
Police : Selawik (OFL, equivalent metrique libre de Segoe UI), dans
assets/polices/selawik/. Les glyphes sont convertis en traces via fontTools.

    python identite/logo.py exploration [1|2]   # planche des pistes du tour
"""

import math
import sys
from pathlib import Path

import cairo
from fontTools.pens.basePen import BasePen
from fontTools.ttLib import TTFont

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE / "video"))
import style  # noqa: E402

POLICES = RACINE / "assets" / "polices" / "selawik"
SORTIE = Path(__file__).resolve().parent


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


# --- Palettes ----------------------------------------------------------------
# a = couleur d'effort (bleu), b = couleur de resultat (ambre), fond = None
# pour un fond transparent. Les versions monochromes ramenent a et b a une
# seule teinte : chaque piste doit rester lisible ainsi.

COULEUR = {"a": style.CONTRIB, "b": style.INTEREST, "fond": style.BG}
BLANC = {"a": "#FFFFFF", "b": "#FFFFFF", "fond": None}
NOIR = {"a": "#000000", "b": "#000000", "fond": None}


# --- Texte vectorise -----------------------------------------------------------

class _PlumeCairo(BasePen):
    """Convertit les contours TrueType en chemin cairo (y de la police vers le haut)."""

    def __init__(self, glyphset, ctx, x, y, echelle):
        super().__init__(glyphset)
        self.ctx, self.x, self.y, self.k = ctx, x, y, echelle

    def _p(self, pt):
        return self.x + pt[0] * self.k, self.y - pt[1] * self.k

    def _moveTo(self, pt):
        self.ctx.move_to(*self._p(pt))

    def _lineTo(self, pt):
        self.ctx.line_to(*self._p(pt))

    def _curveToOne(self, p1, p2, p3):
        self.ctx.curve_to(*self._p(p1), *self._p(p2), *self._p(p3))

    def _closePath(self):
        self.ctx.close_path()


_fontes = {}


def fonte(graisse="b"):
    """graisse : '' (Regular), 'sb' (Semibold), 'b' (Bold), 'l', 'sl'."""
    if graisse not in _fontes:
        _fontes[graisse] = TTFont(str(POLICES / f"selawk{graisse}.ttf"))
    return _fontes[graisse]


def chasse(texte, graisse="b"):
    """Largeur du texte en unites de la police.

    Pas de crenage : Selawik 1.01 n'en a pas (sa table GPOS ne place que les
    accents). L'espacement est celui dessine par la police."""
    f = fonte(graisse)
    cmap, hmtx = f.getBestCmap(), f["hmtx"]
    return sum(hmtx[cmap[ord(c)]][0] for c in texte)


def texte(ctx, s, x, y, corps, graisse="b"):
    """Ajoute au chemin courant le texte s, ligne de base en (x, y), corps = em."""
    f = fonte(graisse)
    gs, cmap, hmtx = f.getGlyphSet(), f.getBestCmap(), f["hmtx"]
    k = corps / f["head"].unitsPerEm
    for c in s:
        nom = cmap[ord(c)]
        gs[nom].draw(_PlumeCairo(gs, ctx, x, y, k))
        x += hmtx[nom][0] * k
    return x


def boite_glyphe(c, graisse="b"):
    """Boite (xMin, yMin, xMax, yMax) d'un glyphe, en unites de la police."""
    f = fonte(graisse)
    g = f["glyf"][f.getBestCmap()[ord(c)]]
    return g.xMin, g.yMin, g.xMax, g.yMax


# --- Outils de trace -------------------------------------------------------------

def trait(ctx, couleur, largeur, pts, fermer=False):
    ctx.set_source_rgb(*rgb(couleur))
    ctx.set_line_width(largeur)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.move_to(*pts[0])
    for p in pts[1:]:
        ctx.line_to(*p)
    if fermer:
        ctx.close_path()
    ctx.stroke()


# --- Piste A : le croisement --------------------------------------------------------
# La droite des versements cumules et la courbe des interets cumules partent
# du meme point, comme sur les graphes des episodes : la courbe reste d'abord
# sous la droite, puis la croise et s'envole. Elle est tracee par-dessus.

A_K = 5.0            # courbure de l'exponentielle
A_PENTE = 0.52       # hauteur atteinte par la droite en bout de course
A_EP = 0.075         # epaisseur des traits


def _a_xy(t, u):
    return 0.15 + 0.70 * t, 0.83 - 0.68 * u


def piste_a(ctx, pal):
    trait(ctx, pal["a"], A_EP, [_a_xy(0, 0), _a_xy(1, A_PENTE)])
    pts = [_a_xy(t, (math.exp(A_K * t) - 1) / (math.exp(A_K) - 1))
           for t in (i / 200 for i in range(201))]
    trait(ctx, pal["b"], A_EP, pts)


# --- Piste B : le monogramme -----------------------------------------------------------
# Un C ouvert (bleu) qui tient une ligature N-E (ambre) : le N et le E partagent
# leur fut, et les bras du E sortent par l'ouverture du C.

def piste_b(ctx, pal):
    ep_c, ep_l = 0.085, 0.07
    r, ouv = 0.37, math.radians(42)
    ctx.set_source_rgb(*rgb(pal["a"]))
    ctx.set_line_width(ep_c)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.new_path()
    ctx.arc(0.5, 0.5, r, ouv, 2 * math.pi - ouv)
    ctx.stroke()
    h0, h1 = 0.335, 0.665           # haut et bas de la ligature
    x0, xf, xe = 0.32, 0.53, 0.75   # fut gauche du N, fut commun, bout des bras
    b = pal["b"]
    trait(ctx, b, ep_l, [(x0, h1), (x0, h0), (xf, h1), (xf, h0)])
    trait(ctx, b, ep_l, [(xf, h0), (xe, h0)])
    trait(ctx, b, ep_l, [(xf, 0.5), (xe - 0.04, 0.5)])
    trait(ctx, b, ep_l, [(xf, h1), (xe, h1)])


# --- Piste C : la lentille ---------------------------------------------------------------
# Une lentille convergente (bleu) et un rayon : il entre a plat, sous l'axe,
# et ressort en montant vers le foyer (ambre). Optiquement juste : la clarte
# qui transforme l'effort en resultat.

def piste_c(ctx, pal):
    ep = 0.07
    xl, hl, fl = 0.42, 0.37, 0.13         # centre, demi-hauteur, bombe de la lentille
    R = (hl ** 2 + fl ** 2) / (2 * fl)
    phi = math.asin(hl / R)
    ctx.set_source_rgb(*rgb(pal["a"]))
    ctx.set_line_width(ep)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.new_path()
    ctx.arc(xl + fl - R, 0.5, R, -phi, phi)               # face droite
    ctx.arc(xl - fl + R, 0.5, R, math.pi - phi, math.pi + phi)  # face gauche
    ctx.close_path()
    ctx.stroke()
    y_in, foyer = 0.64, 0.22
    trait(ctx, pal["a"], ep, [(0.06, y_in), (xl, y_in)])
    pente = (y_in - 0.5) / foyer
    x_out = 0.92
    trait(ctx, pal["b"], ep, [(xl, y_in), (x_out, y_in - pente * (x_out - xl))])


# --- Piste D : c puissance n ----------------------------------------------------------------
# Purement typographique : « c » et un exposant « n » (ambre), lu comme c^n.
# C, N : Clair net ; l'exposant, c'est l'enrichissement, la capitalisation.

def piste_d(ctx, pal):
    g = "b"
    upm = fonte(g)["head"].unitsPerEm
    c_box, n_box = boite_glyphe("c", g), boite_glyphe("n", g)
    k_exp = 0.62                       # corps de l'exposant / corps du c
    approche = -0.02 * upm             # rapproche l'exposant du c
    # largeur et hauteur du groupe, en unites du corps du c
    l_c = c_box[2] - c_box[0]
    l_n = (n_box[2] - n_box[0]) * k_exp
    l_tot = l_c + approche + l_n
    h_c = c_box[3] - c_box[1]
    monte = h_c * 0.78                 # ligne de base de l'exposant au-dessus de celle du c
    h_tot = monte + n_box[3] * k_exp - c_box[1]
    corps = 0.70 / max(l_tot, h_tot) * upm
    k = corps / upm
    x0 = 0.5 - l_tot * k / 2 - c_box[0] * k
    y0 = 0.5 + h_tot * k / 2 + c_box[1] * k
    ctx.new_path()
    texte(ctx, "c", x0, y0, corps, g)
    ctx.set_source_rgb(*rgb(pal["a"] if pal is not COULEUR else style.INK))
    ctx.fill()
    xn = x0 + (c_box[2] + approche) * k - n_box[0] * k * k_exp
    texte(ctx, "n", xn, y0 - monte * k, corps * k_exp, g)
    ctx.set_source_rgb(*rgb(pal["b"]))
    ctx.fill()


# --- Second tour : des objets, en aplats ------------------------------------------------
# Retour d'Alexandre sur le premier tour : trop abstrait, n'attire pas l'oeil.
# D'ou des objets reconnaissables au premier regard et de grandes masses
# d'ambre pleines plutot que des traits fins.

def remplir(ctx, couleur, pts):
    ctx.set_source_rgb(*rgb(couleur))
    ctx.new_path()
    ctx.move_to(*pts[0])
    for p in pts[1:]:
        ctx.line_to(*p)
    ctx.close_path()
    ctx.fill()


def _chemin_sablier(ctx, xg, xd, cou, haut, bas):
    ctx.new_path()
    ctx.move_to(xg, haut)
    ctx.curve_to(xg, 0.37, 0.5 - cou, 0.42, 0.5 - cou, 0.5)
    ctx.curve_to(0.5 - cou, 0.58, xg, 0.63, xg, bas)
    ctx.line_to(xd, bas)
    ctx.curve_to(xd, 0.63, 0.5 + cou, 0.58, 0.5 + cou, 0.5)
    ctx.curve_to(0.5 + cou, 0.42, xd, 0.37, xd, haut)
    ctx.close_path()


def piste_e(ctx, pal):
    """Sablier : peu de sable en haut (bleu), un gros tas en bas (ambre)."""
    a, b = pal["a"], pal["b"]
    xg, xd, cou, haut, bas = 0.31, 0.69, 0.03, 0.17, 0.83
    ctx.save()
    _chemin_sablier(ctx, xg, xd, cou, haut, bas)
    ctx.clip()
    remplir(ctx, a, [(0.2, 0.39), (0.8, 0.39), (0.8, 0.5), (0.2, 0.5)])
    ctx.set_source_rgb(*rgb(b))
    ctx.new_path()
    ctx.move_to(0.2, 0.9)
    ctx.line_to(0.2, 0.75)
    ctx.curve_to(0.36, 0.70, 0.44, 0.60, 0.5, 0.60)
    ctx.curve_to(0.56, 0.60, 0.64, 0.70, 0.8, 0.75)
    ctx.line_to(0.8, 0.9)
    ctx.close_path()
    ctx.fill()
    ctx.restore()
    trait(ctx, b, 0.028, [(0.5, 0.5), (0.5, 0.62)])
    _chemin_sablier(ctx, xg, xd, cou, haut, bas)
    ctx.set_source_rgb(*rgb(a))
    ctx.set_line_width(0.055)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.stroke()
    for y in (0.135, 0.865):
        trait(ctx, a, 0.075, [(0.25, y), (0.75, y)])


def piste_f(ctx, pal):
    """Phare : tour rayee (bleu), lanterne et faisceaux (ambre)."""
    a, b = pal["a"], pal["b"]
    cx, y_haut, y_bas, demi_h, demi_b = 0.47, 0.45, 0.86, 0.065, 0.11

    def x_a(y):
        t = (y - y_haut) / (y_bas - y_haut)
        return demi_h + (demi_b - demi_h) * t

    # tour en trois troncons : les vides font les rayures
    for y0, y1 in ((y_haut, 0.56), (0.62, 0.70), (0.76, y_bas)):
        remplir(ctx, a, [(cx - x_a(y0), y0), (cx + x_a(y0), y0),
                         (cx + x_a(y1), y1), (cx - x_a(y1), y1)])
    trait(ctx, a, 0.06, [(0.27, 0.89), (0.67, 0.89)])              # rocher
    trait(ctx, a, 0.045, [(cx - 0.11, 0.425), (cx + 0.11, 0.425)])   # galerie
    remplir(ctx, b, [(cx - 0.05, 0.31), (cx + 0.05, 0.31),
                     (cx + 0.05, 0.39), (cx - 0.05, 0.39)])          # lanterne
    remplir(ctx, a, [(cx - 0.085, 0.30), (cx + 0.085, 0.30), (cx, 0.20)])  # toit
    # faisceaux : un long vers la droite, un court vers la gauche
    remplir(ctx, b, [(cx + 0.075, 0.33), (0.96, 0.17), (0.96, 0.47), (cx + 0.075, 0.37)])
    remplir(ctx, b, [(cx - 0.075, 0.33), (0.10, 0.24), (0.10, 0.42), (cx - 0.075, 0.37)])


def piste_g(ctx, pal):
    """Loupe : sous la lentille, l'aire de la courbe des interets (ambre)."""
    a, b = pal["a"], pal["b"]
    cx, cy, r, ep = 0.42, 0.42, 0.255, 0.085
    ctx.save()
    ctx.new_path()
    ctx.arc(cx, cy, r, 0, 2 * math.pi)
    ctx.clip()
    ctx.set_source_rgb(*rgb(b))
    ctx.new_path()
    x0, x1 = cx - r, cx + r
    ctx.move_to(x0, 0.9)
    for i in range(101):
        t = i / 100
        u = (math.exp(4.0 * t) - 1) / (math.exp(4.0) - 1)
        ctx.line_to(x0 + (x1 - x0) * t, 0.52 - 0.34 * u)
    ctx.line_to(x1, 0.9)
    ctx.close_path()
    ctx.fill()
    ctx.restore()
    ctx.set_source_rgb(*rgb(a))
    ctx.set_line_width(ep)
    ctx.new_path()
    ctx.arc(cx, cy, r, 0, 2 * math.pi)
    ctx.stroke()
    d = (r + ep / 2) / math.sqrt(2)
    trait(ctx, a, 0.13, [(cx + d + 0.02, cy + d + 0.02), (0.85, 0.85)])


def _feuille(ctx, couleur, base, pointe, largeur, largeur2=None):
    """Feuille de base a pointe ; largeur2 donne un bord moins bombe (aile)."""
    (px, py), (qx, qy) = base, pointe
    dx, dy = qx - px, qy - py
    n = math.hypot(dx, dy)
    nx, ny = -dy / n, dx / n
    w1, w2 = largeur, largeur if largeur2 is None else largeur2
    ctx.set_source_rgb(*rgb(couleur))
    ctx.new_path()
    ctx.move_to(px, py)
    ctx.curve_to(px + dx * 0.25 + nx * w1, py + dy * 0.25 + ny * w1,
                 px + dx * 0.70 + nx * w1, py + dy * 0.70 + ny * w1, qx, qy)
    ctx.curve_to(px + dx * 0.70 - nx * w2, py + dy * 0.70 - ny * w2,
                 px + dx * 0.25 - nx * w2, py + dy * 0.25 - ny * w2, px, py)
    ctx.close_path()
    ctx.fill()


def piste_h(ctx, pal):
    """Pousse : la tige (bleu, l'effort) porte deux feuilles (ambre, le resultat)."""
    a, b = pal["a"], pal["b"]
    trait(ctx, a, 0.07, [(0.22, 0.86), (0.78, 0.86)])
    ctx.set_source_rgb(*rgb(a))
    ctx.set_line_width(0.07)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.new_path()
    ctx.move_to(0.5, 0.86)
    ctx.curve_to(0.5, 0.70, 0.47, 0.60, 0.5, 0.46)
    ctx.stroke()
    _feuille(ctx, b, (0.5, 0.47), (0.86, 0.16), 0.16)
    _feuille(ctx, b, (0.49, 0.53), (0.15, 0.33), 0.11)


# --- Troisieme tour : sablier, pousse et liberte -----------------------------------------
# Retour d'Alexandre sur le tour 2 : il garde le sablier (symbole, symetrie) et
# la pousse (esthetique), et veut que la liberte financiere se voie.

def _sablier(ctx, cx, y0, y1, demi, cou, fermer=True):
    """Chemin du verre, du haut y0 au bas y1 ; fermer=False le laisse ouvert en haut."""
    ym, h = (y0 + y1) / 2, y1 - y0
    ctx.new_path()
    ctx.move_to(cx - demi, y0)
    ctx.curve_to(cx - demi, y0 + 0.30 * h, cx - cou, ym - 0.12 * h, cx - cou, ym)
    ctx.curve_to(cx - cou, ym + 0.12 * h, cx - demi, y1 - 0.30 * h, cx - demi, y1)
    ctx.line_to(cx + demi, y1)
    ctx.curve_to(cx + demi, y1 - 0.30 * h, cx + cou, ym + 0.12 * h, cx + cou, ym)
    ctx.curve_to(cx + cou, ym - 0.12 * h, cx + demi, y0 + 0.30 * h, cx + demi, y0)
    if fermer:
        ctx.close_path()


def _flancs_bas(ctx, cx, y0, y1, demi, cou):
    """Les deux flancs du bulbe du bas, ouverts au col."""
    ym, h = (y0 + y1) / 2, y1 - y0
    ctx.new_path()
    for s in (-1, 1):
        ctx.move_to(cx + s * cou, ym)
        ctx.curve_to(cx + s * cou, ym + 0.12 * h, cx + s * demi, y1 - 0.30 * h, cx + s * demi, y1)


def _tas(ctx, couleur, cx, y0, y1, demi):
    """Sable du bulbe du bas ; a remplir sous un clip du verre. Rend le sommet."""
    ym, h = (y0 + y1) / 2, y1 - y0
    pic, bord, ctrl = ym + 0.15 * h, ym + 0.38 * h, ym + 0.30 * h
    ctx.set_source_rgb(*rgb(couleur))
    ctx.new_path()
    ctx.move_to(cx - demi - 0.1, y1 + 0.1)
    ctx.line_to(cx - demi - 0.1, bord)
    ctx.curve_to(cx - 0.74 * demi, ctrl, cx - 0.32 * demi, pic, cx, pic)
    ctx.curve_to(cx + 0.32 * demi, pic, cx + 0.74 * demi, ctrl, cx + demi + 0.1, bord)
    ctx.line_to(cx + demi + 0.1, y1 + 0.1)
    ctx.close_path()
    ctx.fill()
    return pic


def _verre_et_sable(ctx, pal, cx, y0, y1, demi, cou, ep, fermer=True):
    ctx.save()
    _sablier(ctx, cx, y0, y1, demi, cou)
    ctx.clip()
    pic = _tas(ctx, pal["b"], cx, y0, y1, demi)
    ctx.restore()
    _sablier(ctx, cx, y0, y1, demi, cou, fermer)
    ctx.set_source_rgb(*rgb(pal["a"]))
    ctx.set_line_width(ep)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.stroke()
    return pic


def _miroir(ctx, dessin):
    """Dessine puis redessine en symetrie autour de l'axe x = 0.5."""
    dessin()
    ctx.save()
    ctx.translate(1, 0)
    ctx.scale(-1, 1)
    dessin()
    ctx.restore()


def piste_i(ctx, pal):
    """Sablier en fleur : le bulbe du haut est remplace par deux feuilles."""
    a, b = pal["a"], pal["b"]
    cx, y0, y1, demi, cou = 0.5, 0.17, 0.83, 0.19, 0.03
    ctx.save()
    _sablier(ctx, cx, y0, y1, demi, cou)
    ctx.clip()
    pic = _tas(ctx, b, cx, y0, y1, demi)
    ctx.restore()
    _flancs_bas(ctx, cx, y0, y1, demi, cou)
    ctx.set_source_rgb(*rgb(a))
    ctx.set_line_width(0.055)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.stroke()
    trait(ctx, b, 0.04, [(cx, pic + 0.02), (cx, 0.44)])
    _miroir(ctx, lambda: _feuille(ctx, b, (cx, 0.46), (0.23, 0.14), 0.085))
    trait(ctx, a, 0.075, [(0.25, 0.865), (0.75, 0.865)])


def piste_j(ctx, pal):
    """L'envol : une graine dont les deux feuilles sont des ailes."""
    a, b = pal["a"], pal["b"]
    trait(ctx, a, 0.06, [(0.5, 0.50), (0.5, 0.74)])
    ctx.set_source_rgb(*rgb(a))
    ctx.new_path()
    ctx.arc(0.5, 0.80, 0.075, 0, 2 * math.pi)
    ctx.fill()
    _miroir(ctx, lambda: _feuille(ctx, b, (0.5, 0.52), (0.07, 0.22), 0.04, 0.16))


def piste_k(ctx, pal):
    """La cle du temps : un sablier pour anneau, des feuilles pour dents."""
    a, b = pal["a"], pal["b"]
    cx, y0, y1, demi = 0.5, 0.11, 0.45, 0.15
    _verre_et_sable(ctx, pal, cx, y0, y1, demi, 0.025, 0.05)
    for y in (y0 - 0.025, y1 + 0.025):
        trait(ctx, a, 0.06, [(cx - 0.19, y), (cx + 0.19, y)])
    trait(ctx, a, 0.075, [(cx, y1 + 0.03), (cx, 0.90)])
    _feuille(ctx, b, (cx, 0.70), (0.78, 0.66), 0.06)
    _feuille(ctx, b, (cx, 0.84), (0.72, 0.81), 0.055)


def piste_l(ctx, pal, gras=1.0):
    """Sablier ouvert : sans couvercle, la pousse traverse le verre et sort.

    gras epaissit les traits et les feuilles (gravure peu contrastee)."""
    a, b = pal["a"], pal["b"]
    cx, y0, y1, demi, cou = 0.5, 0.32, 0.86, 0.18, 0.028
    pic = _verre_et_sable(ctx, pal, cx, y0, y1, demi, cou, 0.05 * gras, fermer=False)
    trait(ctx, a, 0.07 * gras, [(0.27, y1 + 0.03), (0.73, y1 + 0.03)])
    trait(ctx, b, 0.035 * gras, [(cx, pic + 0.02), (cx, 0.27)])
    _miroir(ctx, lambda: _feuille(ctx, b, (cx, 0.29), (0.24, 0.07), 0.085 * gras))


# --- Quatrieme tour : le sablier ouvert, avec de l'argent ----------------------------------
# Alexandre retient le sablier ouvert (L) et veut qu'on identifie le sujet :
# l'argent. Des pieces, jamais de symbole monetaire.

def _piece(ctx, couleur, cx, cy, r):
    """Piece vue de face : un listel et un disque central, separes par un vide."""
    ctx.set_source_rgb(*rgb(couleur))
    ctx.new_path()
    ctx.arc(cx, cy, r, 0, 2 * math.pi)
    ctx.new_sub_path()
    ctx.arc_negative(cx, cy, r * 0.84, 2 * math.pi, 0)
    ctx.fill()
    ctx.new_path()
    ctx.arc(cx, cy, r * 0.68, 0, 2 * math.pi)
    ctx.fill()


def _pile(ctx, couleur, cx, pieces, ep=0.048):
    """Pile de pieces vues de profil : (centre y, largeur, decalage x)."""
    for yc, larg, dx in pieces:
        trait(ctx, couleur, ep, [(cx + dx - larg / 2 + ep / 2, yc), (cx + dx + larg / 2 - ep / 2, yc)])


def piste_m(ctx, pal):
    """Le sable en pieces : au fond du bulbe, un tas de pieces vues de face."""
    a, b = pal["a"], pal["b"]
    cx, y0, y1, demi, cou = 0.5, 0.30, 0.86, 0.21, 0.028
    _sablier(ctx, cx, y0, y1, demi, cou, fermer=False)
    ctx.set_source_rgb(*rgb(a))
    ctx.set_line_width(0.05)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.stroke()
    r = 0.072
    for x, y in ((cx - 0.08, 0.775), (cx + 0.08, 0.775), (cx, 0.705)):
        _piece(ctx, b, x, y, r)
    trait(ctx, a, 0.07, [(0.25, y1 + 0.03), (0.75, y1 + 0.03)])
    trait(ctx, b, 0.035, [(cx, 0.63), (cx, 0.27)])
    _miroir(ctx, lambda: _feuille(ctx, b, (cx, 0.29), (0.24, 0.07), 0.085))


def piste_n(ctx, pal):
    """La piece en bouton : entre les deux feuilles, la tige porte une piece."""
    a, b = pal["a"], pal["b"]
    cx, y0, y1, demi, cou = 0.5, 0.36, 0.88, 0.18, 0.028
    pic = _verre_et_sable(ctx, pal, cx, y0, y1, demi, cou, 0.05, fermer=False)
    trait(ctx, a, 0.07, [(0.27, y1 + 0.03), (0.73, y1 + 0.03)])
    trait(ctx, b, 0.035, [(cx, pic + 0.02), (cx, 0.24)])
    _miroir(ctx, lambda: _feuille(ctx, b, (cx, 0.34), (0.17, 0.21), 0.075))
    _piece(ctx, b, cx, 0.165, 0.125)


def piste_o(ctx, pal):
    """Le socle de pieces : le sablier ouvert est pose sur une pile de pieces."""
    a, b = pal["a"], pal["b"]
    cx, y0, y1, demi, cou = 0.5, 0.28, 0.73, 0.16, 0.026
    pic = _verre_et_sable(ctx, pal, cx, y0, y1, demi, cou, 0.048, fermer=False)
    trait(ctx, b, 0.032, [(cx, pic + 0.02), (cx, 0.24)])
    _miroir(ctx, lambda: _feuille(ctx, b, (cx, 0.26), (0.27, 0.07), 0.075))
    trait(ctx, a, 0.05, [(0.30, 0.765), (0.70, 0.765)])
    _pile(ctx, b, cx, [(0.835, 0.36, 0.035), (0.905, 0.36, -0.03)], ep=0.052)


def _piece_frappee(ctx, pal, piece, gravure, gras=1.0, listel=0.028, cercle=None):
    """Le sablier ouvert grave sur une piece de couleur piece, trait gravure.

    cercle : couleur du listel (par defaut celle de la gravure).
    En monochrome (fond transparent), la piece devient un contour."""
    if pal["fond"] is None:
        gravure = cercle = pal["a"]
        ctx.set_source_rgb(*rgb(gravure))
        ctx.set_line_width(0.035)
        ctx.new_path()
        ctx.arc(0.5, 0.5, 0.465, 0, 2 * math.pi)
        ctx.stroke()
    else:
        ctx.set_source_rgb(*rgb(piece))
        ctx.new_path()
        ctx.arc(0.5, 0.5, 0.48, 0, 2 * math.pi)
        ctx.fill()
    ctx.set_source_rgb(*rgb(cercle or gravure))
    ctx.set_line_width(listel)
    ctx.new_path()
    ctx.arc(0.5, 0.5, 0.41, 0, 2 * math.pi)
    ctx.stroke()
    ctx.save()
    ctx.translate(0.5, 0.5)
    ctx.scale(0.66, 0.66)
    ctx.translate(-0.5, -0.5)
    piste_l(ctx, {"a": gravure, "b": gravure, "fond": None}, gras)
    ctx.restore()


def piste_p(ctx, pal):
    """La piece frappee : gravure encre sur piece ambre."""
    _piece_frappee(ctx, pal, style.INTEREST, style.BG)


# --- Cinquieme tour : la piece frappee en bleu ---------------------------------------------
# Alexandre veut du bleu a la place de l'encre. Le bleu et l'ambre de la charte
# ont presque la meme clarte (contraste 1,74:1, contre 10:1 pour l'encre) :
# d'ou une variante a traits renforces et une piece bleue a gravure ambre.

def piste_q(ctx, pal):
    _piece_frappee(ctx, pal, style.INTEREST, style.CONTRIB)


def piste_r(ctx, pal):
    _piece_frappee(ctx, pal, style.INTEREST, style.CONTRIB, gras=1.35, listel=0.04)


def piste_s(ctx, pal):
    _piece_frappee(ctx, pal, style.CONTRIB, style.INTEREST, gras=1.35, listel=0.04)


# Sixieme tour : Q et S avec le cercle en encre, comme sur P (essai demande
# par Alexandre). L'encre s'ajoute au bleu et a l'ambre : trois couleurs.

def piste_q2(ctx, pal):
    _piece_frappee(ctx, pal, style.INTEREST, style.CONTRIB, cercle=style.BG)


def piste_s2(ctx, pal):
    _piece_frappee(ctx, pal, style.CONTRIB, style.INTEREST, gras=1.35, listel=0.04,
                   cercle=style.BG)


# Premier tour (27/10/2026), ecarte : trop abstrait.
PISTES_1 = {
    "A": ("Le croisement", piste_a,
          "Le moment exact où le capital (ambre) dépasse l'effort (bleu) : la promesse de la chaîne en un seul geste."),
    "B": ("Le monogramme", piste_b,
          "Les initiales CNE construites au trait, comme un sceau : une marque d'éditeur sobre et durable."),
    "C": ("La lentille", piste_c,
          "Une lentille qui rend net : l'effort entre à plat, le résultat passe par le foyer et monte."),
    "D": ("c puissance n", piste_d,
          "La capitalisation écrite comme en maths : c pour Clair net, l'exposant pour l'enrichissement."),
}

PISTES_2 = {
    "E": ("Le sablier", piste_e,
          "Le temps fait le travail : c'est la matière première des intérêts composés, et le fil de la chaîne."),
    "F": ("Le phare", piste_f,
          "Un repère dans le brouillard financier : la chaîne éclaire les décisions, elle ne vend rien."),
    "G": ("La loupe", piste_g,
          "On regarde les chiffres de près : sous la lentille, la courbe des intérêts composés."),
    "H": ("La pousse", piste_h,
          "Ce qu'on plante finit par pousser : la tige (l'effort) porte les feuilles (le résultat)."),
}

PISTES_3 = {
    "I": ("Le sablier en fleur", piste_i,
          "Le temps placé finit par fleurir : le haut du sablier s'ouvre en feuilles, plus de compte à rebours."),
    "J": ("L'envol", piste_j,
          "Une graine qui prend son envol, ses feuilles sont des ailes : ne plus dépendre, c'est être libre."),
    "K": ("La clé du temps", piste_k,
          "Un sablier pour anneau, des feuilles pour dents : avec le temps, on déverrouille sa liberté."),
    "L": ("Le sablier ouvert", piste_l,
          "Le sablier n'a plus de couvercle et la pousse en sort : le temps cesse d'être une contrainte."),
}

PISTES_4 = {
    "M": ("Le sable en pièces", piste_m,
          "Le sable écoulé, ce sont des pièces mises de côté : la pousse naît de l'épargne et sort du sablier."),
    "N": ("La pièce en bouton", piste_n,
          "Au bout de la tige, entre les feuilles, le fruit du temps : une pièce."),
    "O": ("Le socle de pièces", piste_o,
          "Le sablier ouvert repose sur une pile de pièces : le temps s'appuie sur l'épargne."),
    "P": ("La pièce frappée", piste_p,
          "Le sablier ouvert gravé sur une pièce : l'avatar lui-même devient une pièce de monnaie."),
}

PISTES_5 = {
    "P": ("Gravure encre (rappel)", piste_p,
          "La pièce frappée du tour 4, pour comparer. Contraste encre sur ambre : 10:1."),
    "Q": ("Gravure bleue", piste_q,
          "La demande telle quelle : le sablier gravé en bleu. Contraste bleu sur ambre : 1,74:1."),
    "R": ("Gravure bleue renforcée", piste_r,
          "Même bleu, traits et feuilles plus épais d'un tiers pour compenser le faible contraste."),
    "S": ("Pièce bleue", piste_s,
          "L'inverse : une pièce bleue, le sablier gravé en ambre, traits renforcés."),
}

PISTES_6 = {
    "Q": PISTES_5["Q"],
    "Q2": ("Q, cercle encre", piste_q2,
           "Le sablier reste bleu ; seul le cercle de la pièce passe en encre, comme sur P."),
    "S": PISTES_5["S"],
    "S2": ("S, cercle encre", piste_s2,
           "Le sablier reste ambre ; seul le cercle de la pièce passe en encre, comme sur P."),
}

TOUTES = {**PISTES_1, **PISTES_2, **PISTES_3, **PISTES_4, **PISTES_5, **PISTES_6}
TOURS = {1: PISTES_1, 2: PISTES_2, 3: PISTES_3, 4: PISTES_4, 5: PISTES_5, 6: PISTES_6}

# Pastille ambre : le symbole en encre sur un disque ambre. Deux couleurs de
# la charte, et la seule version qui ressort dans le mode sombre de YouTube.
AMBRE = {"a": style.BG, "b": style.BG, "fond": style.INTEREST}


# --- Rendu ------------------------------------------------------------------------------

def dessine(ctx, cle, pal, taille, fond_rond=False):
    """Dessine la piste cle sur un carre de cote taille (unites du contexte)."""
    ctx.save()
    ctx.scale(taille, taille)
    if pal["fond"]:
        ctx.set_source_rgb(*rgb(pal["fond"]))
        if fond_rond:
            ctx.arc(0.5, 0.5, 0.5, 0, 2 * math.pi)
        else:
            ctx.rectangle(0, 0, 1, 1)
        ctx.fill()
    TOUTES[cle][1](ctx, pal)
    ctx.restore()


def svg(cle, pal, chemin, taille=512):
    surf = cairo.SVGSurface(str(chemin), taille, taille)
    surf.set_document_unit(cairo.SVGUnit.PX)
    dessine(cairo.Context(surf), cle, pal, taille)
    surf.finish()


def png(cle, pal, taille, fond_rond=False):
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, taille, taille)
    dessine(cairo.Context(surf), cle, pal, taille, fond_rond)
    return surf


# --- Planche d'exploration ----------------------------------------------------------------

YT_SOMBRE, YT_CLAIR = "#0F0F0F", "#FFFFFF"   # fonds des commentaires YouTube


def _lib(ctx, s, x, y, corps, couleur, graisse=cairo.FONT_WEIGHT_NORMAL):
    ctx.select_font_face("Segoe UI", cairo.FONT_SLANT_NORMAL, graisse)
    ctx.set_font_size(corps)
    ctx.set_source_rgb(*rgb(couleur))
    ctx.move_to(x, y)
    ctx.show_text(s)


def _lignes(ctx, s, x, y, corps, couleur, largeur, interligne=1.35):
    ctx.select_font_face("Segoe UI", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
    ctx.set_font_size(corps)
    mots, ligne = s.split(), ""
    for m in mots:
        essai = (ligne + " " + m).strip()
        if ctx.text_extents(essai).x_advance > largeur and ligne:
            _lib(ctx, ligne, x, y, corps, couleur)
            y += corps * interligne
            ligne = m
        else:
            ligne = essai
    _lib(ctx, ligne, x, y, corps, couleur)
    return y


def _pose(ctx, surf, x, y):
    ctx.set_source_surface(surf, x, y)
    ctx.paint()


def _gris(surf):
    """Copie desaturee : ce que voit un ecran en niveaux de gris."""
    g = cairo.ImageSurface(cairo.FORMAT_ARGB32, surf.get_width(), surf.get_height())
    c = cairo.Context(g)
    c.set_source_surface(surf)
    c.paint()
    c.set_operator(cairo.OPERATOR_HSL_SATURATION)
    c.set_source_rgb(0.5, 0.5, 0.5)
    c.mask_surface(surf)
    return g


def _case(ctx, fond, x, y, cote):
    ctx.set_source_rgb(*rgb(fond))
    ctx.rectangle(x, y, cote, cote)
    ctx.fill()


def exploration(tour=2):
    pistes = TOURS[tour]
    pieces = tour >= 5                 # la piece frappee porte ses propres couleurs
    dossier = SORTIE / "exploration" / f"tour{tour}"
    dossier.mkdir(parents=True, exist_ok=True)
    for cle in pistes:
        svg(cle, COULEUR, dossier / f"piste_{cle}.svg")
        svg(cle, BLANC, dossier / f"piste_{cle}_blanc.svg")
        png(cle, COULEUR, 512).write_to_png(str(dossier / f"piste_{cle}_512.png"))
        png(cle, COULEUR, 48, fond_rond=True).write_to_png(str(dossier / f"piste_{cle}_48.png"))
        png(cle, AMBRE, 48, fond_rond=True).write_to_png(str(dossier / f"piste_{cle}_48_ambre.png"))

    col, marge = 300, 40
    W, H = marge * 2 + col * 4, 1000
    surf = cairo.ImageSurface(cairo.FORMAT_RGB24, W, H)
    ctx = cairo.Context(surf)
    ctx.set_source_rgb(*rgb("#1E242D"))
    ctx.paint()
    _lib(ctx, f"Clair net enrichi : pistes de logo, tour {tour}", marge, 46, 26,
         style.INK, cairo.FONT_WEIGHT_BOLD)
    _lib(ctx, "Pixels réels : afficher à 100 % pour juger le 48 px.", marge, 76, 15, style.MUTED)

    for i, (cle, (nom, _, intention)) in enumerate(pistes.items()):
        x, y = marge + i * col, 120
        _lib(ctx, f"{cle}. {nom}", x, y, 20, style.INK, cairo.FONT_WEIGHT_BOLD)
        _lignes(ctx, intention, x, y + 26, 13, style.INK_SOFT, col - 30)
        y = 215
        _pose(ctx, png(cle, COULEUR, 256), x, y)
        y += 256 + 30
        if pieces:
            # la piece porte ses propres couleurs : la pastille ambre ne
            # s'applique plus ; on montre a la place le rendu en gris
            _lib(ctx, "YouTube clair · niveaux de gris, 128 px", x, y, 12, style.MUTED)
            y += 12
            _case(ctx, YT_CLAIR, x, y, 128)
            _pose(ctx, png(cle, COULEUR, 112, fond_rond=True), x + 8, y + 8)
            _case(ctx, YT_SOMBRE, x + 136, y, 128)
            _pose(ctx, _gris(png(cle, COULEUR, 112, fond_rond=True)), x + 144, y + 8)
            cases = [(YT_SOMBRE, COULEUR, False), (YT_CLAIR, COULEUR, False),
                     (YT_SOMBRE, COULEUR, True), (YT_CLAIR, NOIR, False)]
            legende = "sombre · clair · gris · noir"
        else:
            _lib(ctx, "Pastille ambre · noir et blanc, 128 px", x, y, 12, style.MUTED)
            y += 12
            _case(ctx, YT_SOMBRE, x, y, 128)
            _pose(ctx, png(cle, AMBRE, 112, fond_rond=True), x + 8, y + 8)
            _case(ctx, "#FFFFFF", x + 136, y, 128)
            _pose(ctx, png(cle, NOIR, 128), x + 136, y)
            cases = [(YT_SOMBRE, COULEUR, False), (YT_SOMBRE, AMBRE, False),
                     (YT_CLAIR, COULEUR, False), (YT_CLAIR, AMBRE, False)]
            legende = "YouTube sombre ×2 · YouTube clair ×2"
        y += 128 + 30
        _lib(ctx, "48 px, avatar rond", x, y, 12, style.MUTED)
        y += 12
        for j, (fond, pal, gris) in enumerate(cases):
            bx = x + j * 64
            _case(ctx, fond, bx, y, 60)
            s = png(cle, pal, 48, fond_rond=pal is not NOIR)
            _pose(ctx, _gris(s) if gris else s, bx + 6, y + 6)
        y += 60 + 16
        _lib(ctx, legende, x, y, 11, style.MUTED)
        y += 30
        _lib(ctx, "16 px (onglet, favicon)", x, y, 12, style.MUTED)
        y += 10
        _pose(ctx, png(cle, COULEUR, 16, fond_rond=True), x, y)
        if pieces:
            _pose(ctx, _gris(png(cle, COULEUR, 16, fond_rond=True)), x + 24, y)
        else:
            _pose(ctx, png(cle, AMBRE, 16, fond_rond=True), x + 24, y)
        _case(ctx, "#FFFFFF", x + 48, y, 16)
        _pose(ctx, png(cle, NOIR, 16), x + 48, y)

    planche = dossier / "planche_pistes.png"
    surf.write_to_png(str(planche))
    return planche


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "exploration"
    if action == "exploration":
        print(exploration(int(sys.argv[2]) if len(sys.argv) > 2 else 2))
