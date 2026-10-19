# -*- coding: utf-8 -*-
"""Simulation, sans rien appliquer : plafonner les pauses naturelles de la voix.

    python video/outils/simuler_plafond.py <dossier_episode> [plafond_s] [--sortie dossier]

Une pause naturelle est l'intervalle entre la derniere lettre (ou chiffre) d'un
mot et la premiere lettre du mot suivant, mesure sur l'alignement de la voix,
y compris d'un segment a l'autre. Les silences ajoutes au montage
(silence_apres_s, aux mid-rolls) ne sont pas naturels : ils sont conserves
et comptes a part. Le plafonnement coupe ce qui depasse le plafond, au milieu
de la pause.

Ecrit pauses.csv et plafond.json dans --sortie (defaut : build/pauses de
l'episode).
"""
import argparse
import csv
import json
import re
from pathlib import Path

ap = argparse.ArgumentParser(description="Simulation du plafonnement des pauses de la voix")
ap.add_argument("episode", type=Path, help="dossier de l'episode (episodes/EPxxx)")
ap.add_argument("plafond", type=float, nargs="?", default=0.9, help="plafond en s (defaut 0,9)")
ap.add_argument("--sortie", type=Path, help="dossier de sortie (defaut : build/pauses)")
args = ap.parse_args()
EP = args.episode.resolve()
PLAFOND = args.plafond
OUT = args.sortie or EP / "build" / "pauses"
OUT.mkdir(parents=True, exist_ok=True)

tl = json.loads((EP / "build" / "timeline.json").read_text(encoding="utf-8"))
segs = tl["segments"]

# Mots de toute la voix, en temps absolu de l'episode.
mots = []
for s in segs:
    al = json.loads((EP / "audio" / "alignments" / f"{s['id']}.json").read_text(encoding="utf-8"))
    ch, st, en = (al["characters"], al["character_start_times_seconds"],
                  al["character_end_times_seconds"])
    texte, dans_balise, cur = "".join(ch), False, None
    for i, c in enumerate(ch):
        if c == "[":
            dans_balise = True
        lettre = (not dans_balise) and bool(re.match(r"\w", c))
        if c == "]":
            dans_balise = False
        if lettre:
            if cur is None:
                cur = {"seg": s["id"], "debut": s["debut_s"] + st[i], "i0": i}
            cur["fin"] = s["debut_s"] + en[i]
            cur["i1"] = i
        elif cur is not None and (c.isspace() or c in "[" or dans_balise):
            cur["mot"] = texte[cur["i0"]:cur["i1"] + 1]
            mots.append(cur)
            cur = None
    if cur is not None:
        cur["mot"] = texte[cur["i0"]:cur["i1"] + 1]
        mots.append(cur)

ajoute = {s["id"]: s["silence_apres_s"] for s in segs}
pauses = []
for a, b in zip(mots, mots[1:]):
    total = b["debut"] - a["fin"]
    sil = ajoute[a["seg"]] if a["seg"] != b["seg"] else 0.0
    naturel = total - sil
    if naturel <= 0.25:
        continue
    pauses.append({"segment": a["seg"] if a["seg"] == b["seg"] else f"{a['seg']}>{b['seg']}",
                   "t_s": round(a["fin"], 2), "apres": a["mot"], "avant": b["mot"],
                   "pause_s": round(naturel, 2), "silence_montage_s": round(sil, 2),
                   "coupe_s": round(max(0.0, naturel - PLAFOND), 2)})

coupe = sum(p["coupe_s"] for p in pauses)
touchees = [p for p in pauses if p["coupe_s"] > 0]


def decale(t):
    """Instant t de l'episode apres plafonnement."""
    return t - sum(p["coupe_s"] for p in touchees if p["t_s"] < t)


def mmss(t):
    return f"{int(t // 60):02d}:{int(t % 60):02d}"


chap_seg = {c["tc"]: (c["segment"], c["titre"], c["debut_s"]) for c in tl["chapitres"]}

with open(OUT / "pauses.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(pauses[0]), delimiter=";")
    w.writeheader()
    w.writerows(pauses)
res = {
    "plafond_s": PLAFOND,
    "duree_actuelle_s": tl["duree_totale_s"],
    "duree_plafonnee_s": round(tl["duree_totale_s"] - coupe, 2),
    "temps_coupe_s": round(coupe, 2),
    "pauses_naturelles_plus_de_0_25_s": len(pauses),
    "pauses_touchees": len(touchees),
    "silences_montage_conserves": [{"apres": s["id"], "s": s["silence_apres_s"]}
                                   for s in segs if s["silence_apres_s"] > 0],
    "chapitres": [{"actuel": tc, "plafonne": mmss(decale(t0)), "segment": sid,
                   "titre": titre} for tc, (sid, titre, t0) in chap_seg.items()],
    "midrolls": [{"actuel": m["tc"], "plafonne": mmss(decale(m["t_s"]))} for m in tl["midrolls"]],
    "touchees": sorted(touchees, key=lambda p: -p["pause_s"]),
}
(OUT / "plafond.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
print(json.dumps({k: v for k, v in res.items() if k != "touchees"}, ensure_ascii=False, indent=1))
print(f"\n{len(touchees)} pauses de plus de {PLAFOND} s :")
for p in sorted(touchees, key=lambda p: p["t_s"]):
    print(f"  {mmss(p['t_s'])}  {p['segment']:<8} {p['pause_s']:5.2f} s -> coupe {p['coupe_s']:4.2f} s"
          f"   « {p['apres']} | {p['avant']} »")
