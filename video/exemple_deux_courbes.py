# -*- coding: utf-8 -*-
"""Exemple : dix secondes, deux courbes qui entrent l'une apres l'autre.

Un seul segment, ecrit ici comme le script l'ecrirait. Les deux courbes sont
deux parties distinctes de `LineChart` ; la liste `manim_brief.reveals` leur
donne leur top et la duree de leur trace, et les deux legendes arrivent avec
la courbe qu'elles nomment.

    python video/exemple_deux_courbes.py            le calendrier, sans rendu
    python video/exemple_deux_courbes.py --rendu    le mp4, 10 s, 960x540
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

DUREE = 10.0

SEGMENT = {
    "id": "EXEMPLE",
    "type_visuel": "manim",
    "manim_brief": {
        "composant": "LineChart",
        "donnees": [
            {"series": "price_only", "cagr": 5.52},
            {"series": "gross_return", "cagr": 8.81},
            {"start_year": 1987, "end_year": 2026},
        ],
        "axes": {"x": "years", "y": "index value", "unite": "index"},
        "emphase": "one curve drawn, then the other",
        # La premiere courbe se trace seule ; la seconde part une fois qu'elle
        # est finie ; les points d'arrivee ferment le plan. Sans cette liste,
        # les deux traces se chevaucheraient - c'est la cadence par defaut de
        # LineChart, faite pour montrer un ecart se creuser.
        "reveals": [
            {"target": "price_only", "at": 0.8, "run_time": 3.2},
            {"target": "gross_return", "at": 4.4, "run_time": 3.2},
            {"target": "values", "at": 8.0},
        ],
    },
    "overlay_texte": [
        {"ancre": "legende", "t_rel_s": 1.0, "texte_fr": "Sans les dividendes"},
        {"ancre": "legende", "t_rel_s": 4.6, "texte_fr": "Dividendes réinvestis"},
    ],
    "sources": [],
}


def calendrier():
    """Les reperes retenus pour ce plan, sans rien rendre."""
    from components import COMPONENTS, Cues
    from scenes import add_overlays

    cues = Cues(DUREE)
    cues.anchors = {o["ancre"] for o in SEGMENT["overlay_texte"]}
    COMPONENTS[SEGMENT["manim_brief"]["composant"]](SEGMENT, cues)
    add_overlays(SEGMENT, cues, SEGMENT["type_visuel"])
    return sorted((round(t, 2), round(rt, 2)) for t, _, rt in cues.items)


def _libelles():
    """Ce que chaque top porte, pour se relire."""
    noms = {"values": "les points d'arrivée"}
    out = {}
    for e in SEGMENT["manim_brief"]["reveals"]:
        cible = e["target"]
        out[round(float(e["at"]), 2)] = noms.get(cible, f"courbe {cible}")
    for o in SEGMENT["overlay_texte"]:
        out[round(float(o["t_rel_s"]), 2)] = f"légende « {o['texte_fr']} »"
    return out


def montrer(largeur=60):
    """Une reglette de dix secondes, un trait par repere."""
    libelles = _libelles()
    ech = largeur / DUREE
    print(f"\nplan de {DUREE:.0f} s, composant {SEGMENT['manim_brief']['composant']}\n")
    print(" " * 8 + "0s" + " " * (largeur - 6) + f"{DUREE:.0f}s")
    print(" " * 8 + "+" + "-" * (largeur - 2) + "+")
    for t, rt in calendrier():
        a, b = int(t * ech), max(int((t + rt) * ech), int(t * ech) + 1)
        trait = " " * a + "#" * (b - a)
        print(f"{t:6.2f}s  {trait[:largeur]:<{largeur}}  "
              f"{libelles.get(t, '')} ({rt:.1f} s)")
    print()


def rendu():
    """Le mp4. Volontairement hors du chemin par defaut : rien ne se rend
    tant qu'on ne le demande pas."""
    from manim import tempconfig
    from scenes import SegmentScene
    from style import BG

    with tempconfig({"pixel_width": 960, "pixel_height": 540, "frame_rate": 30,
                     "media_dir": str(HERE / "media_exemple"),
                     "output_file": "exemple_deux_courbes",
                     "disable_caching": True, "flush_cache": True,
                     "verbosity": "ERROR", "progress_bar": "none",
                     "background_color": BG}):
        scene = SegmentScene(seg=SEGMENT, dur=DUREE)
        scene.render()
        print("rendu :", scene.renderer.file_writer.movie_file_path)


if __name__ == "__main__":
    rendu() if "--rendu" in sys.argv else montrer()
