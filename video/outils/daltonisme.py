# -*- coding: utf-8 -*-
"""Une image telle que la voit un daltonien.

    python video/outils/daltonisme.py IMAGE.png [deuteranopie|protanopie] [SORTIE.png]

Simulation de Machado, Oliveira et Fernandes (2009), severite 1,0, appliquee
en RGB lineaire. Sortie par defaut : IMAGE_deuteranopie.png a cote de
l'image. Sert a verifier qu'un sens reste lisible sans la couleur (charte,
R10).
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

MACHADO = {
    "deuteranopie": np.array([[0.367322, 0.860646, -0.227968],
                              [0.280085, 0.672501, 0.047413],
                              [-0.011820, 0.042940, 0.968881]]),
    "protanopie": np.array([[0.152286, 1.052583, -0.204868],
                            [0.114503, 0.786281, 0.099216],
                            [-0.003882, -0.048116, 1.051998]]),
}


def simuler(rgb, vue):
    """rgb : tableau (..., 3) en 0..1 (sRGB). Renvoie la meme forme."""
    lin = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    sim = np.clip(lin @ MACHADO[vue].T, 0, 1)
    return np.where(sim <= 0.0031308, 12.92 * sim, 1.055 * sim ** (1 / 2.4) - 0.055)


def main():
    src = Path(sys.argv[1])
    vue = sys.argv[2] if len(sys.argv) > 2 else "deuteranopie"
    dest = Path(sys.argv[3]) if len(sys.argv) > 3 else src.with_name(f"{src.stem}_{vue}.png")
    img = np.asarray(Image.open(src).convert("RGB"), dtype=np.float64) / 255
    out = (simuler(img, vue) * 255 + 0.5).astype(np.uint8)
    Image.fromarray(out).save(dest)
    print(dest)


if __name__ == "__main__":
    main()
