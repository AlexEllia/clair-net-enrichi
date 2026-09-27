# -*- coding: utf-8 -*-
"""Phase 5.3-5.4 — EP001b : un appel ElevenLabs par segment (with-timestamps), WAV + alignement + durations.json.
Usage : python3 gen_tts.py S01,S02,S03"""
import base64, json, os, re, subprocess, sys, tempfile, time
import requests
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
AUD, ALI = os.path.join(HERE, "audio"), os.path.join(HERE, "audio", "alignments")
os.makedirs(ALI, exist_ok=True)

def api_key():
    for l in open(os.path.join(ROOT, "config", "secrets.env"), encoding="utf-8-sig"):
        l = re.sub(r"^export\s+", "", l.strip())
        if l.startswith("#") or "=" not in l: continue
        n, v = l.split("=", 1)
        if n.strip() == "ELEVENLABS_API_KEY": return v.strip().strip('"').strip("'")
    sys.exit("ELEVENLABS_API_KEY absente de config/secrets.env")
KEY = api_key()
man = json.load(open(os.path.join(HERE, "tts_manifest.json"), encoding="utf-8"))
vid = man["voice_id"]
if not vid: sys.exit("voice_id vide dans config/voice.json — arrêt.")

def synth(text):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{vid}/with-timestamps"
    body = {"text": text, "model_id": man["model_id"], "voice_settings": man["voice_settings"],
            "output_format": man["output_format"]}
    for att in range(3):
        r = requests.post(url, params={"output_format": man["output_format"]}, json=body,
                          headers={"xi-api-key": KEY, "Content-Type": "application/json"}, timeout=170)
        if r.ok: return r.json()
        print(f"   HTTP {r.status_code} deny={r.headers.get('x-deny-reason')} : {r.text[:250]}")
        if r.status_code in (401, 403, 422) or att == 2: sys.exit(1)
        time.sleep(5)

def probe(p):
    o = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", p], capture_output=True, text=True, check=True)
    return float(o.stdout.strip())

dpath = os.path.join(AUD, "durations.json")
dur = json.load(open(dpath, encoding="utf-8")) if os.path.exists(dpath) else {}
for sid in sys.argv[1].split(","):
    seg = next(s for s in man["segments"] if s["id"] == sid)
    t0 = time.time(); j = synth(seg["texte_tts"])
    mp3 = os.path.join(tempfile.gettempdir(), f"{sid}.mp3")
    open(mp3, "wb").write(base64.b64decode(j["audio_base64"]))
    wav = os.path.join(AUD, f"{sid}.wav")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", mp3, "-ar", "44100", "-ac", "1",
                    "-c:a", "pcm_s16le", wav], check=True)
    d = round(probe(wav), 2)
    al = j.get("normalized_alignment") or j.get("alignment")
    json.dump(al, open(os.path.join(ALI, f"{sid}.json"), "w", encoding="utf-8"), ensure_ascii=False)
    s_after = seg["silence_apres_s"]
    dur[sid] = {"duree_audio_s": d, "silence_apres_s": s_after, "duree_totale_s": round(d + s_after, 2)}
    print(f"  {sid} : {d:6.2f} s voix + {s_after:.2f} s silence | {time.time()-t0:4.1f} s d'appel")
dur["_meta"] = {"model_id": man["model_id"], "voice_id": vid, "format_source": man["output_format"],
                "wav": "44100 Hz mono 16 bits", "stability": man["voice_settings"]["stability"],
                "regle": "le pipeline video se cale sur duree_totale_s ; le seuil des 485 s porte sur duree_audio_s"}
seg_ids = sorted(k for k in dur if not k.startswith("_"))
dur = {**{k: dur[k] for k in seg_ids}, "_meta": dur["_meta"]}
json.dump(dur, open(dpath, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
v = sum(dur[k]["duree_audio_s"] for k in seg_ids)
print(f"Cumul {len(seg_ids)} segments : voix {v:.1f} s")
