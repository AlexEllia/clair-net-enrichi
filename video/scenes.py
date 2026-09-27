# -*- coding: utf-8 -*-
"""Scene d'un segment : fond, visuel, overlays, et l'ordonnanceur qui les joue.

Un segment = un plan. Sa duree est celle du fichier audio correspondant ;
le montage final se contente de coller les plans bout a bout.
"""

import json
import sys

from manim import *
import numpy as np

from style import (BG, BG_LIFT, INK, INK_SOFT, MUTED, RULE_SOFT, CONTRIB,
                   INTEREST, NEG, TEAL, FW, FH, Y_TOP, Y_BOTTOM, X_LEFT,
                   SZ_TITLE, SZ_BIG, SZ_HUGE, SZ_BODY, SZ_LABEL, SZ_SOURCE,
                   txt, fade_up)
from components import COMPONENTS, Cues

Z_BACK, Z_AMB, Z_PLOT, Z_OVER = -100, -50, 0, 50


# =============================================================================
# Fond et ambiances
# =============================================================================

def backdrop():
    base = Rectangle(width=FW + 0.4, height=FH + 0.4, fill_opacity=1, stroke_width=0)
    base.set_color(BG)
    halo = Rectangle(width=FW + 0.4, height=FH + 0.4, stroke_width=0, fill_opacity=0.55)
    halo.set_color_by_gradient(BG_LIFT, BG)
    g = VGroup(base, halo)
    g.set_z_index(Z_BACK)
    return g


def _drifter(mob, home, amp, speed, phase):
    """Derive lente et bouclee autour d'un point d'ancrage."""
    def upd(m, dt):
        m.clock = getattr(m, "clock", phase) + dt * speed
        m.move_to(home + np.array([np.cos(m.clock) * amp[0],
                                   np.sin(m.clock * 0.73) * amp[1], 0.0]))
    mob.add_updater(upd)
    return mob


def ambience_field(seg):
    """`fond_anime` : champ de points en derive lente. Calme, tres peu contraste."""
    rng = np.random.default_rng(abs(hash(seg["id"])) % 10_000)
    g = VGroup()
    for _ in range(64):
        x = rng.uniform(-FW / 2 + 0.3, FW / 2 - 0.3)
        y = rng.uniform(-FH / 2 + 0.3, FH / 2 - 0.3)
        r = rng.uniform(0.018, 0.055)
        col = INTEREST if rng.random() < 0.22 else CONTRIB
        d = Dot([x, y, 0], radius=r, color=col, fill_opacity=rng.uniform(0.10, 0.34))
        _drifter(d, np.array([x, y, 0.0]),
                 (rng.uniform(0.10, 0.34), rng.uniform(0.08, 0.26)),
                 rng.uniform(0.10, 0.28), rng.uniform(0, 6.28))
        g.add(d)
    for _ in range(3):
        y = rng.uniform(-2.6, 2.6)
        ln = Line([-FW / 2 - 1, y, 0], [FW / 2 + 1, y, 0],
                  stroke_color=RULE_SOFT, stroke_width=1.4)
        _drifter(ln, np.array([0.0, y, 0.0]), (0.0, 0.22), rng.uniform(0.06, 0.14),
                 rng.uniform(0, 6.28))
        g.add(ln)
    g.set_z_index(Z_AMB)
    return g


def ambience_horizon(seg):
    """`broll` : bandes d'horizon en parallaxe.

    Pas de rushes : la chaine est faceless et le dossier ne contient aucune
    banque d'images. On tient le plan avec une texture generee, plus sobre
    qu'un fond anime, pour laisser la voix porter.
    """
    rng = np.random.default_rng(abs(hash(seg["id"])) % 10_000 + 5)
    g = VGroup()
    for k in range(6):
        y0 = -2.9 + k * 0.95
        amp = 0.16 + 0.10 * k
        freq = 0.42 + 0.16 * rng.random()
        ph = rng.uniform(0, 6.28)
        xs = np.linspace(-FW / 2 - 2.2, FW / 2 + 2.2, 90)
        pts = [np.array([x, y0 + amp * np.sin(freq * x + ph), 0.0]) for x in xs]
        curve = VMobject(stroke_color=CONTRIB if k % 2 else INTEREST,
                         stroke_width=1.8 + 0.35 * k,
                         stroke_opacity=0.10 + 0.035 * k)
        curve.set_points_smoothly(pts)
        speed = 0.055 + 0.030 * k          # parallaxe : le proche va plus vite
        home = curve.get_center().copy()

        def upd(m, dt, s=speed, h=home):
            m.clock = getattr(m, "clock", 0.0) + dt * s
            m.move_to(h + np.array([np.sin(m.clock) * 1.5, np.cos(m.clock * 0.6) * 0.10, 0.0]))
        curve.add_updater(upd)
        g.add(curve)
    g.set_z_index(Z_AMB)
    return g


def ambience_type(seg):
    """`typo_cinetique` : un filet horizontal qui se trace sous le texte."""
    rule = Line([-3.4, -1.55, 0], [3.4, -1.55, 0], stroke_color=RULE_SOFT, stroke_width=2)
    rule.set_z_index(Z_AMB)
    return VGroup(rule)


# =============================================================================
# Overlays  -  le texte a l'ecran, tel qu'ecrit dans script.json
# =============================================================================

SPLIT_DOT = "·"      # separateur de valeurs successives
ARROW = "→"          # consequence : deux temps


def _fit(m, max_w):
    if m.width > max_w:
        m.scale_to_fit_width(max_w)
    return m


PLOT_H_MAX = 5.2     # hauteur maximale d'un titre d'axe vertical


def _fit_h(m, max_h):
    if m.height > max_h:
        m.scale_to_fit_height(max_h)
    return m


def _opacity(m, value):
    """Transition d'opacite sur un objet deja pose dans la scene.

    Volontairement pas `m.animate.set_opacity(...)` : deux `.animate` sur le
    meme objet se partagent l'unique attribut `target` et le second ecrase la
    cible du premier. Ici chaque animation porte sa propre copie.
    """
    return Transform(m, m.copy().set_opacity(value))


def _wrap(s, width):
    """Retour a la ligne sur mots, pour les encarts etroits."""
    words, lines, cur = s.split(), [], ""
    for w in words:
        cand = (cur + " " + w).strip()
        if len(cand) > width and cur:
            lines.append(cur)
            cur = w
        else:
            cur = cand
    if cur:
        lines.append(cur)
    return "\n".join(lines)


def _scrim(m, pad=0.34):
    s = RoundedRectangle(width=m.width + 2 * pad, height=m.height + 1.3 * pad,
                         corner_radius=0.16, fill_color=BG, fill_opacity=0.62,
                         stroke_width=0)
    s.move_to(m).set_z_index(Z_OVER - 1)
    return s


def add_overlays(seg, cues, visual):
    """Depose les `overlay_texte` selon leur ancre et le type visuel du plan."""
    items = seg.get("overlay_texte") or []
    if not items:
        return VGroup()

    big = visual in ("typo_cinetique", "fond_anime", "broll")
    out = VGroup()

    by = {}
    for o in items:
        by.setdefault(o["ancre"], []).append(o)

    # --- titre_haut ----------------------------------------------------------
    for o in by.get("titre_haut", []):
        t = _fit(txt(o["texte_fr"], SZ_TITLE, INK, weight=SEMIBOLD), FW - 2.4)
        t.move_to([0, Y_TOP, 0]).set_z_index(Z_OVER)
        cues.at(cues.late(o["t_rel_s"], 1.0), fade_up(t), rt=0.6)
        out.add(t)

    # --- axe_x / axe_y : titres d'axes, poses sur les ancres du composant ----
    for anchor in ("axe_x", "axe_y"):
        for o in by.get(anchor, []):
            s = o["texte_fr"]
            first = next((c for c in s if c.isalpha()), "")
            if first and not first.isupper():
                print(f"[ATTENTION] {seg.get('id')} : libelle {anchor} sans majuscule "
                      f"initiale : {s!r} (laisse tel quel)", file=sys.stderr, flush=True)
            if anchor not in cues.points:
                print(f"[ATTENTION] {seg.get('id')} : le composant n'exporte pas l'ancre "
                      f"{anchor!r}, libelle {s!r} non pose", file=sys.stderr, flush=True)
                continue
            x, y, rot = cues.points[anchor]
            t = txt(s, SZ_LABEL, INK_SOFT)
            if rot:
                t.rotate(rot * DEGREES)
                _fit_h(t, PLOT_H_MAX)
            else:
                _fit(t, FW - 2.4)
            t.move_to([x, y, 0]).set_z_index(Z_OVER)
            cues.at(cues.late(o["t_rel_s"], 0.8), FadeIn(t), rt=0.5)
            out.add(t)

    # --- bas : sources et mentions ------------------------------------------
    for o in by.get("bas", []):
        t = _fit(txt(o["texte_fr"], SZ_SOURCE, MUTED), FW - 1.8)
        t.move_to([0, Y_BOTTOM - 0.44, 0]).set_z_index(Z_OVER)
        cues.at(cues.late(o["t_rel_s"], 0.8), FadeIn(t), rt=0.5)
        out.add(t)

    # --- legende -------------------------------------------------------------
    # Sur un graphe, la legende passe en bandeau au-dessus de l'aire de trace :
    # empilee a gauche, elle heurtait les libelles de l'axe des ordonnees.
    legs = by.get("legende", [])
    cols = list(cues.legend_colors) or (
        [CONTRIB, NEG, TEAL] if big else [CONTRIB, INTEREST, NEG])
    rows = []
    for i, o in enumerate(legs):
        chip = RoundedRectangle(width=0.26, height=0.26, corner_radius=0.06,
                                fill_color=cols[i % len(cols)], fill_opacity=1,
                                stroke_width=0)
        lab = txt(o["texte_fr"], SZ_BODY if big else SZ_LABEL, INK if big else INK_SOFT)
        rows.append(VGroup(chip, lab).arrange(RIGHT, buff=0.24))

    if rows and big:
        for i, row in enumerate(rows):
            _fit(row, FW - 3.0)
            row.move_to([0, 0.55 - 1.35 * i, 0])
    elif rows:
        band = VGroup(*rows).arrange(RIGHT, buff=0.9)
        _fit(band, FW - 1.8)
        # Sous le titre quand il y en a un : au meme niveau, ils se chevauchent.
        band.move_to([0, Y_TOP - (0.80 if by.get("titre_haut") else 0.05), 0])

    for row, o in zip(rows, legs):
        row.set_z_index(Z_OVER)
        cues.at(cues.late(o["t_rel_s"], 0.9), fade_up(row, 0.2), rt=0.55)
        out.add(row)

    # --- centre --------------------------------------------------------------
    ctr = by.get("centre", [])
    if not ctr:
        return out

    if not big:
        # Un graphe occupe deja le centre : le propos passe en encart lateral.
        for i, o in enumerate(ctr):
            t = _fit(txt(_wrap(o["texte_fr"], 18), SZ_BODY, INK, weight=SEMIBOLD), 3.7)
            card = RoundedRectangle(width=t.width + 0.7, height=t.height + 0.6,
                                    corner_radius=0.14, fill_color=BG_LIFT,
                                    fill_opacity=0.92, stroke_color=INTEREST,
                                    stroke_width=2)
            grp = VGroup(card, t)
            t.move_to(card)
            grp.move_to([4.15, 1.4 - 1.9 * i, 0]).set_z_index(Z_OVER)
            cues.at(cues.late(o["t_rel_s"], 1.2), fade_up(grp, 0.24), rt=0.6)
            out.add(grp)
        return out

    if len(ctr) == 1 and SPLIT_DOT in ctr[0]["texte_fr"]:
        # Une meme grandeur qui change de valeur : fondu sur place, sans
        # deplacement, parce que c'est le chiffre qui bouge et rien d'autre.
        #
        # Les valeurs sont posees des le depart a opacite nulle, puis allumees
        # et eteintes tour a tour. Un FadeOut sur un objet pas encore introduit
        # le ferait apparaitre a la premiere image du plan.
        parts = [p.strip() for p in ctr[0]["texte_fr"].split(SPLIT_DOT)]
        t0 = ctr[0]["t_rel_s"]
        span = max(cues.dur - t0 - 1.6, 1.5)
        step = span / max(len(parts) - 1, 1)
        mobs = []
        for p in parts:
            m = _fit(txt(p, SZ_HUGE, INK, weight=SEMIBOLD), FW - 3.0)
            m.move_to(ORIGIN).set_z_index(Z_OVER).set_opacity(0)
            cues.static.append(m)
            mobs.append(m)
            out.add(m)
        for i, m in enumerate(mobs):
            cues.at(cues.late(t0 + i * step, 0.8), _opacity(m, 1), rt=0.6)
            if i + 1 < len(mobs):
                cues.at(cues.late(t0 + (i + 1) * step, 0.8), _opacity(m, 0), rt=0.5)
        return out

    for i, o in enumerate(ctr):
        s = o["texte_fr"]
        y = 0.0 if len(ctr) == 1 else 0.95 - 1.9 * i
        if ARROW in s and len(ctr) == 1:
            # Consequence : la cause, puis la fleche et le resultat.
            left, right = [p.strip() for p in s.split(ARROW, 1)]
            a = txt(left, SZ_BIG, INK_SOFT, weight=SEMIBOLD)
            arr = txt(ARROW, SZ_BIG, MUTED)
            b = txt(right, SZ_BIG, INTEREST, weight=SEMIBOLD)
            row = VGroup(a, arr, b).arrange(RIGHT, buff=0.42)
            _fit(row, FW - 2.2)
            row.move_to([0, y, 0]).set_z_index(Z_OVER)
            cues.at(cues.late(o["t_rel_s"], 1.6), fade_up(a, 0.3), rt=0.55)
            cues.at(cues.late(o["t_rel_s"] + 0.9, 1.0),
                    FadeIn(arr), fade_up(b, 0.3), rt=0.6)
            out.add(row)
        else:
            size = SZ_BIG if len(s) > 22 else SZ_HUGE
            m = _fit(txt(s, size, INK, weight=SEMIBOLD), FW - 2.6)
            m.move_to([0, y, 0]).set_z_index(Z_OVER)
            if visual in ("fond_anime", "broll"):
                sc = _scrim(m)
                out.add(sc)
                cues.at(cues.late(o["t_rel_s"], 0.9), FadeIn(sc), fade_up(m, 0.34), rt=0.6)
            else:
                cues.at(cues.late(o["t_rel_s"], 0.9), fade_up(m, 0.34), rt=0.6)
            out.add(m)
    return out


# =============================================================================
# Ancres exportees
# =============================================================================

def write_anchors(path, sid, component, points):
    """Sxx.anchors.json : les points d'ancrage nommes du plan, en unites Manim
    (origine au centre, y vers le haut) et en pixels du rendu (origine en haut
    a gauche). `rotation` est en degres, sens trigonometrique."""
    w, h = config.pixel_width, config.pixel_height
    out = {}
    for name, (x, y, rot) in points.items():
        out[name] = {"x": round(x, 4), "y": round(y, 4),
                     "px": round((x + FW / 2) / FW * w, 1),
                     "py": round((FH / 2 - y) / FH * h, 1),
                     "rotation": rot}
    doc = {"segment": sid, "composant": component,
           "cadre": {"largeur": FW, "hauteur": FH, "pixels": [w, h]},
           "ancres": out}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
        f.write("\n")


# =============================================================================
# Scene
# =============================================================================

class SegmentScene(Scene):
    """Un plan. `seg` vient de script.json, `dur` du fichier audio rendu."""

    def __init__(self, seg=None, dur=10.0, anchors_path=None, **kw):
        self.seg = seg
        self.dur = float(dur)
        self.anchors_path = anchors_path
        super().__init__(**kw)

    def construct(self):
        seg, dur = self.seg, self.dur
        self.camera.background_color = BG
        self.add(backdrop())

        cues = Cues(dur)
        cues.anchors = {o["ancre"] for o in (seg.get("overlay_texte") or [])}
        visual = seg["type_visuel"]

        family = None
        if visual == "manim":
            from briefs import resolve
            brief_seg, family = resolve(seg, dur)
            art = COMPONENTS[family](brief_seg, cues)
            art.set_z_index(Z_PLOT)
        elif visual == "typo_cinetique":
            self.add(ambience_type(seg))
        elif visual == "broll":
            self.add(ambience_horizon(seg))
        else:
            self.add(ambience_field(seg))

        add_overlays(seg, cues, visual)
        if family and (seg.get("manim_brief") or {}).get("revelations"):
            from briefs import warn_still
            warn_still(brief_seg, [(t, t + rt) for t, _, rt in cues.items], dur)
        if self.anchors_path:
            write_anchors(self.anchors_path, seg["id"], family or visual, cues.points)

        self.add(*cues.static)

        self.run_cues(cues)

    def run_cues(self, cues):
        """Joue tous les reperes sur une seule ligne de temps.

        Chaque repere devient une voie `Succession(Wait(depart), animation)` ;
        toutes les voies partent ensemble dans un `AnimationGroup` sans decalage.
        Un texte pose a 3 s apparait donc bien a 3 s, meme si un balayage de
        barres court encore : c'est ce que le script decrit, et c'est ce qu'un
        enchainement sequentiel ne sait pas rendre.

        Une derniere voie d'attente fixe la duree du plan sur celle de la voix.
        """
        lanes = []
        for start, anims, rt in sorted(cues.items, key=lambda c: c[0]):
            if start >= cues.dur:
                continue
            rt = max(min(rt, cues.dur - start), 0.05)
            for a in anims:
                a.run_time = rt          # a fixer avant d'emballer la voie
                lanes.append(Succession(Wait(start), a) if start > 1e-3 else a)
        lanes.append(Wait(cues.dur))
        self.play(AnimationGroup(*lanes, lag_ratio=0))
