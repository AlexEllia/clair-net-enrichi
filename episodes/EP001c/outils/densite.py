"""Carte de densite visuelle de l'episode monte (lecture seule).

    python densite.py <dossier_episode>

Lit mouvement.npz (ecrit par mouvement.py). Une paire d'images (10 i/s,
480x270) est ACTIVE si au moins MIN_PX pixels changent de plus de SEUIL
niveaux de luminance. Calibre sur l'EP001c : la derive du decor (champ de
points des fonds animes, bandes du b-roll) ne depasse jamais 24 niveaux ; une
apparition, un trace ou un fondu de texte, si. Le decor ne compte donc pas
comme mouvement - meme regle que briefs.py. La colonne `decor_seul` signale
les secondes ou seul le decor bouge.

Ecrit densite_secondes.csv, plages_figees.csv, densite.json et densite.png.
"""
import csv
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

EP = Path(sys.argv[1])
OUT = Path(__file__).resolve().parent.parent
SEUIL, MIN_PX = 24, 20       # evenement visible
SEUIL_DECOR, MIN_DECOR = 6, 3  # derive du decor
FIGE_MAX = 4.0

m = np.load(OUT / "mouvement.npz")
c, seuils, fps = m["comptes"], list(m["seuils"]), int(m["fps"])
actif = c[:, seuils.index(SEUIL)] >= MIN_PX
decor = c[:, seuils.index(SEUIL_DECOR)] >= MIN_DECOR
n = len(actif)

tl = json.load(open(EP / "build" / "timeline.json", encoding="utf-8"))["segments"]
sc = {s["id"]: s for s in json.load(open(EP / "script.json", encoding="utf-8"))["segments"]}


def segment_a(t):
    for s in tl:
        if s["debut_s"] <= t < s["fin_s"]:
            return s
    return tl[-1]


# La paire i couvre l'intervalle [i/fps, (i+1)/fps] ; une plage figee est une
# suite de paires inactives. On coupe aux changements de plan pour attribuer
# chaque plage a un segment (une coupe change de toute facon l'image).
coupes = {int(round(s["debut_s"] * fps)) for s in tl}
plages = []
i = 0
while i < n:
    if actif[i]:
        i += 1
        continue
    j = i
    while j < n and not actif[j] and (j == i or j not in coupes):
        j += 1
    debut, duree = i / fps, (j - i) / fps
    if duree > FIGE_MAX:
        s = segment_a((i + 0.5) / fps)   # coupes a 0,02 s pres d'une image
        plages.append({
            "segment": s["id"], "type_visuel": sc[s["id"]]["type_visuel"],
            "debut_episode_s": round(debut, 1), "debut_segment_s": max(0.0, round(debut - s["debut_s"], 1)),
            "duree_s": round(duree, 1),
            "decor_bouge": bool(decor[i:j].mean() > 0.5),
        })
    i = j

# Secondes de l'episode
secondes = []
for t in range(int(np.ceil(n / fps))):
    a, b = t * fps, min((t + 1) * fps, n)
    s = segment_a(t + 0.5)
    fig = any(p["debut_episode_s"] <= t + 0.5 < p["debut_episode_s"] + p["duree_s"] for p in plages)
    secondes.append({
        "seconde": t, "segment": s["id"], "type_visuel": sc[s["id"]]["type_visuel"],
        "mouvement": int(actif[a:b].any()),
        "decor_seul": int((not actif[a:b].any()) and decor[a:b].any()),
        "dans_plage_figee_4s": int(fig),
        "pixels_max": int(c[a:b, seuils.index(SEUIL)].max()),
    })

# Par segment et par type
par_seg = []
for s in tl:
    a, b = int(round(s["debut_s"] * fps)), int(round(s["fin_s"] * fps))
    dur = (b - a) / fps
    fige = sum(p["duree_s"] for p in plages if p["segment"] == s["id"])
    par_seg.append({
        "segment": s["id"], "role": s["role"], "type_visuel": sc[s["id"]]["type_visuel"],
        "duree_s": round(dur, 2), "fige_4s_s": round(fige, 1),
        "part_fige_4s": round(fige / dur, 3),
        "part_inactive": round(float((~actif[a:b]).mean()), 3),
        "plus_longue_s": max([p["duree_s"] for p in plages if p["segment"] == s["id"]], default=0),
    })
par_seg.sort(key=lambda r: (-r["part_fige_4s"], -r["part_inactive"]))

par_type = {}
for r in par_seg:
    d = par_type.setdefault(r["type_visuel"], {"segments": 0, "duree_s": 0.0, "fige_4s_s": 0.0})
    d["segments"] += 1
    d["duree_s"] += r["duree_s"]
    d["fige_4s_s"] += r["fige_4s_s"]
for d in par_type.values():
    d["duree_s"] = round(d["duree_s"], 1)
    d["fige_4s_s"] = round(d["fige_4s_s"], 1)
    d["part"] = round(d["fige_4s_s"] / d["duree_s"], 3)
total = round(sum(p["duree_s"] for p in plages), 1)
duree_ep = n / fps

for nom, data in (("densite_secondes.csv", secondes), ("plages_figees.csv", plages),
                  ("densite_segments.csv", par_seg)):
    with open(OUT / nom, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(data[0]), delimiter=";")
        w.writeheader()
        w.writerows(data)
json.dump({"critere": {"seuil_luminance": SEUIL, "pixels_min": MIN_PX, "resolution": "480x270",
                       "images_par_s": fps, "fige_au_dela_s": FIGE_MAX},
           "duree_episode_s": round(duree_ep, 1), "total_fige_4s_s": total,
           "part_fige_4s": round(total / duree_ep, 3),
           "part_inactive": round(float((~actif).mean()), 3),
           "par_type": par_type, "segments": par_seg, "plages": plages},
          open(OUT / "densite.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# Image : une ligne par segment, une colonne par dixieme de seconde.
COUL = {"mouvement": (46, 160, 90), "decor": (150, 170, 200), "fige": (225, 225, 225),
        "fige4": (210, 70, 60)}
PX, LH, G = 2, 16, 150
largeur = G + int(max(s["fin_s"] - s["debut_s"] for s in tl) * fps) * PX // 1 + 20
img = Image.new("RGB", (largeur, 30 + LH * len(tl) + 40), "white")
dr = ImageDraw.Draw(img)
try:
    ft = ImageFont.truetype("arial.ttf", 11)
except OSError:
    ft = ImageFont.load_default()
fige4 = np.zeros(n, bool)
for p in plages:
    a = int(round(p["debut_episode_s"] * fps))
    fige4[a:a + int(round(p["duree_s"] * fps))] = True
for k, s in enumerate(tl):
    y = 30 + k * LH
    dr.text((4, y + 2), f"{s['id']} {sc[s['id']]['type_visuel']}", fill="black", font=ft)
    a, b = int(round(s["debut_s"] * fps)), min(int(round(s["fin_s"] * fps)), n)
    for i in range(a, b):
        col = (COUL["mouvement"] if actif[i] else COUL["fige4"] if fige4[i]
               else COUL["decor"] if decor[i] else COUL["fige"])
        x = G + (i - a) * PX
        dr.rectangle([x, y + 2, x + PX - 1, y + LH - 3], fill=col)
    for sec in range(0, int(s["fin_s"] - s["debut_s"]) + 1, 5):
        dr.line([G + sec * fps * PX, y + LH - 2, G + sec * fps * PX, y + LH - 1], fill="black")
dr.text((4, 8), "Vert : mouvement ou apparition.  Rouge : ecran fige > 4 s.  Bleu : seul le decor "
        "derive.  Gris : fige < 4 s.  Graduations : 5 s.", fill="black", font=ft)
img.save(OUT / "densite.png")

print(f"fige > {FIGE_MAX} s : {total} s sur {duree_ep:.1f} s ({100 * total / duree_ep:.1f} %), "
      f"{len(plages)} plages")
for t, d in par_type.items():
    print(f"  {t:15s} {d}")
