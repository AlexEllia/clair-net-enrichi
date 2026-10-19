# -*- coding: utf-8 -*-
"""Profil de voix par segment et ecarts aux jonctions (lecture seule).

    python video/outils/voix.py <dossier_episode> <chemin_duree.py> [--sortie dossier]

<chemin_duree.py> : outils/duree.py de la skill de redaction (syllabes()).

Pour chaque audio/Sxx.wav :
- volume integre (LUFS, EBU R128) et crete vraie (dBTP), par le filtre ebur128
  de ffmpeg ; crete echantillon (dBFS) en complement ;
- F0 par YIN (fenetre 40 ms, pas 10 ms, 70-450 Hz), trames voisees seulement :
  mediane en Hz et dispersion en demi-tons (ecart interquartile et ecart-type) ;
- debit : syllabes de duree.py (meme decoupage que la calibration de la skill)
  divisees par la duree de parole, du premier au dernier caractere aligne ;
  debit d'articulation en complement (pauses de plus de 250 ms retirees) ;
- timbre : centroide spectral moyen des trames voisees (le centroide de toutes
  les trames actives, > -35 dB sous le max, est garde en complement).

Ecrit voix_segments.csv, voix_jonctions.csv et voix.json dans --sortie
(defaut : build/diagnostic de l'episode).
"""
import argparse
import csv
import importlib.util
import json
import re
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

ap = argparse.ArgumentParser(description="Profil de voix par segment et ecarts aux jonctions")
ap.add_argument("episode", type=Path, help="dossier de l'episode (episodes/EPxxx)")
ap.add_argument("duree", type=Path, help="duree.py de la skill (syllabes())")
ap.add_argument("--sortie", type=Path, help="dossier de sortie (defaut : build/diagnostic)")
args = ap.parse_args()
EP = args.episode.resolve()
if not args.duree.exists():
    sys.exit(f"duree.py absent : {args.duree}")
spec = importlib.util.spec_from_file_location("duree", args.duree)
duree = importlib.util.module_from_spec(spec)
spec.loader.exec_module(duree)
OUT = args.sortie or EP / "build" / "diagnostic"
OUT.mkdir(parents=True, exist_ok=True)

# Seuils de perception retenus pour normaliser les ecarts aux jonctions.
SEUIL = {"volume": 1.5,      # LU : seuil donne par Alexandre
         "hauteur": 1.0,     # demi-ton de F0 mediane
         "debit": 10.0,      # % de syllabes/s (variation naturelle ~7 %)
         "timbre": 10.0}     # % de centroide spectral


def lire_wav(p):
    with wave.open(str(p)) as w:
        sr, n, ch = w.getframerate(), w.getnframes(), w.getnchannels()
        x = np.frombuffer(w.readframes(n), np.int16).astype(np.float64) / 32768
    if ch > 1:
        x = x.reshape(-1, ch).mean(1)
    return x, sr


def ebur128(p):
    r = subprocess.run(["ffmpeg", "-nostats", "-hide_banner", "-i", str(p), "-filter_complex",
                        "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True, errors="replace").stderr
    resume = r[r.rfind("Summary:"):]
    i = float(re.search(r"I:\s+(-?[\d.]+) LUFS", resume).group(1))
    lra = float(re.search(r"LRA:\s+(-?[\d.]+) LU", resume).group(1))
    tp = float(re.search(r"Peak:\s+(-?[\d.]+|-inf) dBFS", resume).group(1))
    return i, lra, tp


def yin(x, sr, fmin=70, fmax=450, win=0.04, hop=0.01, seuil=0.15):
    """F0 par trame (NaN si non voisee). YIN classique, sans interpolation fine."""
    N, H = int(win * sr), int(hop * sr)
    tmin, tmax = int(sr / fmax), int(sr / fmin)
    rms_all = []
    f0 = []
    for s in range(0, len(x) - N - tmax, H):
        fr = x[s:s + N + tmax]
        rms_all.append(np.sqrt(np.mean(fr[:N] ** 2)) + 1e-12)
        # difference function via FFT
        a = fr[:N]
        energie = np.cumsum(np.concatenate([[0], fr ** 2]))
        n_fft = 1 << int(np.ceil(np.log2(len(fr) + N)))
        corr = np.fft.irfft(np.fft.rfft(fr, n_fft) * np.conj(np.fft.rfft(a, n_fft)), n_fft)
        taus = np.arange(tmax + 1)
        d = energie[N] + (energie[taus + N] - energie[taus]) - 2 * corr[:tmax + 1]
        d[0] = 0
        cm = np.ones_like(d)
        cs = np.cumsum(d[1:])
        cm[1:] = d[1:] * np.arange(1, tmax + 1) / np.where(cs == 0, 1, cs)
        tau = None
        for t in range(tmin, tmax):
            if cm[t] < seuil:
                while t + 1 < tmax and cm[t + 1] < cm[t]:
                    t += 1
                tau = t
                break
        if tau is None:
            f0.append(np.nan)
            continue
        # interpolation parabolique
        if 1 <= tau < tmax:
            y0, y1, y2 = cm[tau - 1], cm[tau], cm[tau + 1]
            den = y0 - 2 * y1 + y2
            tau = tau + (0.5 * (y0 - y2) / den if den else 0)
        f0.append(sr / tau)
    f0, rms = np.array(f0), np.array(rms_all)
    gate = rms > rms.max() * 10 ** (-35 / 20)
    f0[~gate] = np.nan
    return f0


def centroide(x, sr, voise, win=2048):
    """(centroide moyen des trames actives, centroide moyen des trames voisees).

    Pas de 10 ms, cale sur la grille de yin() : la trame i des deux analyses
    commence au meme echantillon. Le second chiffre ecarte les fricatives
    (s, ch, f), dont la proportion depend du texte et non de la voix.
    """
    hop = int(0.01 * sr)
    w = np.hanning(win)
    freqs = np.fft.rfftfreq(win, 1 / sr)
    cents, en = [], []
    for s in range(0, len(x) - win, hop):
        sp = np.abs(np.fft.rfft(x[s:s + win] * w))
        e = sp.sum()
        en.append(np.sqrt(np.mean(x[s:s + win] ** 2)))
        cents.append((freqs * sp).sum() / e if e > 0 else 0)
    cents, en = np.array(cents), np.array(en)
    actif = en > en.max() * 10 ** (-35 / 20)
    n = min(len(cents), len(voise))
    v = voise[:n] & actif[:n]
    return float(cents[actif].mean()), float(cents[:n][v].mean())


def parole(al):
    """(debut, fin, duree_articulation) depuis l'alignement, balises exclues."""
    ch = al["characters"]
    st, en = al["character_start_times_seconds"], al["character_end_times_seconds"]
    garde, dans_balise = [], False
    for i, c in enumerate(ch):
        if c == "[":
            dans_balise = True
        if not dans_balise and c.strip() and re.match(r"\w", c):
            garde.append(i)
        if c == "]":
            dans_balise = False
    t0, t1 = st[garde[0]], en[garde[-1]]
    pauses = 0.0
    for a, b in zip(garde, garde[1:]):
        trou = st[b] - en[a]
        if trou > 0.25:
            pauses += trou
    return t0, t1, (t1 - t0) - pauses


script = json.load(open(EP / "script.json", encoding="utf-8"))
manif = {s["id"]: s for s in json.load(open(EP / "tts_manifest.json", encoding="utf-8"))["segments"]}
tl = {s["id"]: s for s in json.load(open(EP / "build" / "timeline.json", encoding="utf-8"))["segments"]}

rows = []
for seg in script["segments"]:
    sid = seg["id"]
    wav = EP / "audio" / f"{sid}.wav"
    x, sr = lire_wav(wav)
    lufs, lra, tp = ebur128(wav)
    f0 = yin(x, sr)
    v = f0[~np.isnan(f0)]
    st = 12 * np.log2(v / np.median(v))
    cg, cv = centroide(x, sr, ~np.isnan(f0))
    t_tts = manif[sid]["texte_tts"]
    balise = (re.match(r"\s*\[([^\]]+)\]", t_tts) or [None, ""])[1]
    syl = duree.syllabes(t_tts)
    al = json.load(open(EP / "audio" / "alignments" / f"{sid}.json", encoding="utf-8"))
    t0, t1, art = parole(al)
    rows.append({
        "id": sid, "role": seg["role"], "type_visuel": seg["type_visuel"], "balise": balise,
        "duree_s": round(len(x) / sr, 2),
        "lufs": lufs, "lra_lu": lra, "crete_vraie_dbtp": tp,
        "crete_dbfs": round(20 * np.log10(np.abs(x).max()), 2),
        "f0_mediane_hz": round(float(np.median(v)), 1),
        "f0_iqr_dt": round(float(np.percentile(st, 75) - np.percentile(st, 25)), 2),
        "f0_ecart_type_dt": round(float(st.std()), 2),
        "part_voisee": round(len(v) / len(f0), 3),
        "syllabes": syl, "parole_s": round(t1 - t0, 2),
        "debit_syl_s": round(syl / (t1 - t0), 3),
        "articulation_syl_s": round(syl / art, 3),
        "centroide_hz": round(cg, 0),
        "centroide_voise_hz": round(cv, 0),
    })
    print(sid, rows[-1]["lufs"], rows[-1]["f0_mediane_hz"], rows[-1]["debit_syl_s"],
          rows[-1]["centroide_hz"], rows[-1]["centroide_voise_hz"], flush=True)

jonctions = []
for a, b in zip(rows, rows[1:]):
    dv = b["lufs"] - a["lufs"]
    dh = 12 * np.log2(b["f0_mediane_hz"] / a["f0_mediane_hz"])
    dd = 100 * (b["debit_syl_s"] / a["debit_syl_s"] - 1)
    dt = 100 * (b["centroide_voise_hz"] / a["centroide_voise_hz"] - 1)
    dtg = 100 * (b["centroide_hz"] / a["centroide_hz"] - 1)
    norm = {"volume": abs(dv) / SEUIL["volume"], "hauteur": abs(dh) / SEUIL["hauteur"],
            "debit": abs(dd) / SEUIL["debit"], "timbre": abs(dt) / SEUIL["timbre"]}
    score = float(np.sqrt(sum(n ** 2 for n in norm.values())))
    jonctions.append({
        "jonction": f"{a['id']}>{b['id']}", "actes": f"{a['role']}>{b['role']}",
        "balises": f"{a['balise']}>{b['balise']}",
        "t_s": tl[b["id"]]["debut_s"],
        "d_volume_lu": round(dv, 2), "d_hauteur_dt": round(float(dh), 2),
        "d_debit_pct": round(float(dd), 1), "d_timbre_pct": round(float(dt), 1),
        "d_centroide_global_pct": round(float(dtg), 1),
        **{f"n_{k}": round(v, 2) for k, v in norm.items()},
        "dominante": max(norm, key=norm.get), "score": round(score, 2),
    })

for nom, data in (("voix_segments.csv", rows), ("voix_jonctions.csv", jonctions)):
    with open(OUT / nom, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(data[0]), delimiter=";")
        w.writeheader()
        w.writerows(data)
json.dump({"seuils": SEUIL, "segments": rows, "jonctions": jonctions},
          open(OUT / "voix.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("ok")
