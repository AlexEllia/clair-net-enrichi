# -*- coding: utf-8 -*-
"""Decoupe B aux frontieres (milieu de la pause entre dernier caractere d'un segment et premier du suivant),
construit A_actuel (S18-S26 de production + silences du montage) et normalise A et B au meme niveau."""
import json, os, re, subprocess, wave
HERE = os.path.dirname(os.path.abspath(__file__)); EP = os.path.dirname(HERE)
IDS = [f"S{i}" for i in range(18, 27)]
man = {s["id"]: s for s in json.load(open(os.path.join(EP, "tts_manifest.json"), encoding="utf-8"))["segments"]}
dur = json.load(open(os.path.join(EP, "audio", "durations.json"), encoding="utf-8"))
al = json.load(open(os.path.join(HERE, "B_alignement.json"), encoding="utf-8"))
ch, st, en = al["characters"], al["character_start_times_seconds"], al["character_end_times_seconds"]
bloc = "".join(ch)
# position de chaque segment dans le bloc
pos, p = {}, 0
for i in IDS:
    t = man[i]["texte_tts"]; k = bloc.index(t, p); pos[i] = (k, k + len(t)); p = k + len(t)
def parle(a, b):
    """indices des caracteres prononces (lettres/chiffres hors balises) dans [a, b)"""
    out, inb = [], False
    for x in range(a, b):
        c = ch[x]
        if c == "[": inb = True
        if not inb and re.match(r"\w", c): out.append(x)
        if c == "]": inb = False
    return out
info = []
for i in IDS:
    g = parle(*pos[i]); info.append({"id": i, "debut_parole": st[g[0]], "fin_parole": en[g[-1]]})
bornes = [0.0]
for a, b in zip(info, info[1:]):
    pause = b["debut_parole"] - a["fin_parole"]
    a["pause_apres_s"] = round(pause, 3); bornes.append((a["fin_parole"] + b["debut_parole"]) / 2)
total = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                              os.path.join(HERE, "B_bloc_brut.wav")], capture_output=True, text=True).stdout)
bornes.append(total)
os.makedirs(os.path.join(HERE, "B_segments"), exist_ok=True)
for k, i in enumerate(IDS):
    a, b = bornes[k], bornes[k + 1]
    info[k].update({"coupe_debut_s": round(a, 3), "coupe_fin_s": round(b, 3), "duree_fichier_s": round(b - a, 3)})
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", os.path.join(HERE, "B_bloc_brut.wav"),
                    "-ss", f"{a:.4f}", "-to", f"{b:.4f}", "-c:a", "pcm_s16le",
                    os.path.join(HERE, "B_segments", f"{i}.wav")], check=True)
    # alignement du morceau, re-base sur son debut
    a0, a1 = pos[i]
    json.dump({"characters": ch[a0:a1], "character_start_times_seconds": [t - a for t in st[a0:a1]],
               "character_end_times_seconds": [t - a for t in en[a0:a1]]},
              open(os.path.join(HERE, "B_segments", f"{i}.json"), "w", encoding="utf-8"), ensure_ascii=False)
# A_actuel : segments de production + silences du montage entre eux (pas apres S26)
lst = os.path.join(HERE, "_concat_A.txt"); parts = []
for i in IDS:
    parts.append(os.path.join(EP, "audio", f"{i}.wav"))
    s = dur[i]["silence_apres_s"]
    if i != IDS[-1] and s > 0:
        f = os.path.join(HERE, f"_sil_{s:.2f}.wav")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
                        "-t", f"{s}", "-c:a", "pcm_s16le", f], check=True)
        parts.append(f)
open(lst, "w").write("".join(f"file '{x}'\n" for x in parts))
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c:a", "pcm_s16le",
                os.path.join(HERE, "_A_brut.wav")], check=True)
def lufs(p):
    r = subprocess.run(["ffmpeg", "-nostats", "-hide_banner", "-i", p, "-filter_complex", "ebur128=peak=true",
                        "-f", "null", "-"], capture_output=True, text=True, errors="replace").stderr
    s = r[r.rfind("Summary:"):]
    return float(re.search(r"I:\s+(-?[\d.]+) LUFS", s).group(1)), float(re.search(r"Peak:\s+(-?[\d.]+|-inf) dBFS", s).group(1))
CIBLE = -17.0
norm = {}
for nom, src in (("A_actuel", "_A_brut.wav"), ("B_bloc", "B_bloc_brut.wav")):
    i0, tp0 = lufs(os.path.join(HERE, src)); g = CIBLE - i0
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", os.path.join(HERE, src), "-af", f"volume={g:.2f}dB",
                    "-c:a", "pcm_s16le", os.path.join(HERE, f"{nom}.wav")], check=True)
    i1, tp1 = lufs(os.path.join(HERE, f"{nom}.wav"))
    norm[nom] = {"lufs_avant": i0, "gain_db": round(g, 2), "lufs_apres": i1, "crete_vraie_apres_dbtp": tp1}
for f in os.listdir(HERE):
    if f.startswith("_sil_") or f == "_concat_A.txt": os.remove(os.path.join(HERE, f)) if False else None
voixA = sum(dur[i]["duree_audio_s"] for i in IDS)
silA = {i: dur[i]["silence_apres_s"] for i in IDS[:-1]}
json.dump({"segments_B": info, "duree_B_s": round(total, 2), "voix_A_s": round(voixA, 2),
           "silences_A": silA, "duree_A_avec_silences_s": round(voixA + sum(silA.values()), 2),
           "normalisation": norm}, open(os.path.join(HERE, "decoupe.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps({"duree_B": round(total, 2), "voix_A": round(voixA, 2), "A_avec_silences": round(voixA + sum(silA.values()), 2), "norm": norm}, ensure_ascii=False))
for x in info: print(x)
