# -*- coding: utf-8 -*-
"""Les plans d'un episode se rendent-ils encore a l'identique ?

    python video/outils/identique.py EP004 DEST [S01 S02 ...]

Chaque plan est re-rendu en 1920x1080 dans DEST (dossier de travail), comme
le fait build.py, et compare au rendu en place (episodes/EPxxx/video/plans/
Sxx.mp4) sur l'empreinte md5 de ses images decodees : identique = chaque
image, pixel pour pixel. Ne touche a aucun fichier de l'episode. A lancer
apres un changement du moteur qui ne doit rien changer aux plans existants.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def empreinte(video):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-map", "0:v",
                        "-f", "md5", "-"], capture_output=True, text=True)
    return r.stdout.strip().replace("MD5=", "")


def main():
    import build
    import nombres
    from briefs import with_voice
    from timeline import load_durations, ajuster
    nombres.set_locale("fr")
    ep_dir = ROOT.parent / "episodes" / sys.argv[1]
    dest = Path(sys.argv[2]).resolve()
    dest.mkdir(parents=True, exist_ok=True)
    seuls = set(sys.argv[3:])
    script = json.loads((ep_dir / "script.json").read_text(encoding="utf-8"))
    durations = ajuster(script, load_durations(ep_dir / "audio" / "durations.json"))
    differents = []
    for seg in script["segments"]:
        sid = seg["id"]
        if seuls and sid not in seuls:
            continue
        ref = ep_dir / "video" / "plans" / f"{sid}.mp4"
        if not ref.exists():
            print(f"{sid} : pas de rendu en place", flush=True)
            continue
        d = durations[sid]
        vit = d.total if seg["type_visuel"] == "ecran_fin" else d.audio
        neuf = build.render_segment(with_voice(seg, ep_dir), vit, dest, dest / "_manim",
                                    1920, 1080)
        a, b = empreinte(ref), empreinte(neuf)
        ok = a == b and a != ""
        if not ok:
            differents.append(sid)
        print(f"{sid} : {'identique' if ok else 'DIFFERENT'}  {a}  {b}", flush=True)
        neuf.unlink(missing_ok=True)
    print("plans differents :", " ".join(differents) or "aucun")


if __name__ == "__main__":
    main()
