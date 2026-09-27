# -*- coding: utf-8 -*-
"""Identite visuelle - Clair net enrichi.

Un seul endroit pour la palette, la typographie et la geometrie de cadre.
Toutes les scenes s'y referent : c'est ce qui fait tenir la charte d'un
episode a l'autre.
"""

from manim import *

# --- Palette -----------------------------------------------------------------
# Fond encre profonde, texte creme, deux series opposees en bleu ardoise et
# ambre. Le couple bleu/ambre reste lisible en deuteranopie et protanopie ;
# c'est pour cela qu'il porte l'opposition centrale de la chaine
# (ce que vous versez / ce que le capital verse).

BG          = "#0F1319"   # encre
BG_LIFT     = "#161C25"   # vignette haute
INK         = "#F4F6F8"   # texte principal
INK_SOFT    = "#C8D0DA"   # texte secondaire
MUTED       = "#7F8A9C"   # sources, mentions
RULE        = "#232C38"   # grilles, filets
RULE_SOFT   = "#1A222C"

CONTRIB     = "#5B8DEF"   # ce que vous versez
INTEREST    = "#F2B33D"   # ce que le capital vous verse
TEAL        = "#3FC0A5"   # troisieme serie
NEG         = "#E2725B"   # negatif, perte
WHITE_DIM   = "#9AA5B4"

# --- Typographie -------------------------------------------------------------
FONT       = "Segoe UI"
FONT_MONO  = "Consolas"

SZ_TITLE   = 46
SZ_BIG     = 92
SZ_HUGE    = 132
SZ_BODY    = 34
SZ_LABEL   = 28
SZ_SOURCE  = 24

# --- Geometrie ---------------------------------------------------------------
# Cadre Manim : 14.222 x 8.0 unites pour du 16/9.
FW, FH = 14.222, 8.0

Y_TOP      = 3.05    # ancre "titre_haut"
Y_BOTTOM   = -3.30   # ancre "bas"
X_LEFT     = -6.30   # marge de securite gauche
X_RIGHT    = 6.30

PLOT_W     = 10.2    # aire de trace
PLOT_H     = 4.5
PLOT_C     = np.array([0.0, -0.35, 0.0])   # centre de l'aire de trace


def txt(s, size=SZ_BODY, color=INK, weight=NORMAL, font=FONT):
    return Text(s, font=font, font_size=size, color=color, weight=weight)


def title_top(s):
    """Titre d'ancrage haut : discret, jamais concurrent du graphe."""
    t = txt(s, SZ_TITLE, INK, weight=SEMIBOLD)
    t.move_to([0, Y_TOP, 0])
    return t


def source_line(s):
    """Ligne de source en pied d'image. Petite, grise, jamais centree fort."""
    t = txt(s, SZ_SOURCE, MUTED)
    t.move_to([0, Y_BOTTOM - 0.30, 0])
    if t.width > FW - 1.6:
        t.scale_to_fit_width(FW - 1.6)
    return t


def legend_chip(s, color, size=SZ_LABEL):
    """Pastille de legende : carre de couleur + libelle."""
    dot = RoundedRectangle(width=0.26, height=0.26, corner_radius=0.06,
                           fill_color=color, fill_opacity=1, stroke_width=0)
    lab = txt(s, size, INK_SOFT)
    g = VGroup(dot, lab).arrange(RIGHT, buff=0.22)
    return g


def backdrop():
    """Fond + vignette haute tres douce. Pose une fois par scene."""
    base = Rectangle(width=FW + 0.2, height=FH + 0.2,
                     fill_color=BG, fill_opacity=1, stroke_width=0)
    glow = Rectangle(width=FW + 0.2, height=FH + 0.2, stroke_width=0)
    glow.set_fill(color=[BG_LIFT, BG, BG], opacity=0.85)
    glow.set_sheen_direction(UP)
    return VGroup(base, glow)


def fade_up(m, shift=0.28):
    """Entree maison : le texte monte de quelques pixels en apparaissant."""
    return FadeIn(m, shift=UP * shift)


def euro(v, decimals=0):
    """Montant en euros, dans la langue du rendu (voir nombres.py)."""
    import nombres
    return nombres.euro(v, decimals)


def pct(v, decimals=1):
    import nombres
    return nombres.pct(v, decimals)
