# -*- coding: utf-8 -*-
"""Pictogrammes de la chaine : Lucide 1.59.0, licence ISC (video/pictos/lucide).

Un pictogramme n'ecrit aucun mot (R7) : c'est un dessin au trait, colore par
le composant. Seuls les fichiers du dossier sont admis ; leur provenance et
leur licence sont dans pictos/lucide/PROVENANCE.md.
"""

from pathlib import Path

from manim import SVGMobject, Dot, VGroup
import numpy as np

DOSSIER = Path(__file__).resolve().parent / "pictos" / "lucide"


def disponibles():
    return sorted(p.stem for p in DOSSIER.glob("*.svg"))


def picto(nom, couleur, hauteur=0.8, epaisseur=None):
    """Le pictogramme `nom`, au trait, a la hauteur demandee (unites Manim).

    Lucide dessine certains points comme des traits de longueur nulle a bout
    rond (« M12 7h.01 ») : un navigateur les rend comme des points, Manim ne
    les rend pas. Ils sont remplaces par de vrais points, du diametre du trait.
    """
    src = DOSSIER / f"{nom}.svg"
    if not src.exists():
        raise SystemExit(f"pictogramme inconnu : {nom!r} (disponibles : "
                         f"{', '.join(disponibles())} - video/pictos/lucide)")
    m = SVGMobject(str(src), fill_opacity=0, stroke_color=couleur)
    # Le dessin Lucide occupe environ 20 unites de sa grille de 24, avec un
    # trait de 2 : un point fait donc ~1/10 de la hauteur dessinee. Trait de
    # 4,5 pour 1 unite de haut, juge a l'ecran sur la planche d'essai.
    m.scale(hauteur / max(m.height, 1e-6))
    larg_trait = epaisseur if epaisseur is not None else max(4.5 * hauteur, 1.6)
    taille_point = hauteur / 10.0
    out = VGroup()
    for sub in m.family_members_with_points():
        if max(sub.width, sub.height) < taille_point * 0.6:
            out.add(Dot(sub.get_center(), radius=taille_point / 2, color=couleur,
                        fill_opacity=1, stroke_width=0))
        else:
            sub.set_fill(opacity=0).set_stroke(couleur, width=larg_trait, opacity=1)
            out.add(sub)
    out.move_to(np.zeros(3))
    return out
