# -*- coding: utf-8 -*-
"""Planches de livraison : une image par revelation, pour chaque plan rendu.

    python video/outils/planches_revelations.py EP004 [--sortie dossier] [--only S07 S22]

Les instants viennent du calendrier du moteur (build.calendrier_nouveaute,
sans rendu) : la fin de chaque arrivee visible ; deux arrivees qui finissent a
moins de 0,25 s l'une de l'autre donnent une seule image, la derniere. Les
images sont extraites des plans cales de l'episode (video/plans_cales, le
rendu livre), jamais re-rendues. Pour un plan de chaine sans calendrier
(mention, ecran_fin) : une image toutes les 2 s.

Ecrit, dans --sortie (defaut : build/livraison_v2 de l'episode) :
  Sxx.png            la planche du plan, vignettes 640x360 horodatees ;
  Sxx_fin.png        la derniere image du plan, en pleine definition ;
  revelations.json   les instants retenus, plan par plan.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
PROJECT = ROOT.parent
FUSION, COLS, VW, VH = 0.25, 5, 640, 360


def image(plan, t, dest, taille=None):
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.3f}", "-i", str(plan),
           "-frames:v", "1"]
    if taille:
        cmd += ["-vf", f"scale={taille[0]}:{taille[1]}"]
    subprocess.run(cmd + [str(dest)], check=True)


def duree(plan):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", str(plan)], capture_output=True, text=True)
    return float(r.stdout.strip())


def main():
    ap = argparse.ArgumentParser(description="Planches : une image par revelation")
    ap.add_argument("ep")
    ap.add_argument("--sortie", type=Path)
    ap.add_argument("--only", nargs="*")
    args = ap.parse_args()

    import build
    import nombres
    from timeline import load_durations, ajuster
    from PIL import Image, ImageDraw, ImageFont
    nombres.set_locale("fr")

    ep_dir = PROJECT / "episodes" / args.ep
    out = (args.sortie or ep_dir / "build" / "livraison_v2").resolve()
    tmp = out / "_images"
    tmp.mkdir(parents=True, exist_ok=True)
    script = json.loads((ep_dir / "script.json").read_text(encoding="utf-8"))
    durations = ajuster(script, load_durations(ep_dir / "audio" / "durations.json"))
    try:
        police = ImageFont.truetype("arial.ttf", 22)
    except OSError:
        police = ImageFont.load_default()

    bilan = {}
    for seg in script["segments"]:
        sid, visual = seg["id"], seg["type_visuel"]
        if args.only and sid not in args.only:
            continue
        plan = ep_dir / "video" / "plans_cales" / f"{sid}.mp4"
        long_plan = duree(plan)
        if visual in ("mention", "ecran_fin"):
            instants = [round(2.0 * k, 2) for k in range(1, int(long_plan // 2) + 1)]
        else:
            cal = build.calendrier_nouveaute(seg, durations[sid].audio, ep_dir)
            fins = sorted(b for _, b in cal)
            instants = []
            for b in fins:
                if instants and b - instants[-1] < FUSION:
                    instants[-1] = b
                else:
                    instants.append(b)
        # Une image juste apres la fin de l'arrivee, dans les limites du plan.
        instants = [round(min(t + 0.05, long_plan - 0.05), 2) for t in instants]
        instants = sorted(set(instants))
        bilan[sid] = instants
        n = len(instants)
        lignes = (n + COLS - 1) // COLS
        planche = Image.new("RGB", (COLS * VW, lignes * VH), "black")
        for i, t in enumerate(instants):
            png = tmp / f"{sid}_{i:02d}.png"
            image(plan, t, png, (VW, VH))
            v = Image.open(png).convert("RGB")
            d = ImageDraw.Draw(v)
            texte = f"{sid}  {t:.2f} s"
            d.rectangle((0, 0, 14 + d.textlength(texte, font=police), 30), fill=(0, 0, 0))
            d.text((7, 3), texte, fill=(255, 255, 255), font=police)
            planche.paste(v, ((i % COLS) * VW, (i // COLS) * VH))
        planche.save(out / f"{sid}.png")
        image(plan, long_plan - 0.05, out / f"{sid}_fin.png")
        print(f"{sid}  {n:2d} images  {out / (sid + '.png')}", flush=True)
    (out / "revelations.json").write_text(json.dumps(bilan, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
