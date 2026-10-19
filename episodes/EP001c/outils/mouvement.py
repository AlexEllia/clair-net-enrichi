"""Mouvement image par image de l'episode monte (lecture seule).

Decode video/EP001c.mp4 a 10 i/s en luminance 480x270 et, pour chaque paire
d'images consecutives, compte les pixels dont la luminance change de plus de
chaque seuil. Ecrit mouvement.npz a cote de ce dossier d'outils.

    python mouvement.py <dossier_episode>
"""
import subprocess
import sys
from pathlib import Path

import numpy as np

EP = Path(sys.argv[1])
OUT = Path(__file__).resolve().parent.parent / "mouvement.npz"
FPS, W, H = 10, 480, 270
SEUILS = (6, 12, 24, 48, 96)

cmd = ["ffmpeg", "-v", "error", "-i", str(EP / "video" / f"{EP.name}.mp4"),
       "-vf", f"fps={FPS},scale={W}:{H}:flags=area,format=gray",
       "-f", "rawvideo", "-"]
p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
taille = W * H
prev = None
lignes = []
moy = []
while True:
    buf = p.stdout.read(taille)
    if len(buf) < taille:
        break
    f = np.frombuffer(buf, np.uint8).reshape(H, W).astype(np.int16)
    moy.append(f.mean())
    if prev is not None:
        d = np.abs(f - prev)
        lignes.append([int((d > s).sum()) for s in SEUILS])
    prev = f
p.wait()
np.savez(OUT, comptes=np.array(lignes, np.int32), seuils=np.array(SEUILS),
         fps=FPS, w=W, h=H, luminance=np.array(moy))
print(f"{len(lignes)} paires -> {OUT}")
