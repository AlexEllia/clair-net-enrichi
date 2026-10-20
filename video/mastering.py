# -*- coding: utf-8 -*-
"""Mastering de chaine : un gain global sur le mix final pour atteindre la
sonie cible, puis un limiteur true-peak si la crete depasse le plafond.
Parametres : config/charte.json, cle "mastering".

Le gain est le meme sur tout le mix : l'equilibre entre la voix et la musique
ne change pas, rien n'est traite a part. Le limiteur n'agit que la ou la
crete vraie (4x sur-echantillonnee, comme EBU R128) depasserait le plafond :
sa courbe de gain est un minimum glissant (anticipation et maintien de
fenetre_ms) lisse par une moyenne de meme largeur, donc toujours sous le gain
requis au pic, sans saut. Le gain global est ajuste jusqu'a ce que la sonie
mesuree apres limiteur soit a la cible.
"""
import numpy as np
from scipy.ndimage import minimum_filter1d, uniform_filter1d
from scipy.signal import resample_poly

from musique_fin import sonie

BLOC = 1 << 20          # echantillons par bloc de sur-echantillonnage
MARGE = 64              # recouvrement des blocs (filtre de resample_poly)


def crete_vraie(x):
    """Crete vraie par echantillon : max de |x| sur-echantillonne 4x entre
    cet echantillon et le suivant."""
    n, out = len(x), np.empty(len(x))
    for d in range(0, n, BLOC):
        a, b = max(0, d - MARGE), min(n, d + BLOC + MARGE)
        up = np.abs(resample_poly(x[a:b], 4, 1))
        k = d - a
        m = min(BLOC, n - d)
        out[d:d + m] = up[4 * k:4 * (k + m)].reshape(m, 4).max(1)
    return np.maximum(out, np.abs(x))


def courbe_limiteur(x, sr, plafond_dbtp, fenetre_ms):
    seuil = 10 ** (plafond_dbtp / 20)
    tp = crete_vraie(x)
    g = np.minimum(1.0, seuil / np.maximum(tp, 1e-12))
    if g.min() >= 1.0:
        return np.ones(len(x))
    w = 2 * int(round(fenetre_ms / 1000 * sr)) + 1
    lim = np.minimum(1.0, uniform_filter1d(minimum_filter1d(g, w, mode="nearest"), w,
                                           mode="nearest"))
    # La moyenne glissante laisse des residus d'arrondi (0,99999999...) loin
    # de tout pic : hors de l'action du limiteur, le gain est exactement 1.
    lim[lim > 1.0 - 1e-9] = 1.0
    return lim


def masteriser(x, sr, c):
    """(mix masterise, courbe de gain totale, rapport). x : flottants mono."""
    cible, plafond = c["sonie_cible_lufs"], c["crete_max_dbtp"]
    l0, tp0 = sonie(x, sr)
    gain_db, seuil = cible - l0, plafond - c.get("marge_limiteur_db", 0.2)
    for _ in range(8):
        y = x * 10 ** (gain_db / 20)
        lim = courbe_limiteur(y, sr, seuil, c.get("fenetre_limiteur_ms", 10.0))
        z = y * lim
        l, tp = sonie(z, sr)
        if tp > plafond:
            seuil -= tp - plafond + 0.05
            continue
        if abs(l - cible) <= c.get("tolerance_lu", 0.05):
            break
        gain_db += cible - l
    touches = int((lim < 1.0).sum())
    rapport = {"avant_lufs": l0, "avant_dbtp": tp0, "apres_lufs": l, "apres_dbtp": tp,
               "gain_db": round(gain_db, 2), "seuil_limiteur_dbtp": round(seuil, 2),
               "echantillons_limites": touches,
               "part_limitee": round(touches / len(x), 5),
               "reduction_max_db": round(float(20 * np.log10(lim.min())), 2)}
    return z, 10 ** (gain_db / 20) * lim, rapport
