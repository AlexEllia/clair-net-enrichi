# -*- coding: utf-8 -*-
"""Test de voix EP001c, version B : S18 a S26 en une seule requete.
Lecture seule sur la production (tts_manifest.json, config). N'ecrit que dans test_voix_bloc/.
Une seule variable change par rapport a la production : le decoupage des requetes."""
import base64, json, os, re, subprocess, sys, tempfile
import requests
HERE = os.path.dirname(os.path.abspath(__file__))
EP = os.path.dirname(HERE); ROOT = os.path.dirname(os.path.dirname(EP))
IDS = [f"S{i}" for i in range(18, 27)]
LIMITE = 5000                       # eleven_v3, caracteres par requete (doc ElevenLabs, modeles)
man = json.load(open(os.path.join(EP, "tts_manifest.json"), encoding="utf-8"))
seg = {s["id"]: s["texte_tts"] for s in man["segments"]}
bloc = " ".join(seg[i] for i in IDS)          # separateur : une espace, rien d'autre
open(os.path.join(HERE, "B_texte_envoye.txt"), "w", encoding="utf-8").write(bloc)
print("caracteres du bloc :", len(bloc), "| limite", LIMITE)
if len(bloc) > LIMITE: sys.exit("ARRET : bloc au-dessus de la limite, a couper hors jonctions testees")
if "--sec" in sys.argv: sys.exit(0)
voice = json.load(open(os.path.join(ROOT, "config", "voice.json"), encoding="utf-8"))
if man["voice_id"] != voice["voice_id"]: sys.exit("ARRET : voice_id different")
if os.path.exists(os.path.join(HERE, "STOP")): sys.exit("ARRET : STOP present dans test_voix_bloc/")
key = None
for l in open(os.path.join(ROOT, "config", "secrets.env"), encoding="utf-8-sig"):
    l = re.sub(r"^export\s+", "", l.strip())
    if l.startswith("#") or "=" not in l: continue
    n, v = l.split("=", 1)
    if n.strip() == "ELEVENLABS_API_KEY": key = v.strip().strip('"').strip("'")
r = requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{man['voice_id']}/with-timestamps",
                  params={"output_format": man["output_format"]},
                  json={"text": bloc, "model_id": man["model_id"], "voice_settings": man["voice_settings"],
                        "output_format": man["output_format"]},
                  headers={"xi-api-key": key, "Content-Type": "application/json"}, timeout=175)
if not r.ok: sys.exit(f"HTTP {r.status_code} : {r.text[:250]}")
j = r.json()
mp3 = os.path.join(tempfile.gettempdir(), "EP001c_B_bloc.mp3")
open(mp3, "wb").write(base64.b64decode(j["audio_base64"]))
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", mp3, "-ar", "44100", "-ac", "1", "-c:a", "pcm_s16le",
                os.path.join(HERE, "B_bloc_brut.wav")], check=True)
al = j.get("alignment") or j.get("normalized_alignment")
json.dump(al, open(os.path.join(HERE, "B_alignement.json"), "w", encoding="utf-8"), ensure_ascii=False)
print("alignement identique au texte :", "".join(al["characters"]) == bloc)
print("caracteres envoyes :", len(bloc))
