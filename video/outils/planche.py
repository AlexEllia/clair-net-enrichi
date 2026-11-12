# -*- coding: utf-8 -*-
"""Planche d'images de plans, sans toucher aux rendus de l'episode.

    python video/outils/planche.py DEST EP004:S05 EP004:S12@8.5 EP001c_S02 ...

Chaque plan est rendu en 960x540 dans DEST (dossier de travail) et une image
en est extraite : la derniere par defaut, ou celles des instants donnes apres
`@`, separes par des virgules. `EPxxx:Sxx` rend le segment du script ; `EPxxx_Sxx` rend un plan de
reference comme le fait non_regression.py (brief pilote de video/pilotes/ et
voix figee s'il y en a un). Les images s'appellent DEST/<nom>.png ; la planche,
DEST/planche.png, les range dans l'ordre donne, trois par ligne.
"""
import copy
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def segment(nom):
    import non_regression as nr
    if ":" in nom:
        ep, sid = nom.split(":")
        return nr._segment(ep, sid)
    ep, sid = nom.split("_")
    seg, dur = nr._segment(ep, sid)
    brief = nr._pilot(nom)
    if brief is not None:
        b = json.loads(brief.read_text(encoding="utf-8"))
        seg = copy.deepcopy(seg)
        for k in ("type_visuel", "manim_brief", "overlay_texte"):
            seg[k] = copy.deepcopy(b["remplace"][k])
        seg["_pilote"] = True
        ref = json.loads((ROOT / "reference" / f"{nom}.json").read_text(encoding="utf-8"))
        voix = next((v.get("voix_s") for v in ref.get("versions", [])
                     if v.get("version") == ref.get("courante")), None)
        if voix is not None:
            dur = float(voix)
            seg.pop("_voix", None)
    return seg, dur


def main():
    import build
    import nombres
    nombres.set_locale("fr")
    dest = Path(sys.argv[1]).resolve()
    dest.mkdir(parents=True, exist_ok=True)
    images = []
    for arg in sys.argv[2:]:
        nom, _, quand = arg.partition("@")
        seg, dur = segment(nom)
        seg = dict(seg, id=nom.replace(":", "_"))
        plan = build.render_segment(seg, dur, dest, dest / "_manim", 960, 540)
        for q in (quand.split(",") if quand else [""]):
            t = min(float(q), dur - 0.1) if q else max(dur - 0.1, 0.0)
            png = dest / f"{seg['id']}{'_' + q if q else ''}.png"
            build.sh(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", str(plan),
                      "-frames:v", "1", str(png)])
            images.append(png)
            print(f"{nom}@{q or 'fin'} : {png}", flush=True)
    n = len(images)
    if n > 1:
        cols = min(3, n)
        cases = "|".join(f"{(i % cols) * 960}_{(i // cols) * 540}" for i in range(n))
        cmd = ["ffmpeg", "-y", "-loglevel", "error"]
        for p in images:
            cmd += ["-i", str(p)]
        cmd += ["-filter_complex", f"xstack=inputs={n}:layout={cases}:fill=black",
                str(dest / "planche.png")]
        subprocess.run(cmd, check=True)
        print(f"planche : {dest / 'planche.png'}")


if __name__ == "__main__":
    main()
