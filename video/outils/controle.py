# -*- coding: utf-8 -*-
"""Les controles bloquants de make check sur un plan d'essai hors episode.

    python video/outils/controle.py video/outils/essais/flux_nature.json [...]

Meme jugement que `make check`, sans rendu : aucun intervalle de plus de 4 s
sans element nouveau, aucune faute de placement, code couleur de sens (une
perte en NEG avec son signe moins, un gain en ambre avec son signe plus).
Le plan d'essai s'ecrit {"duree_s": ..., "segment": {...}}, comme pour
planche.py. Code de sortie non nul si un plan est refuse. Ne touche a aucun
fichier.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def juger(seg, dur):
    """[fautes] du plan, les trois controles reunis."""
    import build
    from briefs import _gaps, MAX_STILL
    fautes = []
    cal = build.calendrier_nouveaute(seg, dur)
    trous = _gaps(cal, 0.0, dur)
    pire = max(trous, key=lambda g: g[1] - g[0]) if trous else (0.0, 0.0)
    print(f"  element nouveau : {len(cal)} arrivees, plus long intervalle "
          f"{pire[1] - pire[0]:.2f} s (de {pire[0]:.2f} a {pire[1]:.2f} s)")
    fautes += [f"{b - a:.2f} s sans element nouveau, de {a:.2f} a {b:.2f} s"
               for a, b in trous if b - a > MAX_STILL]
    f, n_e, n_l, _ = build.collisions(seg, dur)
    print(f"  placement       : {n_e} encart(s), {n_l} libelle(s), {len(f)} faute(s)")
    fautes += f
    if seg["type_visuel"] == "manim":
        f, remarques, n = build.fautes_sens(seg, dur)
        print(f"  sens            : {n} gain(s) ou perte(s) declare(s), {len(f)} faute(s)")
        for r in remarques:
            print(f"    remarque : {r}")
        fautes += f
    return fautes


def main():
    import nombres
    nombres.set_locale("fr")
    refus = 0
    for nom in sys.argv[1:]:
        essai = json.loads(Path(nom).read_text(encoding="utf-8"))
        seg, dur = essai["segment"], float(essai["duree_s"])
        print(f"{seg['id']} ({dur:.1f} s)")
        try:
            fautes = juger(seg, dur)
        except SystemExit as e:
            fautes = [f"plan non construit - {e}"]
        for x in fautes:
            print(f"  REFUS : {x}")
        print("  controles bloquants : " + ("REFUS" if fautes else "passes"))
        refus += bool(fautes)
    sys.exit(1 if refus else 0)


if __name__ == "__main__":
    main()
