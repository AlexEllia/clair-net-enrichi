# -*- coding: utf-8 -*-
"""Plans de chaine : construits une fois, reutilises a chaque episode.

Deux valeurs de `type_visuel` sans `manim_brief` ni `overlay_texte`, que le
moteur produit seul, parametrees par la seule duree du segment - et calees
sur sa voix quand l'alignement existe (seg["_voix"]) :

  mention     carte de mention legale, deux lignes, chacune sur son mot ;
  ecran_fin   ecran de fin de marque, qui laisse vides les zones ou YouTube
              Studio posera ses elements (video suggeree, abonnement).

Les zones reservees sont donnees en pixels 1920x1080, comme dans YouTube
Studio, et converties ici en unites de scene.
"""

import re

from manim import *
import numpy as np

from style import (BG, BG_LIFT, INK, INK_SOFT, MUTED, RULE, CONTRIB, INTEREST, TEAL,
                   FW, FH, SZ_TITLE, SZ_BODY, SZ_LABEL, SZ_SOURCE, txt)

MENTION = ("Contenu informatif et pédagogique.",
           "Ni conseil en investissement, ni recommandation personnalisée.")
NOM_CHAINE = "Clair net enrichi"
from timeline import ECRAN_FIN_MIN     # duree minimale du plan, prolongation comprise
ZONE_VIDEO = (1340, 540, 830, 467)      # centre x, centre y, largeur, hauteur (px)
ZONE_ABONNEMENT = (480, 600, 300)       # centre x, centre y, diametre (px)
ZONES_VISIBLES = 2.0       # contour des zones : les 2 premieres secondes seulement


def px(x, y):
    """Pixels 1920x1080 (origine en haut a gauche) -> unites de scene."""
    return np.array([(x - 960) / 1920 * FW, (540 - y) / 1080 * FH, 0.0])


def upx(n):
    return n / 1920 * FW


# --- La voix -------------------------------------------------------------------

def _texte(align):
    T = "".join(align["characters"])
    return T, align["character_start_times_seconds"], align["character_end_times_seconds"]


def mot(align, motif, defaut):
    """Instant du premier caractere de `motif` (expression reguliere, sans
    casse) dans la voix ; `defaut` sans alignement ou sans occurrence."""
    if not align:
        return defaut
    T, st, _ = _texte(align)
    m = re.search(motif, T, flags=re.IGNORECASE)
    return st[m.start()] if m else defaut


def premier_mot(align, defaut):
    if not align:
        return defaut
    T, st, _ = _texte(align)
    dans = False
    for i, c in enumerate(T):
        if c == "[":
            dans = True
        elif c == "]":
            dans = False
        elif not dans and c.isalpha():
            return st[i]
    return defaut


# --- mention -------------------------------------------------------------------

def mention(scene, seg, dur, cues):
    """Deux lignes centrees, en blanc casse, chacune en fondu sur son mot :
    la premiere au premier mot de la voix, la seconde au mot « ni ». Rien
    d'autre - une respiration. Si le plan dure encore plus de 4 s apres la
    seconde ligne, le texte derive tres lentement (2 % d'echelle) pour que
    l'ecran ne soit pas fige (R6)."""
    al = seg.get("_voix")
    l1 = txt(MENTION[0], SZ_BODY + 4, INK_SOFT)
    l2 = txt(MENTION[1], SZ_BODY + 4, INK_SOFT)
    for l in (l1, l2):
        if l.width > FW - 2.4:
            l.scale_to_fit_width(FW - 2.4)
    bloc = VGroup(l1, l2).arrange(DOWN, buff=0.42).move_to(ORIGIN)
    t1 = min(premier_mot(al, 0.3), max(dur - 1.0, 0.0))
    t2 = mot(al, r"\bni\b", t1 + 0.4 * max(dur - t1, 1.0))
    t2 = min(max(t2, t1 + 0.6), max(dur - 0.6, t1))
    cues.at(t1, FadeIn(l1, shift=UP * 0.12), rt=0.8)
    cues.at(t2, FadeIn(l2, shift=UP * 0.12), rt=0.8)
    reste = dur - (t2 + 0.8)
    if reste > 4.0:
        # Derive : de 100 % a 102 %, lineaire, de la fin de la seconde ligne
        # a la fin du plan. Rien ne bouge avant.
        t0 = t2 + 0.8
        cues.at(t0, ScaleInPlace(bloc, 1.02, rate_func=linear, introducer=True), rt=reste)
    return {"ligne_1": round(t1, 2), "ligne_2": round(t2, 2),
            "derive": round(t2 + 0.8, 2) if reste > 4.0 else None}


# --- ecran_fin -----------------------------------------------------------------

def _zones():
    cx, cy, w, h = ZONE_VIDEO
    video = Rectangle(width=upx(w), height=upx(h)).move_to(px(cx, cy))
    ax, ay, d = ZONE_ABONNEMENT
    abo = Circle(radius=upx(d) / 2).move_to(px(ax, ay))
    return video, abo


def _derive(m, amp, vitesse, phase):
    home = m.get_center().copy()

    def upd(mob, dt):
        mob.clock = getattr(mob, "clock", phase) + dt * vitesse
        mob.move_to(home + np.array([np.cos(mob.clock) * amp[0],
                                     np.sin(mob.clock * 0.73) * amp[1], 0.0]))
    m.add_updater(upd)
    return m


def bouton(etat):
    """Bouton d'abonnement dessine : ambre « S'abonner », ou estompe
    « Abonne » avec la cloche. Ni logo ni couleur de marque."""
    from pictos import picto
    if etat == "abonner":
        fond = RoundedRectangle(width=3.0, height=0.78, corner_radius=0.39,
                                fill_color=INTEREST, fill_opacity=1, stroke_width=0)
        lab = txt("S'abonner", SZ_BODY, BG, weight=SEMIBOLD)
        return VGroup(fond, lab.move_to(fond))
    fond = RoundedRectangle(width=3.0, height=0.78, corner_radius=0.39,
                            fill_color=BG_LIFT, fill_opacity=1, stroke_color=MUTED,
                            stroke_width=2)
    lab = txt("Abonné", SZ_BODY, INK_SOFT)
    cloche = picto("bell", INK_SOFT, hauteur=0.38)
    rang = VGroup(cloche, lab).arrange(RIGHT, buff=0.22).move_to(fond)
    return VGroup(fond, rang)


def ecran_fin(scene, seg, dur, cues, zones_seules=False):
    """Ecran de fin. `dur` couvre la voix et la prolongation (>= 20 s).

    - zones reservees (video, abonnement) en pointilles les 2 premieres
      secondes, puis vides ;
    - en haut a gauche, « Clair net enrichi » s'ecrit sur ces mots de la voix ;
    - en fond, une courbe qui monte sous les zones, que parcourt un point, et
      des pictogrammes Lucide de Flux (pieces, pousse, hausse) qui derivent
      loin des zones ;
    - sur « abonnez-vous », un bouton dessine au-dessus du cercle s'enfonce
      et passe a « Abonne », avec la cloche.
    Rien n'arrete de bouger jusqu'a la fin, prolongation comprise.
    """
    from pictos import picto
    al = seg.get("_voix")
    video, abo = _zones()

    # Courbe de fond : sous les deux zones, du bas gauche vers la droite.
    xs = np.linspace(-FW / 2 - 0.2, FW / 2 + 0.2, 80)
    ys = -3.72 + 1.62 * np.clip((xs + FW / 2) / FW, 0.0, None) ** 2.2
    courbe = VMobject(stroke_color=INTEREST, stroke_width=4, stroke_opacity=0.55)
    courbe.set_points_smoothly([np.array([x, y, 0.0]) for x, y in zip(xs, ys)])
    aire = VMobject(fill_color=INTEREST, fill_opacity=0.07, stroke_width=0)
    aire.set_points_as_corners([np.array([x, y, 0.0]) for x, y in zip(xs, ys)]
                               + [np.array([xs[-1], -FH / 2 - 0.2, 0]),
                                  np.array([xs[0], -FH / 2 - 0.2, 0])])

    # Pictogrammes : bande haute a droite du nom, et marge gauche, loin des zones.
    places = [("coins", (-0.6, 2.62), INTEREST), ("sprout", (1.7, 2.95), TEAL),
              ("trending-up", (4.0, 2.55), CONTRIB), ("coins", (6.2, 2.9), INTEREST),
              ("sprout", (-6.25, 1.05), TEAL), ("trending-up", (-6.3, -0.95), CONTRIB)]
    icones = VGroup()
    for k, (nom, (x, y), col) in enumerate(places):
        ic = picto(nom, col, hauteur=0.55)
        ic.move_to([x, y, 0]).set_opacity(0.0)
        icones.add(ic)

    titre = txt(NOM_CHAINE, SZ_TITLE + 6, INK, weight=SEMIBOLD)
    titre.move_to(px(0, 0), aligned_edge=UL).shift(RIGHT * 0.75 + DOWN * 0.62)

    b1 = bouton("abonner")
    b2 = bouton("abonne")
    for b in (b1, b2):
        b.move_to(abo.get_top() + UP * 0.72)

    if zones_seules:
        # Image fixe pour YouTube Studio : l'etat final, zones visibles et
        # cotees en pixels.
        for ic in icones:
            for sm in ic.family_members_with_points():
                (sm.set_fill(opacity=0.8) if isinstance(sm, Dot) else sm.set_stroke(opacity=0.8))
        z = VGroup(video.copy().set_stroke(INK, 3).set_fill(INK, 0.06),
                   abo.copy().set_stroke(INK, 3).set_fill(INK, 0.06))
        cx, cy, w, h = ZONE_VIDEO
        ax, ay, d = ZONE_ABONNEMENT
        l1 = VGroup(txt("Vidéo suggérée", SZ_BODY, INK, weight=SEMIBOLD),
                    txt(f"{w} × {h} px, centre ({cx}, {cy})", SZ_SOURCE, INK_SOFT))
        l1.arrange(DOWN, buff=0.18).move_to(video)
        l2 = VGroup(txt("Abonnement", SZ_BODY, INK, weight=SEMIBOLD),
                    txt(f"Ø {d} px, centre ({ax}, {ay})", SZ_SOURCE, INK_SOFT))
        l2.arrange(DOWN, buff=0.12).move_to(abo)
        for lab, zone in ((l1, video), (l2, abo)):
            if lab.width > zone.width * 0.86:
                lab.scale_to_fit_width(zone.width * 0.86)
        scene.add(aire, courbe, icones, titre, b2, z, l1, l2)
        return {}

    contours = VGroup(DashedVMobject(video.copy().set_stroke(MUTED, 2.2, opacity=0.7),
                                     num_dashes=80),
                      DashedVMobject(abo.copy().set_stroke(MUTED, 2.2, opacity=0.7),
                                     num_dashes=40))
    cues.static.append(contours)
    cues.at(ZONES_VISIBLES - 0.5, FadeOut(contours), rt=0.5)

    cues.at(0.0, Create(courbe), FadeIn(aire), rt=2.5)
    point = Dot(radius=0.07, color=INTEREST).set_opacity(0)
    cues.static.append(point)
    tour = 9.0                                 # un passage de gauche a droite
    # Trajet echantillonne une fois, sur la courbe complete : pendant son
    # trace, la courbe n'a pas encore de longueur a parcourir.
    chemin = np.array([np.array([x, y, 0.0]) for x, y in zip(xs, ys)])

    def parcours(m, dt):
        m.clock = getattr(m, "clock", 0.0) + dt
        u = (m.clock / tour) % 1.0
        i = u * (len(chemin) - 1)
        k = min(int(i), len(chemin) - 2)
        m.move_to(chemin[k] + (chemin[k + 1] - chemin[k]) * (i - k))
        m.set_opacity(min(1.0, u / 0.08, (1 - u) / 0.08) if m.clock > 2.5 else 0.0)
    point.add_updater(parcours)

    for k, ic in enumerate(icones):
        _derive(ic, (0.22, 0.16), 0.22 + 0.04 * k, 1.1 * k)
        cues.static.append(ic)
        cues.at(0.6 + 0.35 * k, _opacity_icone(ic, 0.8), rt=1.0)

    t_nom = mot(al, re.escape(NOM_CHAINE), 1.0)
    cues.at(min(t_nom, dur - 2.0), Write(titre), rt=1.6)

    t_abo = mot(al, r"abonnez", 3.0)
    t_abo = min(t_abo, dur - 3.0)
    cues.at(t_abo, FadeIn(b1, scale=0.9), rt=0.5)
    # Clic : le bouton s'enfonce, puis passe a l'etat abonne.
    cues.at(t_abo + 0.9, ScaleInPlace(b1, 0.92, rate_func=there_and_back, introducer=True),
            rt=0.35)
    cues.at(t_abo + 1.35, FadeOut(b1), FadeIn(b2, scale=0.96), rt=0.45)
    cloche = b2[1][0]
    cues.at(t_abo + 1.9, Wiggle(cloche, scale_value=1.15, rotation_angle=0.12 * TAU,
                                introducer=True), rt=0.8)
    return {"nom": round(t_nom, 2), "abonnez": round(t_abo, 2)}


def exporter_zones(dest, media_dir):
    """build/ecran_fin_zones.png : l'ecran de fin dans son etat final, zones
    reservees visibles et cotees en pixels, pour YouTube Studio."""
    import shutil
    from pathlib import Path
    from style import BG

    class Zones(Scene):
        def construct(self):
            self.camera.background_color = BG
            from scenes import backdrop
            self.add(backdrop())
            ecran_fin(self, {"id": "zones"}, ECRAN_FIN_MIN, None, zones_seules=True)

    with tempconfig({"pixel_width": 1920, "pixel_height": 1080, "media_dir": str(media_dir),
                     "output_file": "ecran_fin_zones", "save_last_frame": True,
                     "write_to_movie": False, "disable_caching": True,
                     "verbosity": "ERROR", "progress_bar": "none", "background_color": BG}):
        sc = Zones()
        sc.render()
        png = Path(sc.renderer.file_writer.image_file_path)
    Path(dest).parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(png), str(dest))
    return Path(dest)


class _Opacite(Animation):
    """Opacite d'un pictogramme au trait, de 0 a `cible` : trait pour les
    chemins, remplissage pour les points. Introducteur : l'icone, deja posee
    a opacite nulle, n'est pas reajoutee avant son heure."""

    def __init__(self, m, cible, **kw):
        self.cible = cible
        super().__init__(m, introducer=True, **kw)

    def interpolate_mobject(self, alpha):
        for sm in self.mobject.family_members_with_points():
            if isinstance(sm, Dot):
                sm.set_fill(opacity=alpha * self.cible)
            else:
                sm.set_stroke(opacity=alpha * self.cible)


def _opacity_icone(m, cible):
    return _Opacite(m, cible)
