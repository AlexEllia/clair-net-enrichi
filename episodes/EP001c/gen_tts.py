# -*- coding: utf-8 -*-
"""EP001c — phase 5 : genere UN segment par appel (endpoint with-timestamps).
Usage : python3 gen_tts.py S01

Verrou (SKILL, phase 5) verifie AVANT l'appel API :
  - VALIDATION_PHASE4.md present ;
  - aucun fichier STOP ;
  - script.json identique a la version validee (md5 inscrit dans VALIDATION_PHASE4.md) ;
  - voice_id du manifeste = celui de config/voice.json.
Un seul segment par execution, jamais en arriere-plan."""
import base64, hashlib, json, os, re, subprocess, sys, tempfile, time
import requests
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
AUD, ALI = os.path.join(HERE, "audio"), os.path.join(HERE, "audio", "alignments")

def verrou():
    val = os.path.join(HERE, "VALIDATION_PHASE4.md")
    if not os.path.exists(val): sys.exit("ARRET : VALIDATION_PHASE4.md absent")
    if os.path.exists(os.path.join(HERE, "STOP")): sys.exit("ARRET : fichier STOP present")
    m = re.search(r"script\.json`, md5 `([0-9a-f]{32})`", open(val, encoding="utf-8").read())
    if not m: sys.exit("ARRET : md5 du script valide introuvable dans VALIDATION_PHASE4.md")
    cur = hashlib.md5(open(os.path.join(HERE, "script.json"), "rb").read()).hexdigest()
    if cur != m.group(1): sys.exit(f"ARRET : script.json modifie depuis la validation ({cur} != {m.group(1)})")

def api_key():
    for l in open(os.path.join(ROOT, "config", "secrets.env"), encoding="utf-8-sig"):
        l = re.sub(r"^export\s+", "", l.strip())
        if l.startswith("#") or "=" not in l: continue
        n, v = l.split("=", 1)
        if n.strip() == "ELEVENLABS_API_KEY": return v.strip().strip('"').strip("'")
    sys.exit("ELEVENLABS_API_KEY absente de config/secrets.env")

def probe(p):
    o = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", p], capture_output=True, text=True, check=True)
    return float(o.stdout.strip())

if len(sys.argv) != 2 or "," in sys.argv[1]: sys.exit("un seul segment par appel : python3 gen_tts.py S01")
sid = sys.argv[1]
man = json.load(open(os.path.join(HERE, "tts_manifest.json"), encoding="utf-8"))
voice = json.load(open(os.path.join(ROOT, "config", "voice.json"), encoding="utf-8"))
vid = man["voice_id"]
if not vid or vid != voice.get("voice_id"): sys.exit("ARRET : voice_id vide ou different de config/voice.json")
seg = next(s for s in man["segments"] if s["id"] == sid)
os.makedirs(ALI, exist_ok=True)
verrou()                                   # derniere verification, juste avant l'appel
t0 = time.time()
r = requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{vid}/with-timestamps",
                  params={"output_format": man["output_format"]},
                  json={"text": seg["texte_tts"], "model_id": man["model_id"],
                        "voice_settings": man["voice_settings"], "output_format": man["output_format"]},
                  headers={"xi-api-key": api_key(), "Content-Type": "application/json"}, timeout=170)
if not r.ok:
    sys.exit(f"HTTP {r.status_code} deny={r.headers.get('x-deny-reason')} : {r.text[:250]}")
j = r.json()
mp3 = os.path.join(tempfile.gettempdir(), f"EP001c_{sid}.mp3")
open(mp3, "wb").write(base64.b64decode(j["audio_base64"]))
wav = os.path.join(AUD, f"{sid}.wav")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", mp3, "-ar", "44100", "-ac", "1",
                "-c:a", "pcm_s16le", wav], check=True)
d = round(probe(wav), 2)
al = j.get("alignment") or j.get("normalized_alignment")
json.dump(al, open(os.path.join(ALI, f"{sid}.json"), "w", encoding="utf-8"), ensure_ascii=False)
dpath = os.path.join(AUD, "durations.json")
dur = json.load(open(dpath, encoding="utf-8")) if os.path.exists(dpath) else {}
sil = seg["silence_apres_s"]
dur[sid] = {"duree_audio_s": d, "silence_apres_s": sil, "duree_totale_s": round(d + sil, 2)}
dur["_meta"] = {"model_id": man["model_id"], "voice_id": vid, "format_source": man["output_format"],
                "wav": "44100 Hz mono 16 bits", "stability": man["voice_settings"]["stability"],
                "regle": "le pipeline video se cale sur duree_totale_s ; le seuil des 485 s porte sur duree_audio_s"}
ids = sorted(k for k in dur if not k.startswith("_"))
json.dump({**{k: dur[k] for k in ids}, "_meta": dur["_meta"]}, open(dpath, "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
txt = "".join(al["characters"]) if al else ""
print(f"{sid} : {d:.2f} s voix + {sil:.2f} s | {len(seg['texte_tts'])} caracteres envoyes | "
      f"alignement identique au texte : {txt == seg['texte_tts']} | {time.time()-t0:.1f} s")
