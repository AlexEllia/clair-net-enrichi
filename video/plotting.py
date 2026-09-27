# -*- coding: utf-8 -*-
"""Cadre de trace et calculs financiers partages par les scenes."""

from manim import *
import numpy as np
from style import *


# --- Cadre de trace ----------------------------------------------------------

class Frame:
    """Projection donnees -> coordonnees de scene.

    On dessine les graphes a la main plutot qu'avec les Axes de Manim :
    la charte impose des filets tres discrets et des libelles hors cadre,
    ce que le style par defaut ne donne pas.
    """

    def __init__(self, x0, x1, y0, y1, w=PLOT_W, h=PLOT_H, center=None):
        self.x0, self.x1, self.y0, self.y1 = float(x0), float(x1), float(y0), float(y1)
        self.w, self.h = w, h
        self.c = np.array(PLOT_C if center is None else center, dtype=float)

    def px(self, x):
        f = (x - self.x0) / (self.x1 - self.x0) if self.x1 != self.x0 else 0.0
        return self.c[0] - self.w / 2 + f * self.w

    def py(self, y):
        f = (y - self.y0) / (self.y1 - self.y0) if self.y1 != self.y0 else 0.0
        return self.c[1] - self.h / 2 + f * self.h

    def pt(self, x, y):
        return np.array([self.px(x), self.py(y), 0.0])

    def wx(self, dx):
        return dx / (self.x1 - self.x0) * self.w

    def wy(self, dy):
        return dy / (self.y1 - self.y0) * self.h

    # -- habillage ------------------------------------------------------------

    def baseline(self):
        return Line(self.pt(self.x0, self.y0), self.pt(self.x1, self.y0),
                    stroke_color=RULE, stroke_width=2.4)

    def gridlines(self, values, fmt=None, side=LEFT):
        """Filets horizontaux + libelles de valeur, en gris tres retenu."""
        g = VGroup()
        for v in values:
            ln = Line(self.pt(self.x0, v), self.pt(self.x1, v),
                      stroke_color=RULE_SOFT, stroke_width=1.6)
            g.add(ln)
            if fmt:
                lab = txt(fmt(v), SZ_SOURCE, MUTED)
                lab.next_to(ln, side, buff=0.22)
                g.add(lab)
        return g

    def xticks(self, values, fmt=str, buff=0.24):
        g = VGroup()
        for v in values:
            lab = txt(fmt(v), SZ_SOURCE, MUTED)
            lab.move_to(self.pt(v, self.y0)).shift(DOWN * (buff + lab.height / 2))
            g.add(lab)
        return g

    def xlabel(self, s):
        t = txt(s, SZ_SOURCE, MUTED)
        t.move_to([self.c[0], self.py(self.y0) - 0.75, 0])
        return t


# --- Calculs -----------------------------------------------------------------

def epargne_mensuelle(monthly=200.0, rate=0.05, years=45):
    """Versement mensuel a taux constant, interets capitalises mensuellement.

    Renvoie une liste de dicts par annee : versements de l'annee, interets
    credites dans l'annee, capital de fin d'annee, cumuls.
    Ce sont les hypotheses affichees a l'ecran comme telles ('Simulation').
    """
    out = []
    bal = 0.0
    cum_contrib = 0.0
    r = rate / 12.0
    for y in range(1, years + 1):
        interest_y = 0.0
        for _ in range(12):
            i = bal * r
            bal += i + monthly
            interest_y += i
        cum_contrib += monthly * 12
        out.append({
            "year": y,
            "contrib_year": monthly * 12,
            "interest_year": interest_y,
            "balance": bal,
            "cum_contrib": cum_contrib,
            "cum_interest": bal - cum_contrib,
        })
    return out


def crossover_year(series):
    """Premiere annee ou les interets de l'annee depassent les versements."""
    for row in series:
        if row["interest_year"] > row["contrib_year"]:
            return row["year"]
    return None


def compound_index(cagr_pct, years, base=100.0):
    """Indice base 100 a taux annuel constant."""
    r = cagr_pct / 100.0
    return [base * (1 + r) ** k for k in range(years + 1)]


def nice_ceiling(v):
    """Plafond d'axe lisible (1-2-5 x 10^n) juste au-dessus de v."""
    if v <= 0:
        return 1.0
    mag = 10 ** np.floor(np.log10(v))
    for m in (1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10):
        if m * mag >= v:
            return m * mag
    return 10 * mag


# --- Calage sur les chiffres du script ---------------------------------------
# Le modele ci-dessus donne la *forme*. Les valeurs affichees a l'ecran, elles,
# doivent etre celles du script, qui sont sourcees et validees en phase 3.
# On recale donc la courbe pour qu'elle passe exactement par les points du
# `manim_brief`. L'ecart est de l'ordre de 5 % : la silhouette ne bouge pas,
# mais un spectateur qui lit un chiffre a l'ecran entend le meme a la voix.

def calibrate(series, key, anchors):
    """Rescale `key` par un facteur log-lineaire passant par `anchors` {annee: valeur}."""
    ys = sorted(anchors)
    facts = {y: anchors[y] / series[y - 1][key] for y in ys}
    for row in series:
        y = row["year"]
        if y <= ys[0]:
            f = facts[ys[0]]
        elif y >= ys[-1]:
            f = facts[ys[-1]]
        else:
            hi = next(k for k in ys if k >= y)
            lo = max(k for k in ys if k <= y)
            if hi == lo:
                f = facts[lo]
            else:
                a = (y - lo) / (hi - lo)
                f = np.exp((1 - a) * np.log(facts[lo]) + a * np.log(facts[hi]))
        row[key] = row[key] * f
    return series


def monotone_curve(anchors, xs):
    """Interpolation monotone (Fritsch-Carlson) - pour lisser une part en %."""
    kx = np.array(sorted(anchors), dtype=float)
    ky = np.array([anchors[k] for k in sorted(anchors)], dtype=float)
    h = np.diff(kx)
    d = np.diff(ky) / h
    m = np.zeros_like(kx)
    m[0], m[-1] = d[0], d[-1]
    for i in range(1, len(kx) - 1):
        if d[i - 1] * d[i] <= 0:
            m[i] = 0.0
        else:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])
    out = []
    for x in xs:
        j = int(np.clip(np.searchsorted(kx, x) - 1, 0, len(kx) - 2))
        t = (x - kx[j]) / h[j]
        h00 = 2 * t ** 3 - 3 * t ** 2 + 1
        h10 = t ** 3 - 2 * t ** 2 + t
        h01 = -2 * t ** 3 + 3 * t ** 2
        h11 = t ** 3 - t ** 2
        out.append(h00 * ky[j] + h10 * h[j] * m[j] + h01 * ky[j + 1] + h11 * h[j] * m[j + 1])
    return np.array(out)
