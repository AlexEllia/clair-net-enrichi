# -*- coding: utf-8 -*-
"""Presence du bouton d'abonnement d'un ecran de fin, image par image.

    python video/presence_bouton.py <video> [debut_s] [fin_s]

Dans la zone du bouton (pixels 1920x1080, au-dessus du cercle d'abonnement),
la presence est le nombre de pixels qui different de la premiere image de la
plage (bouton absent) de plus de 18 niveaux, toutes couleurs cumulees : le
fond de l'etat « Abonne » (BG_LIFT) ne s'ecarte du fond de l'ecran que de 28
niveaux, un seuil plus haut le perdrait de vue alors qu'il est la. Le
bouton doit etre absent avant son mot, puis ne jamais disparaitre : apres son
apparition, la presence ne doit jamais tomber sous la moitie de son niveau
d'apparition, ni chuter de plus de 50 % d'une image a la suivante.
"""
import subprocess
import sys

import numpy as np

ZONE = (270, 295, 690, 410)          # x0, y0, x1, y1


def presence(video, debut=0.0, fin=None):
    x0, y0, x1, y1 = ZONE
    w, h = x1 - x0, y1 - y0
    cmd = ["ffmpeg", "-v", "error", "-ss", f"{debut:.3f}"]
    if fin is not None:
        cmd += ["-t", f"{fin - debut:.3f}"]
    cmd += ["-i", str(video), "-vf", f"scale=1920:1080,crop={w}:{h}:{x0}:{y0},format=rgb24",
            "-f", "rawvideo", "-"]
    b = subprocess.run(cmd, capture_output=True).stdout
    f = np.frombuffer(b, np.uint8).reshape(-1, h, w, 3).astype(np.int16)
    ref = f[0]
    return np.array([int((np.abs(x - ref).sum(axis=2) > 18).sum()) for x in f])


def main():
    video = sys.argv[1]
    debut = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
    fin = float(sys.argv[3]) if len(sys.argv) > 3 else None
    p = presence(video, debut, fin)
    fps = 30
    seuil = 0.25 * p.max()
    i0 = int(np.argmax(p > seuil))                      # apparition
    pic = int(p[i0:i0 + 15].max())                      # niveau d'apparition (0,5 s)
    apres = p[i0 + 15:]
    chute = max((p[i - 1] - p[i]) / max(p[i - 1], 1) for i in range(i0 + 1, len(p)))
    print(f"images analysees : {len(p)} ({len(p) / fps:.2f} s)")
    print(f"avant l'apparition : presence max {int(p[:i0].max()) if i0 else 0} pixels")
    print(f"apparition : image {i0} ({debut + i0 / fps:.2f} s), niveau {pic} pixels")
    print(f"apres : presence min {int(apres.min())} pixels ({100 * apres.min() / pic:.0f} % du "
          f"niveau d'apparition), max {int(apres.max())}")
    print(f"plus forte chute d'une image a la suivante : {100 * chute:.0f} %")
    ok = apres.min() >= 0.5 * pic and chute <= 0.5
    print("VERDICT :", "jamais de disparition" if ok else "DISPARITION OU CHUTE")


if __name__ == "__main__":
    main()
