# -*- coding: utf-8 -*-
"""EP001c - generation de la voix par blocs (phase 5 de la skill). UN bloc par appel :

    python3 gen_tts_blocs.py B1
    python3 gen_tts_blocs.py B4 B4_prise2     (nouvelle prise, ecrite dans audio/blocs/B4_prise2/)

Avant l'appel a l'API, et sans exception :
  - VALIDATION_PHASE4.md existe, et le fichier STOP est absent ;
  - les textes prononces (vo_fr de script.json, texte_tts de tts_manifest.json) ont exactement
    l'empreinte du texte valide : la validation porte sur un texte, pas sur l'empreinte du fichier
    script.json, dont seuls les champs visuels ont change depuis ;
  - voice_id du manifeste = voice_id de config/voice.json ; bloc <= 4 500 caracteres ;
  - le bloc n'a pas deja ete genere (pas de double depense).
Ecrit audio/blocs/Bx.mp3, Bx_brut.wav, Bx_alignement.json, Bx_texte_envoye.txt. Ne decoupe rien."""
import base64, hashlib, json, os, re, subprocess, sys
import requests
EP = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(os.path.dirname(EP))
VO_MD5, TTS_MD5 = "cb607ccadab5ce466ff52654231dce47", "d26d4e085e7ccf33d46f02293421f977"
LIMITE = 4500
def stop(msg): sys.exit("ARRET : " + msg)
bid = sys.argv[1] if len(sys.argv) > 1 else stop("bloc non precise")
if not os.path.exists(os.path.join(EP, "VALIDATION_PHASE4.md")): stop("VALIDATION_PHASE4.md absent")
if os.path.exists(os.path.join(EP, "STOP")): stop("fichier STOP present")
S = json.load(open(os.path.join(EP, "script.json"), encoding="utf-8"))
M = json.load(open(os.path.join(EP, "tts_manifest.json"), encoding="utf-8"))
h = lambda x: hashlib.md5(json.dumps(x, ensure_ascii=False).encode()).hexdigest()
if h([(g["id"], g["vo_fr"]) for g in S["segments"]]) != VO_MD5: stop("vo_fr different du texte valide")
if h([(g["id"], g["texte_tts"]) for g in M["segments"]]) != TTS_MD5: stop("texte_tts different du texte valide")
V = json.load(open(os.path.join(ROOT, "config", "voice.json"), encoding="utf-8"))
if not V.get("voice_id") or M["voice_id"] != V["voice_id"]: stop("voice_id vide ou different de config/voice.json")
bloc = next((b for b in M["blocs"] if b["id"] == bid), None) or stop(f"bloc {bid} inconnu")
tt = {g["id"]: g["texte_tts"] for g in M["segments"]}
texte = " ".join(tt[i] for i in bloc["segments"])
if len(texte) > LIMITE: stop(f"{len(texte)} caracteres > {LIMITE}")
if len(texte) != bloc["caracteres"]: stop("caracteres du manifeste incoherents")
SOUS = sys.argv[2] if len(sys.argv) > 2 else ""          # prise supplementaire : sous-dossier de audio/blocs
if SOUS and not re.fullmatch(r"B\d+_prise\d+", SOUS): stop("sous-dossier de prise invalide")
OUT = os.path.join(EP, "audio", "blocs", SOUS); os.makedirs(OUT, exist_ok=True)
if os.path.exists(os.path.join(OUT, f"{bid}.mp3")): stop(f"{bid} deja genere")
key = None
for l in open(os.path.join(ROOT, "config", "secrets.env"), encoding="utf-8-sig"):
    l = re.sub(r"^export\s+", "", l.strip())
    if l.startswith("#") or "=" not in l: continue
    n, v = l.split("=", 1)
    if n.strip() == "ELEVENLABS_API_KEY": key = v.strip().strip('"').strip("'")
if not key: stop("cle absente de config/secrets.env")
open(os.path.join(OUT, f"{bid}_texte_envoye.txt"), "w", encoding="utf-8").write(texte)
# derniere verification juste avant l'appel
if os.path.exists(os.path.join(EP, "STOP")) or not os.path.exists(os.path.join(EP, "VALIDATION_PHASE4.md")): stop("garde-fou")
r = requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{M['voice_id']}/with-timestamps",
                  params={"output_format": M["output_format"]},
                  json={"text": texte, "model_id": M["model_id"], "voice_settings": M["voice_settings"],
                        "output_format": M["output_format"]},
                  headers={"xi-api-key": key, "Content-Type": "application/json"}, timeout=170)
if not r.ok:
    sys.exit(f"HTTP {r.status_code} {r.headers.get('x-deny-reason', '')} : {r.text[:300]}")
j = r.json()
open(os.path.join(OUT, f"{bid}.mp3"), "wb").write(base64.b64decode(j["audio_base64"]))
json.dump({"alignment": j.get("alignment"), "normalized_alignment": j.get("normalized_alignment")},
          open(os.path.join(OUT, f"{bid}_alignement.json"), "w", encoding="utf-8"), ensure_ascii=False)
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", os.path.join(OUT, f"{bid}.mp3"), "-ar", "44100", "-ac", "1",
                "-c:a", "pcm_s16le", os.path.join(OUT, f"{bid}_brut.wav")], check=True)
al = j.get("alignment") or {}
print(json.dumps({"bloc": bid, "caracteres_envoyes": len(texte),
                  "alignement_identique_au_texte": "".join(al.get("characters", [])) == texte,
                  "request_id": r.headers.get("request-id")}))
