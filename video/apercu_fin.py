# -*- coding: utf-8 -*-
"""Apercu des plans de chaine `mention` et `ecran_fin`, sur une voix factice.

    python video/apercu_fin.py [--ep EP001c] [--mention 6] [--cta 10]

Aucun segment ni aucune voix reelle : un texte de test, aligne lettre a
lettre a debit constant sur la duree donnee, et une piste son silencieuse.
Rend en 1920x1080 dans episodes/EPxxx/build/apercus/ :

  mention_apercu.mp4     la carte de mention, duree --mention
  ecran_fin_apercu.mp4   l'ecran de fin : --cta de voix, prolonge a 20 s
  ../ecran_fin_zones.png l'image fixe des zones reservees, pour YouTube Studio
"""

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
PROJECT = ROOT.parent

TEXTES = {
    "mention": "Ce contenu est informatif et pédagogique. Il ne constitue ni un conseil en "
               "investissement, ni une recommandation personnalisée.",
    "ecran_fin": "Merci d'avoir suivi Clair net enrichi jusqu'au bout. Si ces chiffres vous "
                 "ont servi, abonnez-vous. Et dites-moi quel chiffre vous a surpris.",
}


def alignement_factice(texte, debut, fin):
    """Chaque caractere recoit une part egale de [debut, fin]."""
    n = len(texte)
    pas = (fin - debut) / n
    return {"characters": list(texte),
            "character_start_times_seconds": [round(debut + i * pas, 3) for i in range(n)],
            "character_end_times_seconds": [round(debut + (i + 1) * pas, 3) for i in range(n)]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ep", default="EP001c")
    ap.add_argument("--mention", type=float, default=6.0)
    ap.add_argument("--cta", type=float, default=10.0)
    a = ap.parse_args()

    import build
    import densite
    from timeline import Duree
    import plans_chaine

    out = PROJECT / "episodes" / a.ep / "build" / "apercus"
    out.mkdir(parents=True, exist_ok=True)
    media = out / "_manim"
    rapport = []
    for kind, voix in (("mention", a.mention), ("ecran_fin", a.cta)):
        total = max(voix, plans_chaine.ECRAN_FIN_MIN) if kind == "ecran_fin" else voix
        seg = {"id": f"apercu_{kind}", "type_visuel": kind,
               "_voix": alignement_factice(TEXTES[kind], 0.25, voix - 0.35)}
        # Le plan anime toute sa duree, prolongation comprise : rien n'est tenu.
        raw = build.render_segment(seg, total, out, media, 1920, 1080)
        image = build.conform(raw, Duree(total, 0.0, total), out / f"{kind}_image.mp4",
                              round(total * build.FPS))
        raw.unlink(missing_ok=True)
        (out / f"{seg['id']}.anchors.json").unlink(missing_ok=True)
        mp4 = out / f"{kind}_apercu.mp4"
        build.sh(["ffmpeg", "-y", "-loglevel", "error", "-i", str(image), "-f", "lavfi",
                  "-i", "anullsrc=r=44100:cl=mono", "-c:v", "copy", "-c:a", "aac",
                  "-b:a", "128k", "-t", f"{total:.3f}", str(mp4)])
        actif, _ = densite.mesurer(image)
        figes = densite.plages(actif, minimum=0.0)
        long_ = max(figes, key=lambda p: p[1]) if figes else (0.0, 0.0)
        image.unlink(missing_ok=True)
        rapport.append(f"{kind}: voix {voix:.1f} s, plan {total:.1f} s"
                       + (f" (prolongation {total - voix:.1f} s de silence)" if total > voix else "")
                       + f" ; plus long intervalle fige {long_[1]:.1f} s a {long_[0]:.1f} s -> {mp4}")

    dest = plans_chaine.exporter_zones(out.parent / "ecran_fin_zones.png", media)
    shutil.rmtree(media, ignore_errors=True)
    print("\n".join(rapport))
    print(f"zones  : {dest}")


if __name__ == "__main__":
    main()
