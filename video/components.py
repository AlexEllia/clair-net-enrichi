# -*- coding: utf-8 -*-
"""Composants graphiques - un par valeur de `manim_brief.composant`.

Chaque fonction recoit le segment et un objet `Cues`, y depose ses mobjects
statiques et ses animations horodatees. Elle ne joue rien elle-meme : la scene
fusionne ensuite ces reperes avec ceux des overlays.

Un composant ne se pose pas d'un bloc. Il declare ses parties dans l'ordre ou
elles entrent - une annee, une courbe, une aire, un jalon - et les confie a un
`Reveal`, qui donne a chacune son top de depart. La cadence par defaut est
celle du composant ; le script la remplace plan par plan avec
`manim_brief.reveals`. Les noms de parties sont listes dans LISEZ-MOI.md.

Regle de fond : les valeurs ecrites a l'ecran sont celles du `manim_brief`,
qui sont sourcees. Le modele d'epargne ne sert qu'a dessiner la silhouette
entre ces points.
"""

import sys

from manim import *
import numpy as np

from style import (BG, INK, INK_SOFT, MUTED, RULE, RULE_SOFT, CONTRIB, INTEREST,
                   TEAL, NEG, WHITE_DIM, PLOT_W, PLOT_H, Y_TOP,
                   SZ_TITLE, SZ_BODY, SZ_LABEL, SZ_SOURCE,
                   txt, fade_up, euro, pct)
from plotting import (Frame, epargne_mensuelle, calibrate, compound_index,
                      monotone_curve, nice_ceiling)


class Cues:
    """Liste d'animations horodatees, en secondes depuis le debut du segment."""

    def __init__(self, dur):
        self.dur = dur
        self.static = []
        self.items = []
        self.legend_colors = []   # couleurs reprises par les overlays 'legende'
        self.anchors = set()      # ancres d'overlay presentes, pour laisser la place
        # Points d'ancrage nommes exportes par le composant, en unites Manim :
        # {nom: (x, y, rotation_deg)}. Ecrits dans Sxx.anchors.json au rendu,
        # et lus par les overlays 'axe_x' / 'axe_y'.
        self.points = {"titre_haut": (0.0, Y_TOP, 0)}
        # Mesures pour make check : fin de construction du cadre, debut de la
        # premiere animation de donnee.
        self.meta = {}

    def add(self, *m):
        self.static.extend(m)
        return m[0] if len(m) == 1 else m

    def at(self, t, *anims, rt=0.8):
        if anims:
            self.items.append((float(t), list(anims), float(rt)))

    def late(self, t, margin=1.2):
        """Borne un top de depart pour qu'il tienne dans la duree du segment."""
        return min(float(t), max(0.0, self.dur - margin))

    def point(self, name, xy, rot=0):
        self.points[name] = (float(xy[0]), float(xy[1]), rot)

    def frame_anchors(self, fr, below=0.75, left=0.55):
        """Ancres d'axes d'un cadre de trace.

        `axe_x` : centre sous l'axe horizontal. `axe_y` : a gauche de l'axe
        vertical, texte pivote de 90 degres. `below` laisse la place des
        graduations quand le composant en ecrit."""
        self.point("axe_x", (fr.c[0], fr.py(fr.y0) - below))
        self.point("axe_y", (fr.px(fr.x0) - left, fr.c[1]), rot=90)


# --- Apparitions echelonnees -------------------------------------------------
# Un plan entre par etapes, et c'est le script qui en decide. Quatre ecritures,
# toutes facultatives, dans `manim_brief.reveals` :
#
#   "reveals": [1.6, 8.0, 13.0]                          des tops, dans l'ordre
#   "reveals": [{"target": "gross_return", "at": 8.0}]   une partie nommee
#   "reveals": {"start": 1.4, "step": 2.2}               une cadence reglee
#   "reveals": "together"                                tout au meme top
#
# Sans cette cle, chaque composant garde sa cadence propre : les briefs deja
# ecrits se rendent a l'identique.

_TOGETHER = ("together", "ensemble")
MIN_RT = 0.3            # plancher d'une apparition calee par le script
CONTINUOUS_MAX = 6.0    # plafond de ce qui se trace : courbe, aire, bande, barre qui monte
PUNCTUAL_MAX = 1.5      # plafond de ce qui surgit : repere, accolade, annotation, ligne de reference
LABEL_RT = 0.3          # une etiquette chiffree : apparition ponctuelle
FRAME_MAX = 4.0         # le cadre se construit en 4 s au plus
FRAME_MIN = 1.0         # ... et cede jusqu'a 1 s devant le premier trace (regle v2)
FRAME_RULE = "v2"       # "v1" : le cadre d'abord (23/09/2026), archivee ; voir _frame_end
MIN_LEAD = 0.5          # temps minimal d'un trace pour rejoindre son premier point
GAP = 0.2               # respiration entre deux animations successives


def _reveal_spec(seg):
    return ((seg or {}).get("manim_brief") or {}).get("reveals")


def reveal_count(seg, default):
    """Combien d'apparitions le script demande, sinon `default`.

    Pour les composants qui posent une masse d'objets d'un seul geste : le
    script dit en combien de fois elle se pose, le composant la decoupe.
    """
    spec = _reveal_spec(seg)
    return len(spec) if isinstance(spec, list) and spec else int(default)


class Reveal:
    """Calendrier d'apparitions : une partie, un top de depart.

    `keys` porte la cadence, dans l'ordre d'entree a l'ecran. `extras` liste
    les parties derivees - un repere qui suit sa courbe, une accolade qui suit
    ses barres : le composant leur donne leur top avec `default()`, calcule sur
    les tops reellement retenus, de sorte qu'un decalage demande par le script
    les emmene avec lui. Le script peut fixer les unes comme les autres en les
    nommant.
    """

    def __init__(self, seg, cues, keys, extras=(), t0=1.6, step=None,
                 span=None, rt=0.6, margin=1.2):
        self.cues = cues
        self.seg_id = (seg or {}).get("id", "?")
        self.caps = {}            # plafond de run_time par partie (revelations)
        self._warned = set()
        self.order = [str(k) for k in keys] + [str(k) for k in extras]
        self.rt = float(rt)
        self.margin = float(margin)
        self.times = {}
        self.rts = {}
        self.fixed = set()

        spec = _reveal_spec(seg)
        self.together = (spec in _TOGETHER or
                         (isinstance(spec, dict) and spec.get("mode") in _TOGETHER))
        if isinstance(spec, dict):
            t0 = float(spec.get("start", t0))
            step = spec.get("step", step)
            span = spec.get("span", span)

        keys = [str(k) for k in keys]
        if step is None:
            budget = span if span is not None else max(cues.dur - t0 - self.margin, 0.6)
            step = float(budget) / max(len(keys) - 1, 1)
        self.t0, self.step = float(t0), float(step)
        for i, k in enumerate(keys):
            self.times[k] = self.t0 + (0.0 if self.together else i * self.step)

        if isinstance(spec, list):
            self._apply(spec)

    # -- ce que le script demande ---------------------------------------------

    def _apply(self, spec):
        """Applique la liste du script : entrees nommees, sinon positionnelles."""
        pos = 0
        for entry in spec:
            key, t, rt, cap = None, None, None, None
            if isinstance(entry, dict):
                key = entry.get("target")
                t = entry.get("at", entry.get("start"))
                rt = entry.get("run_time")
                if entry.get("max_rt") is not None:
                    cap = float(entry["max_rt"])
            elif isinstance(entry, (int, float)):
                t = entry
            else:
                continue
            if key is None:
                while pos < len(self.order) and self.order[pos] in self.fixed:
                    pos += 1
                if pos >= len(self.order):
                    break
                key = self.order[pos]
            elif key not in self.order:
                print(f"[REVEALS] partie inconnue : {key!r}", file=sys.stderr)
                continue
            pos = self.order.index(key) + 1
            if t is not None:
                self.times[key] = float(t)
                self.fixed.add(key)
            if rt is not None:
                self.rts[key] = float(rt)
            if cap is not None:
                self.caps[key] = cap
        if self.fixed and not self.together:
            self._reflow(max(self.fixed, key=self.order.index))

    def _reflow(self, key):
        """Les parties suivantes reprennent la cadence a partir de `key` : un
        top repousse ne laisse pas les autres derriere lui."""
        base = self.times[key]
        for i, k in enumerate(self.order[self.order.index(key) + 1:], start=1):
            if k not in self.fixed and k in self.times:
                self.times[k] = base + i * self.step

    # -- ce que le composant pose ---------------------------------------------

    def default(self, key, t, reflow=False):
        """Top d'une partie derivee. Sans effet si le script l'a fixee."""
        if key not in self.fixed:
            self.times[key] = float(t)
            if reflow:
                self._reflow(key)
        return self.times[key]

    def run_time(self, key, default):
        """Duree effective d'une partie : son defaut, borne par la revelation
        suivante si le script l'a calee."""
        rt = self.rts.get(key, float(default))
        if key in self.caps:
            rt = max(min(rt, self.caps[key]), MIN_RT)
        return rt

    def t(self, key, delay=0.0):
        return self.times[key] + float(delay)

    def at(self, key, *anims, rt=None, delay=0.0, margin=None, drop=False):
        """Depose une apparition au top prevu pour `key`.

        `drop` abandonne la partie qui ne tient plus dans le plan au lieu de la
        tasser contre la fin : un jalon de frise n'a pas de sens s'il arrive
        apres la voix. Renvoie alors False, pour que ce qui en depend - un
        libelle, par exemple - soit abandonne avec elle.
        """
        if key not in self.times:
            raise KeyError(f"partie sans top : {key!r}")
        m = self.margin if margin is None else float(margin)
        t = self.times[key] + float(delay)
        rt = self.rts.get(key, self.rt if rt is None else float(rt))

        if key in self.caps:
            # Top impose par une revelation du script : il part a l'heure dite,
            # jamais avance, et finit avant la revelation suivante.
            rt = min(rt, self.caps[key] - float(delay))
            if rt < MIN_RT:
                if key not in self._warned:
                    self._warned.add(key)
                    print(f"[ATTENTION] {self.seg_id} : '{key}' n'a que "
                          f"{self.caps[key] - float(delay):.2f} s avant la revelation "
                          f"suivante ; run_time porte a {MIN_RT} s. Le script enchaine "
                          f"trop vite : c'est lui qu'il faut corriger.",
                          file=sys.stderr, flush=True)
                rt = MIN_RT
            if drop and t >= self.cues.dur:
                return False
            self.cues.at(t, *anims, rt=rt)
            return True

        if drop and t > self.cues.dur - m:
            return False
        self.cues.at(self.cues.late(t, m), *anims, rt=rt)
        return True

    @property
    def last(self):
        """Top de la derniere partie posee."""
        return max(self.times.values()) if self.times else self.t0


# --- Modele commun -----------------------------------------------------------
# Hypothese affichee a l'ecran comme telle : 200 EUR/mois, 5 %/an.

def _model(years=45):
    # Toujours calculer et caler sur 45 ans, puis tronquer : les points de
    # calage du script portent sur l'annee 1 et l'annee 40.
    s = epargne_mensuelle(200.0, 0.05, 45)
    calibrate(s, "interest_year", {1: 55.0, 40: 14057.0})
    return s[:years]


def _flat(rows):
    return {k: v for row in rows for k, v in row.items()}


def _series_names(rows, marker, n):
    """Noms de parties pour des series : ceux du script quand il les donne.

    Le brief nomme deja ses series (`price_only`, `gross_return`) ; les
    reprendre evite d'inventer un second vocabulaire pour designer la meme
    chose dans `reveals`.
    """
    named = [r.get("series") for r in rows if marker in r and r.get("series")]
    if len(named) != n:
        return [f"series_{i + 1}" for i in range(n)]
    return [str(s) for s in named]


def _series_key(cues, labels, colors, y=2.52):
    """Cle de lecture bleu/ambre.

    Le script n'ecrit de legende que pour certains plans ; sans cle, deux
    series de barres ne se distinguent pas. Ce n'est pas du contenu editorial,
    c'est l'etiquetage du graphe, au meme titre que les libelles d'axe. Le
    vocabulaire est celui des legendes ecrites ailleurs dans l'episode.
    """
    rows = []
    for lab, col in zip(labels, colors):
        chip = RoundedRectangle(width=0.24, height=0.24, corner_radius=0.06,
                                fill_color=col, fill_opacity=1, stroke_width=0)
        rows.append(VGroup(chip, txt(lab, SZ_LABEL, INK_SOFT)).arrange(RIGHT, buff=0.20))
    band = VGroup(*rows).arrange(RIGHT, buff=0.80)
    band.move_to([0, y, 0])
    cues.add(band)
    return band


# =============================================================================
# BarRace  -  S01 (bascule cachee), S26 (bascule montree)
# Parties : year_1..year_n, puis crossover (ou cut + note)
# =============================================================================

def BarRace(seg, cues):
    d = _flat(seg["manim_brief"]["donnees"])
    hidden = bool(d.get("crossover_hidden"))
    cross = d.get("crossover_year")

    n = 10 if hidden else 18
    s = _model(n)
    contrib = [r["contrib_year"] for r in s]
    interest = [r["interest_year"] for r in s]

    ymax = nice_ceiling(max(max(contrib), max(interest)) * 1.18)
    fr = Frame(0.4, n + 0.6, 0, ymax)

    cues.add(fr.gridlines(np.linspace(0, ymax, 5)[1:]))
    cues.add(fr.baseline())
    cues.add(fr.xticks(range(1, n + 1, 1 if n <= 10 else 2), fmt=str))
    cues.frame_anchors(fr)
    cues.add(fr.xlabel("années de versement"))
    cues.legend_colors = [CONTRIB, INTEREST]
    _series_key(cues, ["Vos versements", "Les intérêts"], [CONTRIB, INTEREST])

    bw = fr.wx(0.34)
    groups = []
    for i in range(n):
        y = i + 1
        b1 = Rectangle(width=bw, height=max(fr.wy(contrib[i]), 0.01),
                       fill_color=CONTRIB, fill_opacity=0.92, stroke_width=0)
        b1.move_to(fr.pt(y - 0.19, 0), aligned_edge=DOWN)
        b2 = Rectangle(width=bw, height=max(fr.wy(interest[i]), 0.008),
                       fill_color=INTEREST, fill_opacity=0.95, stroke_width=0)
        b2.move_to(fr.pt(y + 0.19, 0), aligned_edge=DOWN)
        groups.append(VGroup(b1, b2))

    # Une annee, une apparition. Le balayage ne mange jamais plus de la moitie
    # du plan : la bascule (ou son absence) doit rester a l'ecran pendant
    # qu'on l'entend.
    sweep = min(0.62 * n, cues.dur * 0.48)
    years = [f"year_{i + 1}" for i in range(n)]
    rev = Reveal(seg, cues, years, extras=["crossover", "cut", "note"],
                 t0=1.6, span=sweep, rt=min(1.0, sweep / n * 1.6), margin=0.6)
    for key, g in zip(years, groups):
        rev.at(key, GrowFromEdge(g, DOWN))

    extra = VGroup()
    if hidden:
        # La bascule est volontairement coupee : le cadre s'arrete avant elle.
        edge = DashedLine(fr.pt(n + 0.55, 0), fr.pt(n + 0.55, ymax * 0.92),
                          dash_length=0.13, stroke_color=RULE, stroke_width=2.4)
        note = txt("la suite, plus tard", SZ_SOURCE, MUTED)
        note.next_to(edge, RIGHT, buff=0.16).shift(UP * 0.2)
        if note.get_right()[0] > 6.6:
            note.next_to(edge, UP, buff=0.14)
        rev.default("cut", rev.t(years[-1]) + 0.6)
        rev.default("note", rev.t("cut") + 0.6)
        rev.at("cut", Create(edge), rt=0.7, margin=2.2)
        rev.at("note", FadeIn(note), rt=0.5, margin=1.6)
        extra.add(edge, note)
    else:
        i = int(cross) - 1
        line = DashedLine(fr.pt(cross, 0), fr.pt(cross, ymax * 0.95),
                          dash_length=0.13, stroke_color=INTEREST, stroke_width=2.6)
        dot = Dot(fr.pt(cross + 0.19, interest[i]), radius=0.085, color=INTEREST)
        lab = txt(f"année {cross}", SZ_LABEL, INTEREST, weight=SEMIBOLD)
        lab.next_to(line, UP, buff=0.16)
        # Le repere tombe sur la barre qui bascule, quelle que soit la cadence
        # retenue : il lit le top de cette annee-la au lieu de le recalculer.
        rev.default("crossover", rev.t(years[min(i, n - 1)]) + 0.2)
        rev.at("crossover", Create(line), FadeIn(dot, scale=0.4), rt=0.6, margin=2.6)
        rev.at("crossover", fade_up(lab), delay=0.6, rt=0.5, margin=2.0)
        extra.add(line, dot, lab)

    return VGroup(*groups, extra)


# =============================================================================
# StackedBars  -  S04 : chaque couche annuelle plus epaisse que la precedente
# Parties : year_1..year_n
# =============================================================================

def StackedBars(seg, cues):
    n = len(seg["manim_brief"]["donnees"]) or 6
    s = _model(n)
    tops = [r["balance"] for r in s]
    ymax = nice_ceiling(tops[-1] * 1.12)
    fr = Frame(0.4, n + 0.6, 0, ymax)

    cues.add(fr.gridlines(np.linspace(0, ymax, 5)[1:]))
    cues.add(fr.baseline())
    cues.add(fr.xticks(range(1, n + 1), fmt=lambda v: f"an {v}"))
    cues.frame_anchors(fr)
    cues.legend_colors = [CONTRIB, INTEREST]
    _series_key(cues, ["Vos versements", "Les intérêts"], [CONTRIB, INTEREST])

    bw = fr.wx(0.52)
    bars, anims = [], []
    for i in range(n):
        base = 0.0 if i == 0 else tops[i - 1]
        c, it = s[i]["contrib_year"], s[i]["interest_year"]

        # Les couches deja acquises, redessinees en retrait sous la nouvelle.
        stack = VGroup()
        for j in range(i):
            b0 = 0.0 if j == 0 else tops[j - 1]
            cj, ij = s[j]["contrib_year"], s[j]["interest_year"]
            r1 = Rectangle(width=bw, height=fr.wy(cj), fill_color=CONTRIB,
                           fill_opacity=0.30, stroke_width=0)
            r1.move_to(fr.pt(i + 1, b0), aligned_edge=DOWN)
            r2 = Rectangle(width=bw, height=max(fr.wy(ij), 0.012),
                           fill_color=INTEREST, fill_opacity=0.45, stroke_width=0)
            r2.move_to(fr.pt(i + 1, b0 + cj), aligned_edge=DOWN)
            stack.add(r1, r2)

        blue = Rectangle(width=bw, height=fr.wy(c), fill_color=CONTRIB,
                         fill_opacity=0.55 + 0.05 * i, stroke_width=0)
        blue.move_to(fr.pt(i + 1, base), aligned_edge=DOWN)
        amber = Rectangle(width=bw, height=max(fr.wy(it), 0.012),
                          fill_color=INTEREST, fill_opacity=0.95, stroke_width=0)
        amber.move_to(fr.pt(i + 1, base + c), aligned_edge=DOWN)

        bars.append(VGroup(stack, blue, amber))
        anims.append(AnimationGroup(FadeIn(stack, run_time=0.25),
                                    GrowFromEdge(VGroup(blue, amber), DOWN, run_time=0.55),
                                    lag_ratio=0.35))

    span = min(cues.dur * 0.62, 1.6 * n)
    years = [f"year_{i + 1}" for i in range(n)]
    rev = Reveal(seg, cues, years, t0=2.0, span=span,
                 rt=min(1.4, span / max(n - 1, 1) * 0.8), margin=0.8)
    for key, a in zip(years, anims):
        rev.at(key, a)
    return VGroup(*bars)


# =============================================================================
# LineChart  -  S07 (indice, deux series), S25 (capital final, trois series)
# Parties : le nom de serie du brief (price_only, gross_return...), puis values
# =============================================================================

_PALETTE = {"CONTRIB": CONTRIB, "INTEREST": INTEREST, "TEAL": TEAL, "NEG": NEG,
            "WHITE_DIM": WHITE_DIM, "INK_SOFT": INK_SOFT}
_LINE_COLORS = [INTEREST, CONTRIB, TEAL, NEG, WHITE_DIM]


def _point_series(rows):
    """Series de points depuis `donnees` ecrit en tableaux.

    Deux ecritures :
      large  [x, y1, y2, ...]      une ligne par abscisse, une colonne par serie
      longue [x, y] repete         a abscisse egale, la k-ieme ligne va a la
                                   serie k (dans l'ordre du script)
    """
    rows = [[float(v) for v in r] for r in rows]
    if all(len(r) >= 3 for r in rows):
        n = len(rows[0]) - 1
        return [[(r[0], r[k + 1]) for r in rows] for k in range(n)]
    series, seen = [], {}
    for x, y in rows:
        k = seen.get(x, 0)
        seen[x] = k + 1
        while len(series) <= k:
            series.append([])
        series[k].append((x, y))
    return series


INTERPOLATIONS = ("exponentielle", "lineaire", "escalier")


def _interp(pts, xs, mode, growth):
    """Trace entre deux points sources, selon ce que le brief affirme.

    Le moteur ne choisit pas la forme : entre deux valeurs sourcees, la courbe
    est une hypothese, et c'est au script de la declarer.
      exponentielle  taux constant entre deux points. Pour un gain en %
                     (`growth`), c'est le capital 1 + y/100 qui croit a taux
                     constant ; sinon y lui-meme, qui doit rester > 0.
      lineaire       segments droits.
      escalier       la valeur tient jusqu'au point suivant.
    """
    kx = np.array([p[0] for p in pts])
    ky = np.array([p[1] for p in pts])
    if len(pts) == 1:
        return np.full_like(xs, ky[0])
    if mode == "lineaire":
        return np.interp(xs, kx, ky)
    if mode == "escalier":
        idx = np.clip(np.searchsorted(kx, xs, side="right") - 1, 0, len(kx) - 1)
        return ky[idx]
    if growth:
        return (np.exp(np.interp(xs, kx, np.log1p(ky / 100.0))) - 1) * 100.0
    if (ky <= 0).any():
        raise SystemExit("interpolation exponentielle impossible : valeur <= 0 "
                         "(ecrire 'lineaire', ou une unite de gain en %)")
    return np.exp(np.interp(xs, kx, np.log(ky)))


def _named_times(keys, rev):
    """Rendez-vous de parties successives (barres, bandes).

    Une partie nommee par le script garde son top. Une partie non nommee se
    place entre ses voisines nommees, a intervalles reguliers ; avant la
    premiere ou apres la derniere, elle s'en ecarte de GAP + MIN_LEAD par
    rang, le plus court ecart jouable entre deux rendez-vous. Sans aucune
    partie nommee, la cadence par defaut du composant s'applique.
    """
    fixed = [(i, rev.t(k)) for i, k in enumerate(keys) if k in rev.fixed]
    if not fixed:
        return {k: rev.t(k) for k in keys}
    step = GAP + MIN_LEAD
    out = {}
    for i, k in enumerate(keys):
        if k in rev.fixed:
            out[k] = rev.t(k)
            continue
        prev = [f for f in fixed if f[0] < i]
        nxt = [f for f in fixed if f[0] > i]
        if prev and nxt:
            (j0, t0), (j1, t1) = prev[-1], nxt[0]
            out[k] = t0 + (t1 - t0) * (i - j0) / (j1 - j0)
        elif prev:
            j0, t0 = prev[-1]
            out[k] = t0 + step * (i - j0)
        else:
            j1, t1 = nxt[0]
            out[k] = max(0.0, t1 - step * (j1 - i))
    return out


def _frame_end(tracks):
    """Fin de la construction du cadre, depuis les pistes de donnees.

    Regle v2, « le cadre cede » (validee le 25/09/2026) : le cadre est du
    decor, il cede d'abord. Le premier trace recoit sa duree de reference -
    CONTINUOUS_MAX fois la part de sa longueur a parcourir avant son premier
    rendez-vous - et le cadre prend le reste, entre FRAME_MIN et FRAME_MAX.
    Si l'attente est si courte que meme FRAME_MIN priverait le trace de
    MIN_LEAD, le cadre descend sous FRAME_MIN (jusqu'a etre pose d'un bloc).

    Regle v1, « le cadre d'abord » (validee le 23/09/2026, archivee) : le
    cadre prend jusqu'a FRAME_MAX, le trace le reste. Pour y revenir :
    FRAME_RULE = "v1", et les references v1 de video/reference/.
    """
    firsts = [(rdv[0][1], rdv[0][0]) for rdv in tracks.values() if rdv]
    if not firsts:
        return 0.0
    t1, f1 = min(firsts)
    wait = t1 - GAP
    if FRAME_RULE == "v1":
        return min(FRAME_MAX, max(0.0, wait - MIN_LEAD))
    end = min(FRAME_MAX, max(FRAME_MIN, wait - CONTINUOUS_MAX * f1))
    return min(end, max(0.0, wait - MIN_LEAD))


def _build_frame(cues, axes, grid_pairs, xlabels, dur):
    """Le cadre s'installe : axes, puis lignes de grille avec leur valeur, puis
    graduations horizontales, une a une sur `dur` secondes. Sous 0,3 s, il est
    pose d'un bloc des la premiere image."""
    if dur < MIN_RT:
        cues.add(axes, *grid_pairs, *xlabels)
        return
    items = [Create(axes)]
    items += [AnimationGroup(Create(g[0]), FadeIn(g[1])) for g in grid_pairs]
    items += [FadeIn(m) for m in xlabels]
    step = dur / len(items)
    for k, a in enumerate(items):
        t = k * step
        cues.at(t, a, rt=min(step * 1.6, dur - t))


def _plan_runs(sid, tracks, start_after, later, full_max, dur):
    """Planifie des traces qui avancent par morceaux vers leurs rendez-vous.

    `tracks` : {nom: [(fraction, instant), ...]} - la fraction du trace qui
    doit etre atteinte a cet instant. `later` : [(instant, est_un_trace)] des
    autres parties calees, qui bornent la fin du dernier morceau.
    `full_max` : duree d'un trace complet a vitesse de reference (6 s pour une
    courbe) ; un morceau de fraction df dispose au plus de full_max * df.

    Renvoie ({nom: [keyframes, ...]}, debut du premier mouvement). Chaque
    keyframes est une liste [(instant, fraction)] : un morceau continu. Les
    morceaux ne se chevauchent jamais et se suivent a GAP d'ecart ; deux
    rendez-vous consecutifs de la meme piste sont relies sans coupure. Une
    piste qui n'a plus de rendez-vous finit son trace aussitot, a vitesse
    constante ; une piste qui en a encore s'arrete et attend.
    """
    events = sorted((t, order, name, f) for order, (name, rdv) in enumerate(tracks.items())
                    for f, t in rdv)
    remaining = {name: len(rdv) for name, rdv in tracks.items()}
    cur = {name: 0.0 for name in tracks}
    runs = {name: [] for name in tracks}
    busy, first_motion, open_ = start_after, None, None

    def close(next_t, next_is_track):
        nonlocal busy
        name, kf = open_
        if remaining[name] == 0 and kf[-1][1] < 1.0:
            tl, fl = kf[-1]
            if len(kf) >= 2:
                tp, fp = kf[-2]
                end = tl + (1.0 - fl) * (tl - tp) / max(fl - fp, 1e-6)
            else:
                # Piste ouverte sur son tout premier point : pas de vitesse
                # acquise, elle prend la vitesse de reference.
                end = tl + (1.0 - fl) * full_max
            bounds = [dur]
            if next_t is not None:
                bounds.append(next_t - GAP - (MIN_LEAD if next_is_track else 0.0))
            bounds += [t - GAP - (MIN_LEAD if tr else 0.0) for t, tr in later if t > tl + 1e-6]
            end = min(end, max(tl + MIN_RT, min(bounds)))
            kf.append((end, 1.0))
            cur[name] = 1.0
        runs[name].append(kf)
        busy = kf[-1][0]

    for t, _, name, f in events:
        if f <= 1e-9 and cur[name] <= 1e-9 and not runs[name] and not (open_ and open_[0] == name):
            # Rendez-vous au tout debut du trace (premier point sur le bord de
            # l'axe) : rien a anticiper, le trace part sur le mot.
            remaining[name] -= 1
            if open_:
                close(t, True)
            open_ = (name, [(t, 0.0)])
            first_motion = t if first_motion is None else min(first_motion, t)
            busy = t
            continue
        if f <= cur[name] + 1e-9:
            print(f"[ATTENTION] {sid} : rendez-vous de {name} a {t:.2f} s en arriere "
                  f"du trace, ignore", file=sys.stderr)
            remaining[name] -= 1
            continue
        remaining[name] -= 1
        if open_ and open_[0] == name:
            if t <= open_[1][-1][0] + 1e-6:
                print(f"[ATTENTION] {sid} : rendez-vous de {name} non croissants, "
                      f"point a {t:.2f} s ignore", file=sys.stderr)
                continue
            open_[1].append((t, f))
        else:
            if open_:
                close(t, True)
            start = max(busy + GAP, t - full_max * (f - cur[name]))
            if t - start < MIN_LEAD:
                print(f"[ATTENTION] {sid} : {name} n'a que {t - start:.2f} s pour atteindre "
                      f"son rendez-vous de {t:.2f} s ; le script enchaine trop vite",
                      file=sys.stderr)
                start = max(0.0, t - MIN_LEAD)
            open_ = (name, [(start, cur[name]), (t, f)])
            first_motion = start if first_motion is None else min(first_motion, start)
        cur[name] = f
        busy = t
    if open_:
        close(None, False)
    for name, rdv in tracks.items():
        if not rdv:
            print(f"[ATTENTION] {sid} : {name} n'a aucun rendez-vous, jamais trace",
                  file=sys.stderr)
    return runs, first_motion


class TracePiece(Animation):
    """Un morceau de trace : de la fraction atteinte jusqu'a la suivante, selon
    ses keyframes [(instant, fraction)]. Le meme objet recoit plusieurs
    morceaux ; entre deux, il reste a l'arret, trace jusqu'ou il en est."""

    def __init__(self, mob, full, keyframes, **kw):
        self.full = full
        self.frac = _keyframe_rate(keyframes)
        super().__init__(mob, rate_func=linear, introducer=True, **kw)

    def interpolate_mobject(self, alpha):
        self.mobject.pointwise_become_partial(self.full, 0, self.frac(alpha))


class AreaSweep(Animation):
    """Une aire se revele de gauche a droite, jusqu'a la fraction de sa
    longueur que donnent ses keyframes - la meme que son trace."""

    def __init__(self, area, top, base, keyframes, **kw):
        self.top = top
        self.base = base
        self.frac = _keyframe_rate(keyframes)
        super().__init__(area, rate_func=linear, introducer=True, **kw)

    def interpolate_mobject(self, alpha):
        f = self.frac(alpha)
        n = len(self.top)
        pos = min(max(f, 0.0), 1.0) * (n - 1)
        k = int(np.floor(pos))
        pts = [p for p in self.top[:k + 1]]
        if k < n - 1 and pos > k:
            pts.append(self.top[k] + (self.top[k + 1] - self.top[k]) * (pos - k))
        if len(pts) < 2:
            pts = [self.top[0], self.top[0] + np.array([1e-4, 0.0, 0.0])]
        bottom = [np.array([q[0], self.base, 0.0]) for q in reversed(pts)]
        self.mobject.set_points_as_corners(pts + bottom + [pts[0]])


def _keyframe_rate(keyframes):
    """Rate function lineaire par morceaux : a l'instant keyframes[k][0], le
    trace a parcouru la fraction keyframes[k][1] de sa longueur."""
    t0, t1 = keyframes[0][0], keyframes[-1][0]
    ts = np.array([(t - t0) / (t1 - t0) for t, _ in keyframes])
    fs = np.array([f for _, f in keyframes])
    return lambda u: float(np.interp(u, ts, fs))


def _arrival(keyframes, f):
    """Instant ou le trace atteint la fraction f."""
    ts = np.array([t for t, _ in keyframes])
    fs = np.array([x for _, x in keyframes])
    return float(np.interp(f, fs, ts))


def _nice_step(raw):
    """Pas de graduation rond (1, 2, 2.5, 5 x 10^n) juste au-dessus de `raw`."""
    mag = 10 ** np.floor(np.log10(raw)) if raw > 0 else 1.0
    return next(m * mag for m in (1, 2, 2.5, 5, 10) if m * mag >= raw - 1e-9)


def _ease_inverse(f):
    """Instant (0..1) ou ease_in_out_sine atteint la fraction f du trace."""
    return float(np.arccos(1 - 2 * np.clip(f, 0, 1)) / np.pi)


def _y_format(mb):
    """Format des nombres de l'axe vertical, depuis `axes.unite_y`.
    Renvoie (format, gain) : `gain` vaut True pour un gain en %."""
    u = str((mb.get("axes") or {}).get("unite_y", "")).lower()
    if "percent" in u or "pct" in u or "%" in u:
        return "pct", ("growth" in u or "gain" in u)
    if "eur" in u:
        return "euro", False
    return "nombre", False


def _line_points(seg, cues, prefix="series", fill=False, family="LineChart"):
    """LineChart a N series, depuis des points sources.

    Aucun mot a l'ecran - titres d'axes et legendes arrivent par la couche
    overlay - mais les chiffres, oui : graduations des deux axes, valeur de
    chaque point source, valeur d'une annotation. Leur typographie suit la
    langue du rendu (nombres.py).

    Parametres du brief :
      interpolation  "exponentielle" | "lineaire" | "escalier"   OBLIGATOIRE
      couleurs       ["INTEREST", "WHITE_DIM", ...]  une par serie
      origine        [x, y]   point commun ajoute en tete de chaque serie
      croisement     true     repere au premier croisement des series 1 et 2
      ecart          {"x": 30, "valeur": 9.5, "format": "facteur"}
                     accolade entre les series ; `valeur` est facultative et
                     vient du script, jamais d'un calcul
      facteur        {"serie": 1, "x": 30, "valeur": 4.3}
                     multiplicateur ecrit a cote d'un point de la serie
    Parties : series_1..series_n (top = rendez-vous du premier point source,
    le trace est planifie a rebours) ; series_k_point_j (point source et sa
    valeur, apparait quand le trace l'atteint) ; crossing, gap, factor.
    Le cadre (`frame`) est du decor : il se construit jusqu'a la premiere
    donnee, 4 s au plus.
    """
    import nombres
    sid = seg.get("id", "?")
    mb = seg["manim_brief"]
    mode = mb.get("interpolation")
    if mode not in INTERPOLATIONS:
        raise SystemExit(f"{sid} : manim_brief.interpolation obligatoire pour {family}, "
                         f"parmi {', '.join(INTERPOLATIONS)} (recu {mode!r})")
    if not (mb.get("axes") or {}).get("unite_y"):
        raise SystemExit(f"{sid} : manim_brief.axes.unite_y obligatoire pour {family} "
                         f"(percent_growth, percent, EUR, EUR_per_year...)")
    series = _point_series(mb["donnees"])
    origin =tuple(float(v) for v in mb["origine"]) if mb.get("origine") is not None else None
    if origin:
        series = [[origin] + s if s[0][0] > origin[0] else s for s in series]
    yfmt, growth = _y_format(mb)
    cols = [_PALETTE.get(c, c) for c in mb.get("couleurs", [])]
    cols += _LINE_COLORS[len(cols):]
    n = len(series)
    keys = [f"{prefix}_{i + 1}" for i in range(n)]

    x0 = min(p[0] for s in series for p in s)
    x1 = max(p[0] for s in series for p in s)
    ylo = min(0.0, min(p[1] for s in series for p in s))
    yhi = nice_ceiling(max(p[1] for s in series for p in s) * 1.08)
    # Aire de trace ajustee a ce qui l'entoure : bandeau de legende en haut,
    # titre d'axe et source en bas, annotation a droite de la derniere abscisse.
    top = 1.70 if "legende" in cues.anchors else 1.90
    bottom = -2.20 if {"axe_x", "bas"} <= cues.anchors else -2.60
    right = 1.30 if (mb.get("facteur") or mb.get("ecart")) else 0.0
    fr = Frame(x0, x1, ylo, yhi, w=PLOT_W - right, h=top - bottom,
               center=[-right / 2, (top + bottom) / 2, 0])
    cues.legend_colors = cols[:n]

    # Graduations chiffrees : 5 valeurs sur y, des abscisses rondes sur x.
    yvals = np.linspace(ylo, yhi, 5)
    ygrid = fr.gridlines(yvals, fmt=lambda v: nombres.fmt(v, yfmt, 0))
    step = _nice_step((x1 - x0) / 4)
    xvals = list(np.arange(np.ceil(x0 / step) * step, x1 + 1e-9, step))
    xticks = fr.xticks(xvals, fmt=lambda v: nombres.num(v, 0))
    widest = max((m.width for m in ygrid if isinstance(m, Text)), default=0.0)
    cues.frame_anchors(fr, below=0.24 + xticks.height + 0.40, left=0.22 + widest + 0.45)

    # Le cadre est du decor : il n'est pas une revelation et ne borne rien,
    # mais il se construit pendant l'attente de la premiere donnee.
    axes = VGroup(fr.baseline(),
                  Line(fr.pt(x0, ylo), fr.pt(x0, yhi), stroke_color=RULE, stroke_width=2.4))
    grid_pairs = [VGroup(ygrid[k], ygrid[k + 1]) for k in range(0, len(ygrid) - 1, 2)]

    xs = np.linspace(x0, x1, 120)
    curves = []
    areas = {}
    for i, s in enumerate(series):
        ys = _interp(s, xs, mode, growth)
        ln = VMobject(stroke_color=cols[i], stroke_width=5.6 if i == 0 else 4.4)
        ln.set_points_smoothly([fr.pt(x, y) for x, y in zip(xs, ys)])
        # Chaque point source porte sa valeur ; l'origine est une convention,
        # elle n'en porte pas. Point et valeur forment une partie a part,
        # `series_k_point_j`, independante du trace.
        marks = []
        for x, y in s:
            if origin and (x, y) == origin:
                continue
            dot = Dot(fr.pt(x, y), radius=0.08, color=cols[i])
            lab = txt(nombres.fmt(y, yfmt), SZ_LABEL, cols[i], weight=SEMIBOLD)
            lab.next_to(dot, UP, buff=0.14).shift(LEFT * (lab.width / 2 + 0.06))
            marks.append((f"{prefix}_{i + 1}_point_{len(marks) + 1}", x, VGroup(dot, lab)))
        curves.append((ys, ln, marks))
        cues.point(f"{prefix}_{i + 1}_fin", fr.pt(*s[-1]))
        if fill:
            # L'aire va de zero a la courbe ; elle se balaie de gauche a droite
            # au meme rythme que son trace.
            top = [fr.pt(x, y) for x, y in zip(xs, ys)]
            base = fr.py(0.0) if ylo <= 0.0 <= yhi else fr.py(ylo)
            area = VMobject(fill_color=cols[i], fill_opacity=0.30, stroke_width=0)
            areas[i] = (area, np.array(top), base)

    extras, cross, gap, factor = [k for c in curves for k, _, _ in c[2]], None, None, None
    if mb.get("croisement") and n >= 2:
        diff = curves[0][0] - curves[1][0]
        idx = np.where(np.diff(np.sign(diff)) != 0)[0]
        if len(idx):
            j = int(idx[0])
            f = diff[j] / (diff[j] - diff[j + 1])
            cx = xs[j] + f * (xs[j + 1] - xs[j])
            cy = float(np.interp(cx, xs, curves[0][0]))
            cross = VGroup(DashedLine(fr.pt(cx, ylo), fr.pt(cx, cy), dash_length=0.12,
                                      stroke_color=INK_SOFT, stroke_width=2.2),
                           Dot(fr.pt(cx, cy), radius=0.11, color=INK))
            cues.point("croisement", fr.pt(cx, cy))
            extras.append("crossing")
        else:
            print(f"[ATTENTION] {sid} : les series 1 et 2 ne se croisent pas", file=sys.stderr)

    if mb.get("ecart") and n >= 2:
        e = mb["ecart"]
        gx = float(e["x"])
        ys = [float(np.interp(gx, xs, c[0])) for c in curves]
        lo, hi = min(ys), max(ys)
        bx = fr.px(gx) + 0.32
        kw = dict(stroke_color=INK_SOFT, stroke_width=2.4)
        gap = VGroup(Line([bx, fr.py(lo), 0], [bx, fr.py(hi), 0], **kw),
                     Line([bx - 0.14, fr.py(lo), 0], [bx, fr.py(lo), 0], **kw),
                     Line([bx - 0.14, fr.py(hi), 0], [bx, fr.py(hi), 0], **kw))
        if e.get("valeur") is not None:
            tag = txt(nombres.fmt(float(e["valeur"]), e.get("format", "nombre")),
                      SZ_TITLE, INK, weight=SEMIBOLD)
            tag.next_to(gap, RIGHT, buff=0.18)
            gap.add(tag)
        cues.point("ecart", (bx + 0.25, fr.py((lo + hi) / 2)))
        extras.append("gap")

    if mb.get("facteur"):
        fa = mb["facteur"]
        k = int(fa.get("serie", 1)) - 1
        fx = float(fa["x"])
        fy = float(np.interp(fx, xs, curves[k][0]))
        tag = txt(nombres.facteur(float(fa["valeur"])), SZ_TITLE, cols[k], weight=SEMIBOLD)
        tag.next_to(fr.pt(fx, fy), RIGHT, buff=0.34)
        ring = Circle(radius=0.2, stroke_color=cols[k], stroke_width=2.4).move_to(fr.pt(fx, fy))
        factor = VGroup(ring, tag)
        cues.point("facteur", tag.get_center())
        extras.append("factor")

    rev = Reveal(seg, cues, keys, extras=extras, t0=0.6, rt=0.6, margin=0.6)

    # --- traces planifies a rebours, par morceaux ----------------------------
    # Le top d'une serie est le rendez-vous de son premier point source : la
    # courbe l'atteint a l'instant ou la voix enonce la valeur, et c'est la
    # que la valeur apparait. Un point nomme par le script (`series_k_point_j`)
    # a son propre rendez-vous. Les series peuvent alterner - serie 1 a 20 ans,
    # serie 2 a 20 ans, puis les deux a 30 ans : chacune avance par morceaux,
    # jamais en meme temps qu'une autre (voir _plan_runs).
    span = (x1 - x0) or 1.0
    tracks = {}
    for i in range(n):
        key, (_, _, marks) = keys[i], curves[i]
        rdv = [((x - x0) / span, rev.t(mk)) for mk, x, _ in marks if mk in rev.fixed]
        # Le top de la serie vaut rendez-vous de son premier point quand le
        # script ecrit `series_k`, ou quand il ne nomme aucun point (cadence par
        # defaut). Un premier point non nomme, alors que d'autres le sont, est
        # atteint en chemin, sans rendez-vous.
        first_named = bool(marks) and marks[0][0] in rev.fixed
        if marks and not first_named and (key in rev.fixed or not rdv):
            rdv.append(((marks[0][1] - x0) / span, rev.t(key)))
        tracks[key] = sorted(rdv)

    # --- cadre : construit jusqu'au premier mouvement de donnee --------------
    frame_end = _frame_end(tracks)
    _build_frame(cues, axes, grid_pairs, list(xticks), frame_end)
    cues.meta["frame_end"] = frame_end

    own = set(keys) | {mk for c in curves for mk, _, _ in c[2]}
    later = [(t, False) for k, t in rev.times.items() if k in rev.fixed and k not in own]
    runs, first_motion = _plan_runs(sid, tracks, frame_end, later, CONTINUOUS_MAX, cues.dur)

    for key, (_, ln, marks) in zip(keys, curves):
        rs = runs.get(key) or []
        i = keys.index(key)
        sweep = (lambda kf: [AreaSweep(*areas[i], kf)]) if i in areas else (lambda kf: [])
        if len(rs) == 1 and rs[0][0][1] == 0.0 and rs[0][-1][1] == 1.0:
            # Trace d'un seul tenant : un Create, comme le plan valide S09.
            kf = rs[0]
            cues.at(kf[0][0], *sweep(kf), Create(ln, rate_func=_keyframe_rate(kf)),
                    rt=kf[-1][0] - kf[0][0])
        else:
            full = ln.copy()
            for kf in rs:
                cues.at(kf[0][0], *sweep(kf), TracePiece(ln, full, kf),
                        rt=kf[-1][0] - kf[0][0])
        for mk, x, m in marks:
            f = (x - x0) / span
            kf = next((r for r in rs if r[0][1] - 1e-9 <= f <= r[-1][1] + 1e-9), None)
            if kf is None:
                print(f"[ATTENTION] {sid} : {mk} jamais atteint par le trace", file=sys.stderr)
                continue
            t_arr = _arrival(kf, f)
            rev.times[mk] = t_arr
            cues.at(t_arr, FadeIn(m, scale=0.6), rt=LABEL_RT)
    cues.meta["first_data"] = first_motion

    if cross is not None:
        rev.default("crossing", rev.last + 0.4)
        rev.at("crossing", Create(cross[0]), FadeIn(cross[1], scale=0.4), rt=PUNCTUAL_MAX)
    if gap is not None:
        rev.default("gap", rev.last + 0.4)
        rev.at("gap", Create(gap), rt=PUNCTUAL_MAX)
    if factor is not None:
        rev.default("factor", rev.last + 0.4)
        rev.at("factor", Create(factor[0]), fade_up(factor[1], 0.2), rt=PUNCTUAL_MAX)

    return VGroup(*[a[0] for a in areas.values()],
                  *[VGroup(c[1], *[m for _, _, m in c[2]]) for c in curves],
                  *[m for m in (cross, gap, factor) if m is not None])


def LineChart(seg, cues):
    rows = seg["manim_brief"]["donnees"]
    if rows and all(isinstance(r, (list, tuple)) for r in rows):
        return _line_points(seg, cues)
    d = _flat(rows)
    is_index = any("cagr" in r for r in rows)

    if is_index:                                     # S07 - indice base 100
        cagrs = [r["cagr"] for r in rows if "cagr" in r]
        y0, y1 = int(d.get("start_year", 1987)), int(d.get("end_year", 2026))
        n = y1 - y0
        series = [compound_index(c, n) for c in cagrs]
        keys = _series_names(rows, "cagr", len(series))
        cols = [WHITE_DIM, INTEREST]
        widths = [4.0, 5.6]
        ends = None
        ymax = nice_ceiling(max(series[-1]) * 1.06)
        fr = Frame(0, n, 0, ymax)
        cues.frame_anchors(fr)
        cues.add(fr.gridlines(np.linspace(0, ymax, 5)[1:], fmt=lambda v: f"{v:.0f}"))
        cues.add(fr.xticks([0, n // 4, n // 2, 3 * n // 4, n], fmt=lambda v: str(y0 + v)))
        cues.add(fr.xlabel("indice base 100 au départ"))
        cues.legend_colors = cols
    else:                                            # S25 - trois trajectoires
        finals = [r["final"] for r in rows if "final" in r]
        n = 30
        base = _model(n)
        ref = base[-1]["balance"]
        shape = [base[i]["balance"] / ref * 100.0 for i in range(n)]
        series = []
        for f in finals:
            q = f / shape[-1]
            # Depart commun, ecart qui se creuse a partir du tiers de la periode.
            adj = [c * (1 + (q - 1) * min(1.0, max(0.0, (i / n - 0.30) / 0.70)))
                   for i, c in enumerate(shape)]
            series.append([0.0] + adj)
        keys = _series_names(rows, "final", len(series))
        cols = [INTEREST, CONTRIB, NEG]
        widths = [5.6, 4.4, 4.4]
        # Echelle serree : c'est l'ecart d'arrivee qui est le sujet, un axe
        # qui monte a 150 l'ecraserait au tiers bas du cadre.
        ymax = 120
        ends = finals
        fr = Frame(0, n, 0, ymax)
        cues.frame_anchors(fr)
        cues.add(fr.gridlines([25, 50, 75, 100], fmt=lambda v: f"{v:.0f}"))
        cues.add(fr.xticks([0, 10, 20, 30], fmt=lambda v: f"an {v}"))
        cues.add(fr.xlabel("capital atteint, base 100 sans interruption"))
        cues.legend_colors = cols[1:]    # les deux overlays portent sur les ecarts

    cues.add(fr.baseline())

    # Une courbe, un top. Les traces se chevauchent largement par defaut :
    # c'est l'ecart entre les courbes qui est le sujet, il faut le voir se
    # creuser. Un script qui veut les separer franchement - ou les remettre
    # ensemble, comme avant - l'ecrit dans `reveals`.
    draw = min(cues.dur * 0.52, 9.0)
    step = 0.45 * draw
    budget = max(cues.dur - 1.7 - 1.0, 1.2)
    need = step * (len(series) - 1) + draw
    if need > budget:
        draw, step = draw * budget / need, step * budget / need

    rev = Reveal(seg, cues, keys, extras=["values"], t0=1.7, step=step,
                 rt=draw, margin=0.6)

    out = VGroup()
    tips = []
    for i, ser in enumerate(series):
        pts = [fr.pt(j, v) for j, v in enumerate(ser)]
        ln = VMobject(stroke_color=cols[i], stroke_width=widths[i])
        ln.set_points_smoothly(pts)
        end = Dot(pts[-1], radius=0.075, color=cols[i])
        out.add(ln, end)
        tips.append(FadeIn(end, scale=0.5))
        rev.at(keys[i], Create(ln, rate_func=rate_functions.ease_in_out_sine))
        if ends:
            v = ends[i]
            lab = txt(f"{v:.0f}".replace(".", ",") if v == int(v) else f"{v:.1f}".replace(".", ","),
                      SZ_LABEL, cols[i], weight=SEMIBOLD)
            lab.next_to(end, RIGHT, buff=0.18)
            tips.append(FadeIn(lab))
            out.add(lab)

    # Les valeurs d'arrivee attendent que la derniere courbe soit tracee.
    rev.default("values", rev.last + draw)
    rev.at("values", *tips, rt=0.4, margin=0.5)
    return out


# =============================================================================
# BarChart  -  S08 (A/B), S12 (versements vs interets an 1), S15 (an 1 vs an 40)
# Parties : bar_1, bar_2, puis gap (S08), ring (S12) ou reference (S15)
# =============================================================================

def BarChart(seg, cues):
    rows = seg["manim_brief"]["donnees"]
    d = _flat(rows)

    kind = "ab" if "label" in d else ("year1" if "contributions" in d else "span")

    if kind == "ab":                                   # S08
        vals = [r["value"] for r in rows]
        names = ["Cours seul", "Dividendes réinvestis"]
        cols = [WHITE_DIM, INTEREST]
        ratio = vals[1] / vals[0]
        annot = "x" + f"{ratio:.1f}".replace(".", ",")
    elif kind == "year1":                              # S12
        vals = [d["contributions"], d["interest"]]
        names = ["Ce que vous versez", "Ce que ça rapporte"]
        cols = [CONTRIB, INTEREST]
        annot = None
    else:                                              # S15
        yr = [r for r in rows if "interest" in r]
        vals = [r["interest"] for r in yr]
        names = [f"Année {r['year']}" for r in yr]
        cols = [INTEREST, INTEREST]
        annot = None

    ymax = nice_ceiling(max(vals) * 1.22)
    # Si le script pose un texte au centre, le graphe se decale a gauche pour
    # lui laisser la colonne de droite.
    cx, pw = (-1.9, 6.6) if "centre" in cues.anchors else (0.0, 7.2)
    fr = Frame(0.35, len(vals) + 0.65, 0, ymax, w=pw, center=[cx, -0.35, 0])
    cues.frame_anchors(fr)
    cues.add(fr.gridlines(np.linspace(0, ymax, 5)[1:], fmt=euro))
    cues.add(fr.baseline())

    bw = fr.wx(0.42)
    keys = [f"bar_{i + 1}" for i in range(len(vals))]
    extras = {"ab": ["gap"], "year1": ["ring"], "span": ["reference"]}[kind]
    rev = Reveal(seg, cues, keys, extras=extras, t0=1.7, step=1.5, rt=0.9, margin=1.0)

    out = VGroup()
    for i, (v, name, col) in enumerate(zip(vals, names, cols)):
        bar = Rectangle(width=bw, height=max(fr.wy(v), 0.006), fill_color=col,
                        fill_opacity=0.93, stroke_width=0)
        bar.move_to(fr.pt(i + 1, 0), aligned_edge=DOWN)
        cap = txt(euro(round(v)), SZ_BODY, INK, weight=SEMIBOLD)
        cap.next_to(bar, UP, buff=0.20)
        lab = txt(name, SZ_LABEL, INK_SOFT)
        lab.move_to(fr.pt(i + 1, 0)).shift(DOWN * 0.42)
        if lab.width > fr.wx(0.95):
            lab.scale_to_fit_width(fr.wx(0.95))
        out.add(bar, cap, lab)
        rev.at(keys[i], GrowFromEdge(bar, DOWN), rt=0.9)
        rev.at(keys[i], fade_up(cap), fade_up(lab), delay=0.55, rt=0.5)

    if annot:
        x = (fr.px(1) + fr.px(2)) / 2
        t1, t2 = fr.py(vals[0]), fr.py(vals[1])
        brace = VGroup(
            Line([x, t1, 0], [x, t2, 0], stroke_color=INK_SOFT, stroke_width=2.2),
            Line([x - 0.16, t1, 0], [x + 0.16, t1, 0], stroke_color=INK_SOFT, stroke_width=2.2),
            Line([x - 0.16, t2, 0], [x + 0.16, t2, 0], stroke_color=INK_SOFT, stroke_width=2.2))
        tag = txt(annot, SZ_TITLE, INK, weight=SEMIBOLD)
        tag.next_to(brace, RIGHT, buff=0.22)
        rev.default("gap", rev.t(keys[-1]) + 3.2)      # le temps de lire les deux barres
        rev.at("gap", Create(brace), rt=0.6, margin=3.2)
        rev.at("gap", fade_up(tag), delay=0.6, rt=0.5, margin=2.6)
        out.add(brace, tag)

    if kind == "year1":       # la barre presque invisible, montree du doigt
        ring = Circle(radius=0.42, stroke_color=INTEREST, stroke_width=2.4)
        ring.move_to([fr.px(2), fr.py(vals[1]) + 0.04, 0])
        rev.default("ring", rev.t(keys[-1]) + 4.0)
        rev.at("ring", Create(ring), rt=0.6, margin=3.0)
        out.add(ring)

    if kind == "span":        # reference : les versements d'une annee
        ref_v = d.get("yearly_contribution", 2400)
        ref = DashedLine(fr.pt(fr.x0, ref_v), fr.pt(fr.x1, ref_v),
                         dash_length=0.12, stroke_color=CONTRIB, stroke_width=2.4)
        rl = txt("versements : " + euro(ref_v) + "/an", SZ_SOURCE, CONTRIB)
        rl.next_to(ref, UP, buff=0.10).align_to(ref, LEFT)
        rev.default("reference", 1.1)                  # pose avant les barres
        rev.at("reference", Create(ref), rt=0.7, margin=0.8)
        rev.at("reference", FadeIn(rl), delay=0.7, rt=0.4, margin=0.6)
        out.add(ref, rl)

    return out


# =============================================================================
# StackedAreaChart  -  S14 : la part des interets passe devant les versements
# Parties : contributions, interest, boundary, puis half
# =============================================================================

def StackedAreaChart(seg, cues):
    rows = seg["manim_brief"]["donnees"]
    anchors = {0: 0.0}
    anchors.update({r["year"]: r["interest_share"] for r in rows})
    n = max(anchors)
    xs = np.arange(0, n + 1)
    share = monotone_curve(anchors, xs)

    fr = Frame(0, n, 0, 100)
    cues.frame_anchors(fr)
    cues.add(fr.gridlines([25, 50, 75, 100], fmt=lambda v: f"{v:.0f} %"))
    cues.add(fr.baseline())
    cues.add(fr.xticks([0, 10, 20, 30, 40], fmt=lambda v: f"an {v}"))
    cues.legend_colors = [CONTRIB, INTEREST]

    lower = [fr.pt(x, 100 - s) for x, s in zip(xs, share)]
    top = [fr.pt(x, 100) for x in xs]

    contrib_area = Polygon(*([fr.pt(0, 0)] + lower + [fr.pt(n, 0)]),
                           fill_color=CONTRIB, fill_opacity=0.42, stroke_width=0)
    interest_area = Polygon(*(lower + list(reversed(top))),
                            fill_color=INTEREST, fill_opacity=0.62, stroke_width=0)
    border = VMobject(stroke_color=INK, stroke_width=3.4)
    border.set_points_smoothly(lower)

    # Trois temps au lieu d'un : ce que vous versez, ce que le capital verse,
    # puis la frontiere qui se trace sous nos yeux. Les deux legendes du script
    # arrivent dans le meme ordre, chacune sur son aire.
    draw = min(cues.dur * 0.50, 7.5)
    rev = Reveal(seg, cues, ["contributions", "interest", "boundary"],
                 extras=["half"], t0=1.4, step=1.6, rt=0.8, margin=0.8)
    rev.at("contributions", FadeIn(contrib_area))
    rev.at("interest", FadeIn(interest_area))
    rev.at("boundary", Create(border), rt=draw)

    out = VGroup(contrib_area, interest_area, border)

    over = np.where(share >= 50.0)[0]
    if len(over):
        k = int(over[0])
        mark = DashedLine(fr.pt(k, 0), fr.pt(k, 100), dash_length=0.12,
                          stroke_color=INK_SOFT, stroke_width=2)
        lab = txt(f"an {k} : moitié-moitié", SZ_LABEL, INK, weight=SEMIBOLD)
        lab.next_to(mark, UP, buff=0.12)
        # Le jalon suit le trace : il tombe quand la frontiere atteint l'annee.
        rev.default("half", rev.t("boundary") + draw * (k / n) + 0.4)
        rev.at("half", Create(mark), rt=0.5, margin=3.4)
        rev.at("half", fade_up(lab), delay=0.5, rt=0.45, margin=2.8)
        out.add(mark, lab)
    return out


# =============================================================================
# FunnelScatter  -  S20 : la dispersion se resserre quand la duree s'allonge
# Parties : envelope, cloud, point_1..point_n
# =============================================================================

def FunnelScatter(seg, cues):
    rows = seg["manim_brief"]["donnees"]
    xs = [r["holding_years"] for r in rows]
    p1 = [r["p1"] for r in rows]

    # Enveloppe haute : silhouette illustrative, jamais chiffree a l'ecran.
    # Seuls les points sources (1er percentile) portent une valeur ecrite.
    hi = [26.0, 17.0, 11.5, 8.5][:len(xs)]

    fr = Frame(3.0, 32.0, -18.0, 30.0)
    cues.frame_anchors(fr)
    cues.add(fr.gridlines([-10, 10, 20], fmt=lambda v: pct(v, 0)))
    cues.add(fr.xticks(xs, fmt=lambda v: f"{v} ans"))
    cues.add(fr.xlabel("durée de détention"))
    cues.legend_colors = [NEG, TEAL]     # 5 ans -> rouge, 30 ans -> vert
    zero = Line(fr.pt(fr.x0, 0), fr.pt(fr.x1, 0), stroke_color=INK_SOFT, stroke_width=2.6)
    zl = txt("0 %", SZ_SOURCE, INK_SOFT)
    zl.next_to(zero, LEFT, buff=0.20)
    cues.add(zero, zl)

    xd = np.linspace(xs[0], xs[-1], 90)
    hd = monotone_curve(dict(zip(xs, hi)), xd)
    ld = monotone_curve(dict(zip(xs, p1)), xd)
    band = Polygon(*([fr.pt(x, y) for x, y in zip(xd, hd)] +
                     [fr.pt(x, y) for x, y in zip(xd[::-1], ld[::-1])]),
                   fill_color=CONTRIB, fill_opacity=0.20, stroke_width=0)

    rng = np.random.default_rng(20)
    dots = VGroup()
    for _ in range(140):
        x = rng.uniform(xs[0], xs[-1])
        h, l = np.interp(x, xd, hd), np.interp(x, xd, ld)
        mid, half = (h + l) / 2, (h - l) / 2
        y = mid + half * np.clip(rng.normal(0, 0.42), -1, 1)
        dots.add(Dot(fr.pt(x, y), radius=0.035,
                     color=INTEREST if y >= 0 else NEG, fill_opacity=0.75))

    pts = [f"point_{i + 1}" for i in range(len(xs))]
    rev = Reveal(seg, cues, ["envelope", "cloud"] + pts,
                 t0=1.4, step=0.9, rt=0.5, margin=1.4)
    rev.at("envelope", FadeIn(band, shift=RIGHT * 0.3), rt=0.9)
    cloud = rev.default("cloud", rev.t("envelope") + 0.7)
    rev.at("cloud", LaggedStart(*[FadeIn(m, scale=0.3) for m in dots],
                                lag_ratio=0.012, run_time=3.4), rt=3.4)
    # Les points sources ne se posent qu'une fois le nuage retombe : ce sont
    # eux qui portent les chiffres, ils ne doivent pas se perdre dedans.
    rev.default(pts[0], cloud + 4.1, reflow=True)

    marks = VGroup()
    for i, (x, v) in enumerate(zip(xs, p1)):
        col = NEG if v < 0 else TEAL
        dot = Dot(fr.pt(x, v), radius=0.09, color=col)
        lab = txt(pct(v), SZ_LABEL, col, weight=SEMIBOLD)
        lab.next_to(dot, DOWN, buff=0.16)
        marks.add(dot, lab)
        rev.at(pts[i], FadeIn(dot, scale=0.4), fade_up(lab, 0.18), rt=0.5, drop=True)
    return VGroup(band, dots, marks)


# =============================================================================
# BarStrip  -  S21 : 168 placements de 20 ans, tous au-dessus de zero
# Parties : strip_1..strip_k (une passe par defaut), puis tag
# =============================================================================

def BarStrip(seg, cues):
    d = _flat(seg["manim_brief"]["donnees"])
    n = int(d.get("count", 168))
    k_hi = int(d.get("highlighted", 6))

    # Silhouette seule : aucune de ces hauteurs n'est ecrite a l'ecran.
    # Le message porte sur le signe, pas sur les valeurs.
    rng = np.random.default_rng(7)
    vals = np.clip(rng.normal(5.6, 2.2, n), 0.6, 12.5)
    vals = np.convolve(vals, np.ones(9) / 9, mode="same")
    vals = np.clip(vals, 0.9, 11.0)

    fr = Frame(-0.5, n - 0.5, 0, nice_ceiling(vals.max() * 1.2))
    cues.frame_anchors(fr)
    cues.add(fr.gridlines([3, 6, 9], fmt=lambda v: pct(v, 0)))
    zero = Line(fr.pt(fr.x0, 0), fr.pt(fr.x1, 0), stroke_color=INK_SOFT, stroke_width=3)
    zl = txt("0 %", SZ_SOURCE, INK_SOFT)
    zl.next_to(zero, LEFT, buff=0.20)
    cues.add(zero, zl)
    cues.add(fr.xlabel("chaque barre : un placement de 20 ans"))

    bw = fr.wx(0.72)
    hi_idx = set(np.linspace(6, n - 8, k_hi).astype(int).tolist())
    bars = VGroup()
    for i, v in enumerate(vals):
        on = i in hi_idx
        b = Rectangle(width=bw, height=fr.wy(v),
                      fill_color=INTEREST if on else CONTRIB,
                      fill_opacity=0.95 if on else 0.55, stroke_width=0)
        b.move_to(fr.pt(i, 0), aligned_edge=DOWN)
        bars.add(b)

    # Un balayage continu par defaut - c'est la masse qui fait le propos. Un
    # script qui liste plusieurs apparitions le coupe en autant de tranches,
    # chacune posee a son top.
    sweep = min(cues.dur * 0.42, 9.0)
    k = max(1, reveal_count(seg, 1))
    keys = [f"strip_{i + 1}" for i in range(k)]
    rev = Reveal(seg, cues, keys, extras=["tag"], t0=1.5,
                 step=sweep / k, rt=sweep / k, margin=0.6)
    cuts = np.linspace(0, len(bars), k + 1).astype(int)
    for i, key in enumerate(keys):
        part = bars[int(cuts[i]):int(cuts[i + 1])]
        rev.at(key, LaggedStart(*[GrowFromEdge(b, DOWN) for b in part],
                                lag_ratio=0.008, run_time=sweep / k))

    tag = txt(f"{k_hi} sur {n}", SZ_TITLE, INTEREST, weight=SEMIBOLD)
    tag.move_to([fr.px(n * 0.5), fr.py(fr.y1) + 0.28, 0])
    rev.default("tag", rev.t(keys[-1]) + sweep / k + 0.5)
    rev.at("tag", fade_up(tag), rt=0.5, margin=2.2)
    return VGroup(bars, tag)


# =============================================================================
# Timeline  -  S27 : la meme bascule, a quatre rendements differents
# Parties : mark_1..mark_n
# =============================================================================

def Timeline(seg, cues):
    rows = seg["manim_brief"]["donnees"]
    ymax = max(r["year"] for r in rows)
    fr = Frame(0, ymax + 3, 0, 1, h=0.1, center=[0, -0.4, 0])
    cues.frame_anchors(fr)

    cues.add(Line(fr.pt(0, 0), fr.pt(ymax + 3, 0), stroke_color=RULE, stroke_width=3))
    for y in range(0, ymax + 4, 5):
        cues.add(Line(fr.pt(y, 0) + DOWN * 0.10, fr.pt(y, 0) + UP * 0.10,
                      stroke_color=RULE, stroke_width=2))
    cues.add(fr.xticks([0, 10, 20, 30, 40], fmt=lambda v: f"an {v}", buff=0.42))

    out = VGroup()
    cols = [TEAL, INTEREST, CONTRIB, NEG]
    keys = [f"mark_{i + 1}" for i in range(len(rows))]
    rev = Reveal(seg, cues, keys, t0=1.8, step=3.4, rt=0.5, margin=1.2)
    for i, r in enumerate(rows):
        x, rate = r["year"], r["rate"]
        up = (i % 2 == 0)
        stem = Line(fr.pt(x, 0),
                    fr.pt(x, 0) + (UP if up else DOWN) * (1.15 + 0.42 * (i % 2)),
                    stroke_color=cols[i % 4], stroke_width=3)
        dot = Dot(fr.pt(x, 0), radius=0.085, color=cols[i % 4])
        rl = txt(pct(rate, 2 if rate % 1 else 0) + " par an", SZ_BODY,
                 cols[i % 4], weight=SEMIBOLD)
        yl = txt(f"bascule an {x}", SZ_LABEL, INK_SOFT)
        blk = VGroup(rl, yl).arrange(DOWN, buff=0.12)
        blk.next_to(stem, UP if up else DOWN, buff=0.14)
        blk.shift(RIGHT * (min(6.0 - blk.get_right()[0], 0.0)
                           + max(-6.0 - blk.get_left()[0], 0.0)))
        out.add(stem, dot, blk)
        # Un jalon qui n'a plus la place d'etre lu est abandonne, pas tasse.
        if rev.at(keys[i], Create(stem), FadeIn(dot, scale=0.4), rt=0.5, drop=True):
            rev.at(keys[i], fade_up(blk, 0.22 * (1 if up else -1)), delay=0.45, rt=0.5)
    return out


# =============================================================================
# Bars  -  barres simples, groupees, empilees ; mise en avant, repere, annotation
# Parties : bar_g (ou bar_g_s), highlight, reference, annotation
# =============================================================================

def _x_format(mb):
    """Format des etiquettes de categorie, depuis `axes.unite_x`."""
    u = str((mb.get("axes") or {}).get("unite_x", "")).lower()
    if "percent" in u or "pct" in u or "%" in u:
        return "pct"
    if "eur" in u:
        return "euro"
    return "nombre"


BAR_MODES = ("simple", "groupees", "empilees")


def Bars(seg, cues):
    """Barres verticales, une categorie par ligne de `donnees`.

    `donnees` : [x, v1, v2, ...] - x est la categorie (ecrite sous le groupe),
    v1..vn les valeurs des series. Une seule serie : barres simples.

    Parametres du brief :
      mode           "simple" | "groupees" | "empilees"     OBLIGATOIRE
      axes.unite_y   format des valeurs                      OBLIGATOIRE
      axes.unite_x   format des categories (facultatif)
      couleurs       une par serie
      mise_en_avant  {"barre": g} ou {"barre": g, "serie": s}
      repere         {"valeur": v}  ligne horizontale a cette hauteur
      annotation     {"barre": g, "valeur": v, "format": "facteur"}
    Parties : bar_g (serie 1) et bar_g_s ; highlight, reference, annotation.

    Une barre qui monte vers sa hauteur ne revele pas sa valeur tant qu'elle
    n'y est pas : sa croissance est un trace (jusqu'a 6 s), planifie a rebours,
    et sa valeur apparait a l'instant ou la barre l'atteint, sur le mot qui
    l'enonce. Mise en avant, repere et annotation surgissent (1,5 s).
    """
    import nombres
    sid = seg.get("id", "?")
    mb = seg["manim_brief"]
    mode = mb.get("mode")
    if mode not in BAR_MODES:
        raise SystemExit(f"{sid} : manim_brief.mode obligatoire pour Bars, parmi "
                         f"{', '.join(BAR_MODES)} (recu {mode!r})")
    if not (mb.get("axes") or {}).get("unite_y"):
        raise SystemExit(f"{sid} : manim_brief.axes.unite_y obligatoire pour Bars")
    rows = [[float(v) for v in r] for r in mb["donnees"]]
    n_s = len(rows[0]) - 1
    if mode == "simple" and n_s != 1:
        raise SystemExit(f"{sid} : mode 'simple' mais {n_s} valeurs par ligne")
    yfmt, _ = _y_format(mb)
    xfmt = _x_format(mb)
    cols = [_PALETTE.get(c, c) for c in mb.get("couleurs", [])]
    cols += [CONTRIB, INTEREST, TEAL, NEG, WHITE_DIM][len(cols):]
    n_g = len(rows)

    if mode == "empilees":
        tops = [sum(max(v, 0) for v in r[1:]) for r in rows]
        lows = [sum(min(v, 0) for v in r[1:]) for r in rows]
    else:
        tops = [max(r[1:]) for r in rows]
        lows = [min(r[1:]) for r in rows]
    repere = mb.get("repere")
    extra = [float(repere["valeur"])] if repere else []
    # Graduations a pas rond (1, 2, 2,5, 5 x 10^n), cinq intervalles environ.
    raw_hi = max([max(tops)] + extra) * 1.12
    raw_lo = min([0.0] + lows + extra) * 1.12
    ystep = _nice_step((raw_hi - raw_lo) / 5)
    yhi = float(np.ceil(raw_hi / ystep) * ystep)
    ylo = float(np.floor(raw_lo / ystep) * ystep)

    top = 1.70 if "legende" in cues.anchors else 1.90
    bottom = -2.20 if {"axe_x", "bas"} <= cues.anchors else -2.60
    right = 1.30 if mb.get("annotation") else 0.0
    fr = Frame(0.4, n_g + 0.6, ylo, yhi, w=PLOT_W - right, h=top - bottom,
               center=[-right / 2, (top + bottom) / 2, 0])
    cues.legend_colors = cols[:n_s]

    yvals = list(np.arange(ylo, yhi + ystep / 2, ystep))
    ygrid = fr.gridlines(yvals, fmt=lambda v: nombres.fmt(v, yfmt, 0))
    xlabels = [txt(nombres.fmt(r[0], xfmt), SZ_SOURCE, MUTED) for r in rows]
    for g, lab in enumerate(xlabels):
        lab.move_to(fr.pt(g + 1, ylo)).shift(DOWN * (0.24 + lab.height / 2))
    widest = max((m.width for m in ygrid if isinstance(m, Text)), default=0.0)
    xh = max(m.height for m in xlabels)
    cues.frame_anchors(fr, below=0.24 + xh + 0.40, left=0.22 + widest + 0.45)
    axes = VGroup(Line(fr.pt(fr.x0, 0), fr.pt(fr.x1, 0), stroke_color=RULE, stroke_width=2.4),
                  Line(fr.pt(fr.x0, ylo), fr.pt(fr.x0, yhi), stroke_color=RULE, stroke_width=2.4))
    grid_pairs = [VGroup(ygrid[k], ygrid[k + 1]) for k in range(0, len(ygrid) - 1, 2)]

    # --- barres ----------------------------------------------------------
    gw = 0.62                                   # largeur d'un groupe, en unites x
    bw = fr.wx(gw / (n_s if mode == "groupees" else 1))
    bars = {}                                   # nom de partie -> (rect, etiquette)
    order = []
    for g, r in enumerate(rows):
        base_pos, base_neg = 0.0, 0.0
        for s_i, v in enumerate(r[1:]):
            key = f"bar_{g + 1}" if n_s == 1 else f"bar_{g + 1}_{s_i + 1}"
            if mode == "groupees":
                cx = g + 1 - gw / 2 + gw / n_s * (s_i + 0.5)
                y0 = 0.0
            else:
                cx = g + 1
                y0 = (base_pos if v >= 0 else base_neg) if mode == "empilees" else 0.0
            h = max(abs(fr.wy(v)), 0.006)
            rect = Rectangle(width=bw, height=h, fill_color=cols[s_i], fill_opacity=0.92,
                             stroke_width=0)
            edge = DOWN if v >= 0 else UP
            rect.move_to(fr.pt(cx, y0), aligned_edge=edge)
            lab = txt(nombres.fmt(v, yfmt), SZ_LABEL, INK, weight=SEMIBOLD)
            if mode == "empilees":
                lab.move_to(rect)
                if lab.height > h * 0.8 or lab.width > bw * 1.4:
                    lab.next_to(rect, RIGHT, buff=0.12)
            else:
                lab.next_to(rect, UP if v >= 0 else DOWN, buff=0.14)
            bars[key] = (rect, lab, edge)
            order.append(key)
            if mode == "empilees":
                if v >= 0:
                    base_pos += v
                else:
                    base_neg += v
            cues.point(key, rect.get_edge_center(UP if v >= 0 else DOWN))

    extras, hl, ref, ann = [], None, None, None
    if mb.get("mise_en_avant"):
        m = mb["mise_en_avant"]
        g = int(m["barre"])
        key = f"bar_{g}" if n_s == 1 else f"bar_{g}_{int(m.get('serie', 1))}"
        if key not in bars:
            raise SystemExit(f"{sid} : mise_en_avant vise {key!r}, absente")
        target = bars[key][0]
        box = SurroundingRectangle(target, color=INK, buff=0.08, stroke_width=2.6,
                                   corner_radius=0.05)
        others = [bars[k][0] for k in order if k != key]
        hl = (box, others)
        extras.append("highlight")
    if repere:
        rv = float(repere["valeur"])
        line = DashedLine(fr.pt(fr.x0, rv), fr.pt(fr.x1, rv), dash_length=0.12,
                          stroke_color=INK_SOFT, stroke_width=2.4)
        tag = txt(nombres.fmt(rv, yfmt), SZ_LABEL, INK_SOFT, weight=SEMIBOLD)
        tag.next_to(line, RIGHT, buff=0.12)
        ref = VGroup(line, tag)
        cues.point("reference", line.get_right())
        extras.append("reference")
    if mb.get("annotation"):
        a = mb["annotation"]
        g = int(a["barre"])
        tag = txt(nombres.fmt(float(a["valeur"]), a.get("format", "nombre")),
                  SZ_TITLE, INK, weight=SEMIBOLD)
        grp_top = max(bars[k][1].get_top()[1] for k in order
                      if k == f"bar_{g}" or k.startswith(f"bar_{g}_"))
        tag.move_to([fr.px(g), grp_top + 0.45, 0])
        ann = tag
        cues.point("annotation", tag.get_center())
        extras.append("annotation")

    rev = Reveal(seg, cues, order, extras=extras, t0=1.6, rt=PUNCTUAL_MAX, margin=0.6)

    # --- croissance planifiee a rebours --------------------------------------
    # Une barre est une piste a un seul rendez-vous : toute sa hauteur a
    # l'instant du mot. Sa croissance est un trace, jusqu'a CONTINUOUS_MAX : la
    # barre suivante commence a monter pendant que la voix parle encore de la
    # precedente. Le mouvement anticipe, l'information attend.
    times = _named_times(order, rev)
    tracks = {k: [(1.0, times[k])] for k in order}
    frame_end = _frame_end(tracks)
    _build_frame(cues, axes, grid_pairs, xlabels, frame_end)
    cues.meta["frame_end"] = frame_end

    later = [(t, False) for k, t in rev.times.items() if k in rev.fixed and k not in bars]
    runs, first_motion = _plan_runs(sid, tracks, frame_end, later, CONTINUOUS_MAX, cues.dur)
    cues.meta["first_data"] = first_motion
    for k in order:
        rect, lab, edge = bars[k]
        for kf in runs.get(k) or []:
            t0, t1 = kf[0][0], kf[-1][0]
            cues.at(t0, GrowBar(rect, edge), rt=t1 - t0)
            rev.times[k] = t1
            cues.at(t1, FadeIn(lab, scale=0.6), rt=LABEL_RT)

    if hl is not None:
        box, others = hl
        rev.default("highlight", rev.last + 0.4)
        rev.at("highlight", Create(box), *[_opacity_to(o, 0.32) for o in others],
               rt=PUNCTUAL_MAX)
    if ref is not None:
        rev.default("reference", rev.last + 0.4)
        rev.at("reference", Create(ref[0]), FadeIn(ref[1]), rt=PUNCTUAL_MAX)
    if ann is not None:
        rev.default("annotation", rev.last + 0.4)
        rev.at("annotation", fade_up(ann, 0.2), rt=PUNCTUAL_MAX)

    out = VGroup(*[VGroup(bars[k][0], bars[k][1]) for k in order])
    for m in (hl[0] if hl else None, ref, ann):
        if m is not None:
            out.add(m)
    return out


# =============================================================================
# Areas  -  aires superposees depuis zero, bandes de dispersion
# Parties : mode aires  : area_k, area_k_point_j (+ crossing, gap, factor)
#           mode bandes : band_k
# =============================================================================

AREA_MODES = ("aires", "bandes")
BAND_BOUNDS = ("plancher", "plafond")


def Areas(seg, cues):
    """Aires et bandes.

    mode "aires"  : chaque serie est une aire de zero a sa courbe ; les aires
                    se superposent. Memes donnees et memes parametres que
                    LineChart (interpolation obligatoire) ; parties area_k et
                    area_k_point_j. L'aire se balaie au rythme de son trace.
    mode "bandes" : une bande verticale par ligne de `donnees`, voir _bands.
    """
    mb = seg["manim_brief"]
    mode = mb.get("mode")
    if mode not in AREA_MODES:
        raise SystemExit(f"{seg.get('id', '?')} : manim_brief.mode obligatoire pour Areas, "
                         f"parmi {', '.join(AREA_MODES)} (recu {mode!r})")
    if mode == "aires":
        return _line_points(seg, cues, prefix="area", fill=True, family="Areas")
    return _bands(seg, cues)


def _bands(seg, cues):
    """Bandes de dispersion, une par categorie.

    `donnees` : [x, bas, haut] - bande entre deux bornes sourcees ; ou
    [x, borne] avec `borne` = "plancher" (bande ouverte vers le haut : les
    cas au-dessus de la valeur) ou "plafond" (ouverte vers le bas). Le cote
    ouvert s'efface en degrade : le moteur n'invente jamais la borne que la
    source ne donne pas.

    Une bande est un trace (jusqu'a CONTINUOUS_MAX) planifie a rebours : elle
    s'etend depuis son cote ouvert - ou depuis son milieu - et atteint sa
    borne sur le mot qui l'enonce ; la borne et sa valeur apparaissent alors.
    """
    import nombres
    sid = seg.get("id", "?")
    mb = seg["manim_brief"]
    if not (mb.get("axes") or {}).get("unite_y"):
        raise SystemExit(f"{sid} : manim_brief.axes.unite_y obligatoire pour Areas")
    rows = [[float(v) for v in r] for r in mb["donnees"]]
    width = {len(r) for r in rows}
    if width == {3}:
        borne = "deux"
    elif width == {2}:
        borne = mb.get("borne")
        if borne not in BAND_BOUNDS:
            raise SystemExit(f"{sid} : une seule valeur par ligne ; manim_brief.borne "
                             f"obligatoire, parmi {', '.join(BAND_BOUNDS)} (recu {borne!r})")
    else:
        raise SystemExit(f"{sid} : Areas bandes attend [x, bas, haut] ou [x, borne]")
    yfmt, _ = _y_format(mb)
    xfmt = _x_format(mb)
    body = (_PALETTE.get(c, c) for c in mb.get("couleurs", []))
    body = next(body, CONTRIB)
    n_g = len(rows)

    vals = [v for r in rows for v in r[1:]]
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or abs(hi) or 1.0
    # Le cote ouvert a besoin de place pour s'effacer ; l'autre juste d'une marge.
    raw_hi = hi + (0.35 if borne == "plancher" else 0.10) * span
    raw_lo = lo - (0.35 if borne == "plafond" else 0.10) * span
    raw_hi, raw_lo = max(raw_hi, 0.0), min(raw_lo, 0.0)
    ystep = _nice_step((raw_hi - raw_lo) / 5)
    yhi = float(np.ceil(raw_hi / ystep) * ystep)
    ylo = float(np.floor(raw_lo / ystep) * ystep)

    top = 1.70 if "legende" in cues.anchors else 1.90
    bottom = -2.20 if {"axe_x", "bas"} <= cues.anchors else -2.60
    fr = Frame(0.4, n_g + 0.6, ylo, yhi, h=top - bottom, center=[0, (top + bottom) / 2, 0])
    cues.legend_colors = [body]

    yvals = list(np.arange(ylo, yhi + ystep / 2, ystep))
    ygrid = fr.gridlines(yvals, fmt=lambda v: nombres.fmt(v, yfmt, 0))
    xlabels = [txt(nombres.fmt(r[0], xfmt), SZ_SOURCE, MUTED) for r in rows]
    for g, lab in enumerate(xlabels):
        lab.move_to(fr.pt(g + 1, ylo)).shift(DOWN * (0.24 + lab.height / 2))
    widest = max((m.width for m in ygrid if isinstance(m, Text)), default=0.0)
    xh = max(m.height for m in xlabels)
    cues.frame_anchors(fr, below=0.24 + xh + 0.40, left=0.22 + widest + 0.45)
    axes = VGroup(fr.baseline(),
                  Line(fr.pt(fr.x0, ylo), fr.pt(fr.x0, yhi), stroke_color=RULE, stroke_width=2.4))
    if ylo < 0.0 < yhi:
        # Zero : la ligne qui separe gain et perte. Decor, mais appuye.
        axes.add(Line(fr.pt(fr.x0, 0.0), fr.pt(fr.x1, 0.0), stroke_color=INK_SOFT,
                      stroke_width=2.6))
    grid_pairs = [VGroup(ygrid[k], ygrid[k + 1]) for k in range(0, len(ygrid) - 1, 2)]

    bw = fr.wx(0.50)
    order, bands = [], {}
    for g, r in enumerate(rows):
        key = f"band_{g + 1}"
        if borne == "deux":
            b_lo, b_hi, edge = r[1], r[2], ORIGIN
        elif borne == "plancher":
            b_lo, b_hi, edge = r[1], yhi, UP
        else:
            b_lo, b_hi, edge = ylo, r[1], DOWN
        rect = Rectangle(width=bw, height=max(fr.wy(b_hi - b_lo), 0.006), stroke_width=0)
        rect.move_to(fr.pt(g + 1, (b_lo + b_hi) / 2))
        if borne == "deux":
            rect.set_fill(body, opacity=0.55)
        else:
            # Degrade vers le cote ouvert : aucune borne n'y est affirmee.
            rect.set_fill([body, BG] if borne == "plancher" else [BG, body], opacity=0.85)
            rect.set_sheen_direction(UP)
        marks = VGroup()
        stated = [r[1], r[2]] if borne == "deux" else [r[1]]
        for v in stated:
            col = NEG if v < 0 else TEAL
            edge_line = Line(fr.pt(g + 1 - 0.25, v), fr.pt(g + 1 + 0.25, v),
                             stroke_color=col, stroke_width=4.2)
            lab = txt(nombres.fmt(v, yfmt), SZ_LABEL, col, weight=SEMIBOLD)
            below = (borne == "plancher") or (borne == "deux" and v == r[1])
            lab.next_to(edge_line, DOWN if below else UP, buff=0.12)
            marks.add(edge_line, lab)
            cues.point(f"{key}_{'bas' if below else 'haut'}", edge_line.get_center())
        bands[key] = (rect, marks, edge)
        order.append(key)

    rev = Reveal(seg, cues, order, t0=1.6, rt=PUNCTUAL_MAX, margin=0.6)
    times = _named_times(order, rev)
    tracks = {k: [(1.0, times[k])] for k in order}
    frame_end = _frame_end(tracks)
    _build_frame(cues, axes, grid_pairs, xlabels, frame_end)
    cues.meta["frame_end"] = frame_end

    later = [(t, False) for k, t in rev.times.items() if k in rev.fixed and k not in bands]
    runs, first_motion = _plan_runs(sid, tracks, frame_end, later, CONTINUOUS_MAX, cues.dur)
    cues.meta["first_data"] = first_motion
    for k in order:
        rect, marks, edge = bands[k]
        for kf in runs.get(k) or []:
            t0, t1 = kf[0][0], kf[-1][0]
            cues.at(t0, GrowBar(rect, edge), rt=t1 - t0)
            rev.times[k] = t1
            cues.at(t1, FadeIn(marks, scale=0.8), rt=LABEL_RT)

    return VGroup(*[VGroup(bands[k][0], bands[k][1]) for k in order])


class GrowBar(Animation):
    """Une barre monte depuis sa base : la hauteur croit, la largeur ne bouge
    pas (GrowFromEdge grandit aussi en largeur, ce qui se voit sur une
    croissance lente). `edge` : le bord qui reste fixe - DOWN pour une barre,
    UP pour une bande qui descend vers son plancher, ORIGIN pour une bande qui
    s'ouvre depuis son milieu."""

    def __init__(self, rect, edge=DOWN, **kw):
        self.edge = edge
        self.anchor = rect.get_edge_center(edge).copy()
        self.full_h = rect.height
        super().__init__(rect, rate_func=rate_functions.smooth, introducer=True, **kw)

    def interpolate_mobject(self, alpha):
        m = self.mobject
        m.become(self.starting_mobject)
        m.stretch_to_fit_height(max(self.full_h * alpha, 1e-4))
        m.move_to(self.anchor, aligned_edge=self.edge)


def _opacity_to(m, value):
    """Voir scenes._opacity : une copie par animation, jamais `.animate`."""
    return Transform(m, m.copy().set_opacity(value))


COMPONENTS = {
    "BarRace": BarRace,
    "StackedBars": StackedBars,
    "LineChart": LineChart,
    "BarChart": BarChart,
    "StackedAreaChart": StackedAreaChart,
    "FunnelScatter": FunnelScatter,
    "BarStrip": BarStrip,
    "Timeline": Timeline,
    "Bars": Bars,
    "Areas": Areas,
}
