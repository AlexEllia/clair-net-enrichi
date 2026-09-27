# -*- coding: utf-8 -*-
"""Phase 5.5 — EP001b : intercale les respirations (silence numérique) et produit audio/voix_respirations.wav."""
import json, os, subprocess, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); AUD = os.path.join(HERE, "audio")
d = json.load(open(os.path.join(AUD, "durations.json"), encoding="utf-8"))
ids = sorted(k for k in d if not k.startswith("_"))
tmp = tempfile.mkdtemp(); sil = {}
def silence(x):
    if x not in sil:
        p = os.path.join(tmp, f"sil_{x:.2f}.wav")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono",
                        "-t", f"{x}", "-c:a", "pcm_s16le", p], check=True)
        sil[x] = p
    return sil[x]
lst = os.path.join(tmp, "list.txt")
with open(lst, "w") as f:
    for k in ids:
        f.write(f"file '{os.path.join(AUD, k + '.wav')}'\n")
        if d[k]["silence_apres_s"] > 0: f.write(f"file '{silence(d[k]['silence_apres_s'])}'\n")
out = os.path.join(AUD, "voix_respirations.wav")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", lst,
                "-c:a", "pcm_s16le", "-ar", "44100", "-ac", "1", out], check=True)
real = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", out],
                            capture_output=True, text=True).stdout)
voix = sum(d[k]["duree_audio_s"] for k in ids); tot = sum(d[k]["duree_totale_s"] for k in ids)
print(f"voix seule {voix:.1f} s ({int(voix//60)} min {voix%60:04.1f}) | avec respirations {tot:.1f} s | fichier {real:.2f} s")
print("contrôle 485 s (voix seule) :", "OK" if voix >= 485 else "ÉCHEC")
