# -*- coding: utf-8 -*-
"""Synchronisation de la fin (plans de chaine mention et ecran_fin) mesuree
dans la video montee.

    python video/outils/sync_fin.py <dossier_episode> [--video chemin.mp4]

Les deux plans sont reperes par leur `type_visuel` dans script.json ; la video
par defaut est video/<episode>.mp4. Lit build/timeline.json et les
alignements de audio/alignments/.

Pour chaque element, une zone de l'image (pixels 1920x1080, gabarit de
plans_chaine.py) et le mot de la voix qui doit le declencher. L'instant
mesure est la premiere image ou la zone change nettement (au moins 40 pixels
de plus de 24 niveaux par rapport a l'image d'avant), apres le debut du
segment - ou apres un instant donne. Tolerance : 0,3 s. L'enfoncement du
bouton 0,9 s apres « abonnez-vous » est voulu (plans_chaine.py) : il sort
donc de la tolerance.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

NOM_CHAINE = "Clair net enrichi"            # plans_chaine.NOM_CHAINE
TOLERANCE = 0.3
# Zones de mesure (x0, y0, x1, y1), pixels 1920x1080.
ZONE_MENTION_1 = (300, 445, 1620, 515)
ZONE_MENTION_2 = (150, 565, 1770, 635)
ZONE_NOM = (80, 60, 820, 180)
ZONE_BOUTON = (260, 290, 700, 420)


def images_par_s(video):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=r_frame_rate", "-of", "csv=p=0", str(video)],
                       capture_output=True, text=True).stdout.strip()
    n, d = r.split("/")
    return float(n) / float(d)


class Mesure:
    def __init__(self, ep, video):
        self.ep, self.video = ep, video
        self.fps = images_par_s(video)
        self.tl = {r["id"]: r for r in json.load(
            open(ep / "build" / "timeline.json", encoding="utf-8"))["segments"]}

    def _al(self, sid):
        return json.load(open(self.ep / "audio" / "alignments" / f"{sid}.json", encoding="utf-8"))

    def mot(self, sid, motif):
        al = self._al(sid)
        m = re.search(motif, "".join(al["characters"]), flags=re.IGNORECASE)
        if m is None:
            sys.exit(f"{sid} : « {motif} » absent de l'alignement")
        return self.tl[sid]["debut_s"] + al["character_start_times_seconds"][m.start()]

    def premier_mot(self, sid):
        al = self._al(sid)
        dans = False
        for i, c in enumerate(al["characters"]):
            if c == "[":
                dans = True
            elif c == "]":
                dans = False
            elif not dans and c.isalpha():
                return self.tl[sid]["debut_s"] + al["character_start_times_seconds"][i]

    def onset(self, box, t_from, t_to, apres=None):
        x0, y0, x1, y1 = box
        w, h = x1 - x0, y1 - y0
        cmd = ["ffmpeg", "-v", "error", "-ss", f"{t_from:.3f}", "-t", f"{t_to - t_from:.3f}",
               "-i", str(self.video), "-vf",
               f"crop={w}:{h}:{x0}:{y0},format=gray", "-f", "rawvideo", "-"]
        b = subprocess.run(cmd, capture_output=True).stdout
        f = np.frombuffer(b, np.uint8).reshape(-1, h, w).astype(np.int16)
        for i in range(1, len(f)):
            t = t_from + i / self.fps
            if apres is not None and t < apres:
                continue
            if int((np.abs(f[i] - f[i - 1]) > 24).sum()) >= 40:
                return round(t, 3)
        return None


def segment_de_type(ep, type_visuel):
    ids = [s["id"] for s in json.load(open(ep / "script.json", encoding="utf-8"))["segments"]
           if s.get("type_visuel") == type_visuel]
    if len(ids) != 1:
        sys.exit(f"script.json : {len(ids)} segment(s) de type {type_visuel}, il en faut un")
    return ids[0]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("episode", type=Path, help="dossier de l'episode (episodes/EPxxx)")
    ap.add_argument("--video", type=Path, help="video montee (defaut : video/<episode>.mp4)")
    a = ap.parse_args()
    ep = a.episode.resolve()
    video = a.video or ep / "video" / f"{ep.name}.mp4"
    if not video.exists():
        sys.exit(f"video absente : {video}")
    m = Mesure(ep, video)
    sm, sf = segment_de_type(ep, "mention"), segment_de_type(ep, "ecran_fin")
    mention, fin = m.tl[sm], m.tl[sf]

    w1 = m.premier_mot(sm)
    w2 = m.mot(sm, r"\bni\b")
    m1 = m.onset(ZONE_MENTION_1, mention["debut_s"], mention["fin_s"])
    m2 = m.onset(ZONE_MENTION_2, mention["debut_s"], mention["fin_s"])
    wn = m.mot(sf, re.escape(NOM_CHAINE))
    mn = m.onset(ZONE_NOM, fin["debut_s"], fin["fin_s"])
    wa = m.mot(sf, r"abonnez")
    ma = m.onset(ZONE_BOUTON, fin["debut_s"], fin["fin_s"])
    mp = m.onset(ZONE_BOUTON, fin["debut_s"], fin["fin_s"], apres=(ma or wa) + 0.6)

    lignes = []
    for nom, w_, m_ in (("Mention, ligne 1 (premier mot)", w1, m1),
                        ("Mention, ligne 2 (« ni »)", w2, m2),
                        (f"Ecriture de « {NOM_CHAINE} »", wn, mn),
                        ("Bouton : apparition (« abonnez-vous »)", wa, ma),
                        ("Bouton : enfoncement (« abonnez-vous »)", wa, mp)):
        ecart = None if m_ is None else round(m_ - w_, 3)
        ok = ecart is not None and abs(ecart) <= TOLERANCE
        lignes.append(f"| {nom} | {w_:.3f} s | {m_ if m_ is None else f'{m_:.3f} s'} | "
                      f"{ecart if ecart is None else f'{ecart:+.3f} s'} | {'oui' if ok else 'NON'} |")
    print(f"{ep.name} : mention {sm}, ecran de fin {sf}, {video.name} a {m.fps:g} i/s")
    print("| Element | Mot dans l'alignement | Mesure dans la video | Ecart | <= 0,3 s |")
    print("|---|---|---|---|---|")
    print("\n".join(lignes))


if __name__ == "__main__":
    main()
