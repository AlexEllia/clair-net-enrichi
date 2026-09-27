# -*- coding: utf-8 -*-
"""Phase 5 — generation audio ElevenLabs, un fichier par segment, endpoint with-timestamps."""
import re,json,base64,os,sys,subprocess,time,urllib.request,urllib.error

ROOT=os.path.dirname(os.path.abspath(__file__)); EP=os.path.join(ROOT,"episodes","EP001")
AUD=os.path.join(EP,"audio"); ALI=os.path.join(AUD,"alignments")
os.makedirs(ALI,exist_ok=True)

def api_key():
    for l in open(os.path.join(ROOT,"config","secrets.env"),encoding="utf-8-sig"):
        l=re.sub(r"^export\s+","",l.strip())
        if l.startswith("#") or "=" not in l: continue
        n,v=l.split("=",1)
        if n.strip()=="ELEVENLABS_API_KEY": return v.strip().strip('"').strip("'")
    raise SystemExit("ELEVENLABS_API_KEY absente de config/secrets.env")
KEY=api_key()

MAN=os.path.join(EP,"tts_manifest.json")
man=json.load(open(MAN,encoding="utf-8"))
vid=(json.load(open(os.path.join(ROOT,"config","voice.json"),encoding="utf-8")).get("voice_id") or "").strip()
if not vid: raise SystemExit("voice_id vide dans config/voice.json — arret (phase 5, etape 2).")

FMT="mp3_44100_192"
man.update({"voice_id":vid,"model_id":"eleven_v3","output_format":FMT})
man["voice_settings"]["stability"]=0.5
man["_notes_techniques"]={
 "stability":"0.5 (equivalent numerique de 'natural' : l'API refuse la valeur textuelle)",
 "output_format":"mp3_44100_192 puis conversion WAV 44,1 kHz mono 16 bits par ffmpeg. pcm_44100 est reserve au palier Pro sur ce compte.",
 "conditionnement":"previous_text / next_text conserves dans ce fichier a titre documentaire mais NON transmis a l'API : eleven_v3 les refuse (HTTP 400, unsupported_model). Arbitrage valide : on garde les balises de direction de lecture, que multilingual_v2 vocaliserait."}
json.dump(man,open(MAN,"w",encoding="utf-8"),ensure_ascii=False,indent=2)

def synth(seg):
    body={"text":seg["texte_tts"],"model_id":man["model_id"],"voice_settings":man["voice_settings"]}
    url="https://api.elevenlabs.io/v1/text-to-speech/%s/with-timestamps?output_format=%s"%(vid,FMT)
    req=urllib.request.Request(url,data=json.dumps(body).encode("utf-8"),
        headers={"xi-api-key":KEY,"Content-Type":"application/json"},method="POST")
    with urllib.request.urlopen(req,timeout=300) as r: return json.loads(r.read().decode("utf-8"))

def to_wav(mp3,wav):
    subprocess.run(["ffmpeg","-y","-loglevel","error","-i",mp3,"-ac","1","-ar","44100",
                    "-c:a","pcm_s16le",wav],check=True)
    d=subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
                      "-of","default=nw=1:nk=1",wav],capture_output=True,text=True,check=True)
    return float(d.stdout.strip())

ids=sys.argv[1].split(",")
dpath=os.path.join(AUD,"durations.json")
dur=json.load(open(dpath,encoding="utf-8")) if os.path.exists(dpath) else {}
for sid in ids:
    seg=next(s for s in man["segments"] if s["id"]==sid)
    for att in range(3):
        try: j=synth(seg); break
        except urllib.error.HTTPError as e:
            msg=e.read(500).decode("utf-8","replace")
            print("  %s HTTP %s : %s"%(sid,e.code,msg[:300]))
            if e.code in (401,403,422) or att==2: raise SystemExit(1)
            time.sleep(4)
    mp3="/tmp/%s.mp3"%sid
    open(mp3,"wb").write(base64.b64decode(j["audio_base64"]))
    wav=os.path.join(AUD,"%s.wav"%sid); d=to_wav(mp3,wav)
    al=j.get("normalized_alignment") or j.get("alignment")
    json.dump(al,open(os.path.join(ALI,"%s.json"%sid),"w",encoding="utf-8"),ensure_ascii=False)
    dur[sid]=round(d,2)
    print("  %s : %6.2f s | alignement %4d caracteres | %s"%(sid,d,len(al["characters"]),os.path.basename(wav)))
dur["_meta"]={"model_id":man["model_id"],"voice_id":vid,"format_source":FMT,
              "wav":"44100 Hz mono 16 bits","stability":man["voice_settings"]["stability"]}
json.dump(dur,open(dpath,"w",encoding="utf-8"),ensure_ascii=False,indent=2)
tot=sum(v for k,v in dur.items() if not k.startswith("_"))
print("Cumul %d segments : %.1f s (%d min %02d s)"%(len([k for k in dur if not k.startswith('_')]),tot,int(tot)//60,int(tot)%60))
