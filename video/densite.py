# -*- coding: utf-8 -*-
"""Ce que voit le spectateur : l'ecran bouge-t-il ? Mesure en pixels.

Une video (un plan ou l'episode monte) est decodee a 10 images/s en luminance
480 x 270. Une image est ACTIVE si au moins MIN_PX pixels y changent de plus
de SEUIL niveaux par rapport a la precedente. Une plage figee est une suite
d'images inactives ; au-dela de MAX_STILL, c'est un temps mort.

Calibre sur l'EP001c (diagnostic du 17/10/2026) :
- la derive du decor - champ de points des fonds animes, bandes du b-roll -
  ne depasse jamais 24 niveaux a cette resolution : elle ne compte pas comme
  mouvement, comme dans briefs.py ;
- une apparition, un trace, un fondu de texte, si. Mais un fondu adouci sur
  un petit chiffre ne franchit le seuil qu'a ~20 % d'opacite, 0,4 a 0,5 s
  apres son depart : la mesure en pixels voit les temps morts un peu plus
  longs que le calendrier (S09 : 4,1 s mesures, 3,56 s au calendrier). C'est
  voulu : on mesure ce qui se voit, pas ce qui est programme.
A 960 x 540, la derive des bandes du b-roll franchit le seuil : ne pas
augmenter la resolution sans recalibrer.
"""

import json
import subprocess
from pathlib import Path

import numpy as np

FPS, W, H = 10, 480, 270
SEUIL, MIN_PX = 24, 20           # evenement visible
SEUIL_DECOR, MIN_DECOR = 6, 3    # derive du decor seule
MAX_STILL = 4.0


def mesurer(video):
    """(actif, decor) : deux tableaux booleens, une valeur par paire d'images
    consecutives, la paire i couvrant [i/FPS, (i+1)/FPS]."""
    cmd = ["ffmpeg", "-v", "error", "-i", str(video),
           "-vf", f"fps={FPS},scale={W}:{H}:flags=area,format=gray",
           "-f", "rawvideo", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    taille, prev, actif, decor = W * H, None, [], []
    while True:
        buf = p.stdout.read(taille)
        if len(buf) < taille:
            break
        f = np.frombuffer(buf, np.uint8).reshape(H, W).astype(np.int16)
        if prev is not None:
            d = np.abs(f - prev)
            actif.append(int((d > SEUIL).sum()) >= MIN_PX)
            decor.append(int((d > SEUIL_DECOR).sum()) >= MIN_DECOR)
        prev = f
    p.wait()
    return np.array(actif, bool), np.array(decor, bool)


def plages(actif, coupes=(), minimum=MAX_STILL):
    """[(debut_s, duree_s)] des suites d'images inactives de plus de `minimum`,
    coupees aux indices de `coupes` (changements de plan)."""
    coupes, out, n, i = set(coupes), [], len(actif), 0
    while i < n:
        if actif[i]:
            i += 1
            continue
        j = i
        while j < n and not actif[j] and (j == i or j not in coupes):
            j += 1
        if (j - i) / FPS > minimum:
            out.append((i / FPS, (j - i) / FPS))
        i = j
    return out


def plages_plan(video, debut=0.0, fin=None):
    """Temps morts d'un plan, en secondes depuis son debut. Avec `debut` et
    `fin` : seulement ceux qui commencent dans [debut, fin] (fenetre R6)."""
    actif, _ = mesurer(video)
    out = plages(actif)
    if fin is not None:
        out = [(a, d) for a, d in out if debut - 1e-6 <= a <= fin]
    return out


# --- Carte d'un episode ou d'un plan ------------------------------------------

def carte(video, segments, dest, nom="densite"):
    """Carte de densite : une ligne par segment, seconde par seconde.

    `segments` : [{"id", "type_visuel", "debut_s", "fin_s"}] (timeline, ou un
    seul plan qui commence a 0). Ecrit <nom>.json, <nom>_secondes.csv,
    <nom>_plages.csv et <nom>.png dans `dest`. Renvoie le resume (dict)."""
    import csv
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    actif, decor = mesurer(video)
    n = len(actif)

    def seg_a(t):
        for s in segments:
            if s["debut_s"] <= t < s["fin_s"]:
                return s
        return segments[-1]

    coupes = [int(round(s["debut_s"] * FPS)) for s in segments]
    figes = []
    for a, d in plages(actif, coupes):
        # Coupes a 0,02 s pres d'une image : on attribue par le milieu de la
        # premiere image de la plage.
        s = seg_a(a + 0.5 / FPS)
        figes.append({"segment": s["id"], "type_visuel": s["type_visuel"],
                      "debut_s": round(a, 1),
                      "debut_segment_s": max(0.0, round(a - s["debut_s"], 1)),
                      "duree_s": round(d, 1)})
    fige4 = np.zeros(n, bool)
    for p in figes:
        a = int(round(p["debut_s"] * FPS))
        fige4[a:a + int(round(p["duree_s"] * FPS))] = True

    secondes = []
    for t in range(int(np.ceil(n / FPS))):
        a, b = t * FPS, min((t + 1) * FPS, n)
        s = seg_a(t + 0.5)
        secondes.append({"seconde": t, "segment": s["id"], "type_visuel": s["type_visuel"],
                         "mouvement": int(actif[a:b].any()),
                         "decor_seul": int(not actif[a:b].any() and decor[a:b].any()),
                         "dans_plage_figee": int(fige4[a:b].any())})
    par_seg = []
    for s in segments:
        a, b = int(round(s["debut_s"] * FPS)), min(int(round(s["fin_s"] * FPS)), n)
        f = sum(p["duree_s"] for p in figes if p["segment"] == s["id"])
        par_seg.append({"segment": s["id"], "type_visuel": s["type_visuel"],
                        "duree_s": round((b - a) / FPS, 2), "fige_s": round(f, 1),
                        "part_fige": round(f / max((b - a) / FPS, 1e-6), 3),
                        "part_inactive": round(float((~actif[a:b]).mean()) if b > a else 0, 3)})
    total = round(sum(p["duree_s"] for p in figes), 1)
    resume = {"critere": {"resolution": f"{W}x{H}", "images_par_s": FPS, "seuil": SEUIL,
                          "pixels_min": MIN_PX, "fige_au_dela_s": MAX_STILL},
              "duree_s": round(n / FPS, 1), "total_fige_s": total,
              "part_fige": round(total / max(n / FPS, 1e-6), 3),
              "segments": par_seg, "plages": figes}
    (dest / f"{nom}.json").write_text(json.dumps(resume, ensure_ascii=False, indent=1),
                                      encoding="utf-8")
    for suffixe, rows in (("secondes", secondes), ("plages", figes)):
        with open(dest / f"{nom}_{suffixe}.csv", "w", newline="", encoding="utf-8") as f:
            cols = list(rows[0]) if rows else ["segment", "debut_s", "duree_s"]
            w = csv.DictWriter(f, fieldnames=cols, delimiter=";")
            w.writeheader()
            w.writerows(rows)
    _image(actif, decor, fige4, segments, dest / f"{nom}.png")
    return resume


def _image(actif, decor, fige4, segments, path):
    from PIL import Image, ImageDraw, ImageFont
    vert, rouge, bleu, gris = (46, 160, 90), (210, 70, 60), (150, 170, 200), (225, 225, 225)
    PX, LH, G = 2, 16, 150
    n = len(actif)
    plus_long = max(s["fin_s"] - s["debut_s"] for s in segments)
    img = Image.new("RGB", (G + int(plus_long * FPS) * PX + 20, 30 + LH * len(segments) + 10),
                    "white")
    dr = ImageDraw.Draw(img)
    try:
        ft = ImageFont.truetype("arial.ttf", 11)
    except OSError:
        ft = ImageFont.load_default()
    dr.text((4, 8), "Vert : mouvement.  Rouge : fige > 4 s.  Bleu : seul le decor derive.  "
            "Gris : fige < 4 s.  Graduations : 1 s (longues : 5 s).", fill="black", font=ft)
    for k, s in enumerate(segments):
        y = 30 + k * LH
        dr.text((4, y + 2), f"{s['id']} {s['type_visuel']}", fill="black", font=ft)
        a, b = int(round(s["debut_s"] * FPS)), min(int(round(s["fin_s"] * FPS)), n)
        for i in range(a, b):
            col = vert if actif[i] else rouge if fige4[i] else bleu if decor[i] else gris
            x = G + (i - a) * PX
            dr.rectangle([x, y + 2, x + PX - 1, y + LH - 3], fill=col)
        for sec in range(0, int(s["fin_s"] - s["debut_s"]) + 1):
            x = G + sec * FPS * PX
            dr.line([x, y + LH - (4 if sec % 5 else 7), x, y + LH - 1], fill="black")
    img.save(path)
