# -*- coding: utf-8 -*-
"""Memes mesures que build/diagnostic/outils/voix.py (ses fonctions sont executees telles quelles,
le fichier n'est pas modifie), appliquees a A (production) et B (bloc), segments S18 a S26."""
import json, os, re, sys, importlib.util
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); EP = os.path.dirname(HERE); ROOT = os.path.dirname(os.path.dirname(EP))
src = open(os.path.join(EP, "build", "diagnostic", "outils", "voix.py"), encoding="utf-8").read()
defs = src.split("script = json.load(")[0]
spec = importlib.util.spec_from_file_location("duree", sys.argv[1]); duree = importlib.util.module_from_spec(spec); spec.loader.exec_module(duree)
ns = {"__name__": "voix_defs", "__file__": os.path.join(EP, "build", "diagnostic", "outils", "voix.py")}
sys_argv = sys.argv; sys.argv = ["voix.py", EP, sys.argv[1]]
exec(compile(defs, "voix.py", "exec"), ns); sys.argv = sys_argv
IDS = [f"S{i}" for i in range(18, 27)]
man = {s["id"]: s["texte_tts"] for s in json.load(open(os.path.join(EP, "tts_manifest.json"), encoding="utf-8"))["segments"]}
def profil(wav, alp, sid):
    x, sr = ns["lire_wav"](wav); lufs, lra, tp = ns["ebur128"](wav)
    f0 = ns["yin"](x, sr); v = f0[~np.isnan(f0)]
    cg, cv = ns["centroide"](x, sr, ~np.isnan(f0))
    al = json.load(open(alp, encoding="utf-8")); t0, t1, art = ns["parole"](al)
    syl = duree.syllabes(man[sid])
    return {"id": sid, "lufs": lufs, "f0": round(float(np.median(v)), 1), "debit": round(syl / (t1 - t0), 3),
            "articulation": round(syl / art, 3), "centroide_voise": round(cv), "duree_fichier": round(len(x) / sr, 2),
            "silence_tete": round(t0, 2), "silence_queue": round(len(x) / sr - t1, 2)}
res = {"A": [], "B": []}
for sid in IDS:
    res["A"].append(profil(os.path.join(EP, "audio", f"{sid}.wav"), os.path.join(EP, "audio", "alignments", f"{sid}.json"), sid))
    res["B"].append(profil(os.path.join(HERE, "B_segments", f"{sid}.wav"), os.path.join(HERE, "B_segments", f"{sid}.json"), sid))
S = ns["SEUIL"]
def jonctions(rows):
    out = []
    for a, b in zip(rows, rows[1:]):
        dv = b["lufs"] - a["lufs"]; dh = 12 * np.log2(b["f0"] / a["f0"])
        dd = 100 * (b["debit"] / a["debit"] - 1); dt = 100 * (b["centroide_voise"] / a["centroide_voise"] - 1)
        n = {"volume": abs(dv) / S["volume"], "hauteur": abs(dh) / S["hauteur"], "debit": abs(dd) / S["debit"], "timbre": abs(dt) / S["timbre"]}
        out.append({"jonction": f"{a['id']}>{b['id']}", "d_volume_lu": round(dv, 2), "d_hauteur_dt": round(float(dh), 2),
                    "d_debit_pct": round(float(dd), 1), "d_timbre_pct": round(float(dt), 1),
                    "score": round(float(np.sqrt(sum(v ** 2 for v in n.values()))), 2), "dominante": max(n, key=n.get)})
    return out
res["jonctions_A"] = jonctions(res["A"]); res["jonctions_B"] = jonctions(res["B"])
json.dump(res, open(os.path.join(HERE, "mesures.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for k in ("A", "B"):
    print(k); [print("  ", r) for r in res[k]]
print("jonctions A / B :")
for a, b in zip(res["jonctions_A"], res["jonctions_B"]):
    print(f"  {a['jonction']}: A score {a['score']} (vol {a['d_volume_lu']}, ht {a['d_hauteur_dt']}, deb {a['d_debit_pct']}, tim {a['d_timbre_pct']}) | B score {b['score']} (vol {b['d_volume_lu']}, ht {b['d_hauteur_dt']}, deb {b['d_debit_pct']}, tim {b['d_timbre_pct']})")
