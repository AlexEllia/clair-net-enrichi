# -*- coding: utf-8 -*-
"""Phase 5.1 — EP001b : script.json -> tts_manifest.json (normalisation + direction de lecture)."""
import json, os, re
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sc = json.load(open(os.path.join(HERE, "script.json"), encoding="utf-8"))
vid = json.load(open(os.path.join(ROOT, "config", "voice.json"), encoding="utf-8")).get("voice_id", "").strip()

# Normalisation phonétique : uniquement les chiffres restants du script validé.
NORM = [("août 2026", "août deux mille vingt-six"),
        ("en 2025", "en deux mille vingt-cinq"),
        ("CAC 40", "CAC quarante"),
        ("depuis 1987", "depuis mille neuf cent quatre-vingt-sept"),
        ("depuis 1988", "depuis mille neuf cent quatre-vingt-huit"),
        ("En 2024", "En deux mille vingt-quatre"),
        ("trimestre 2026", "trimestre deux mille vingt-six")]

# Balise d'ouverture par segment (continuité intra-acte), puis balise secondaire sur un vrai basculement.
OPEN = {"S01": "serious", "S02": "thoughtful",
        **{f"S{i:02d}": "thoughtful" for i in range(3, 11)},
        **{f"S{i:02d}": "curious" for i in range(11, 18)}, "S18": "thoughtful",
        **{f"S{i:02d}": "serious" for i in range(19, 24)}, "S24": "warm", "S25": "thoughtful",
        "S26": "warm", "S27": "warm", "S28": "serious"}
SECOND = {"S06": ("La ligne des versements est plate", "excited"),
          "S08": ("Passé trente ans", "excited"),
          "S10": ("Et le montant que vous versez", "curious"),
          "S13": ("Alors la voici.", "excited"),
          "S15": ("Cette quinzième année ne dépend pas", "excited"),
          "S28": ("Abonnez-vous", "warm")}

segs = sc["segments"]
def sil(i):
    s = segs[i]
    if i == len(segs) - 1: return 0.0
    nxt = segs[i + 1]
    if nxt["role"] == "payoff" and s["role"] != "payoff": return 1.2
    if s["midroll_apres"] or nxt["role"] != s["role"]: return 1.0
    return 0.45

TOK = re.compile(r"[0-9]+|[^\W\d_]+(?:['’\-][^\W\d_]+)*", re.UNICODE)
out, ecarts = [], []
for i, s in enumerate(segs):
    t = s["vo_fr"]
    for a, b in NORM: t = t.replace(a, b)
    assert not re.search(r"\d", t), (s["id"], t)
    if s["id"] in SECOND:
        anchor, tag = SECOND[s["id"]]
        assert anchor in t, (s["id"], anchor)
        t = t.replace(anchor, f"[{tag}] " + anchor, 1)
    t = f"[{OPEN[s['id']]}] " + t
    n0 = len(TOK.findall(s["vo_fr"]))
    n1 = len(TOK.findall(re.sub(r"\[[a-z]+\]", "", t)))
    if abs(n1 - n0) / n0 > 0.05: ecarts.append(f"{s['id']} {n0}->{n1}")
    out.append({"id": s["id"], "texte_tts": t, "fichier_sortie": f"audio/{s['id']}.mp3",
                "silence_apres_s": sil(i)})

man = {"voice_id": vid, "model_id": "eleven_v3", "output_format": "mp3_44100_192",
       "voice_settings": {"stability": 0.5, "similarity_boost": 0.75, "style": 0.35,
                          "use_speaker_boost": True, "speed": 1.0},
       "_notes": {"normalisation": "Seuls les nombres en chiffres (années, CAC 40) sont passés en toutes lettres. "
                  "Écart de décompte > 5 % sur " + (", ".join(ecarts) or "aucun segment") +
                  " : purement mécanique (une année en chiffres compte pour 1 mot, en lettres pour 3 ou 4), "
                  "contenu prononcé identique.",
                  "previous_next_text": "Non transmis : eleven_v3 les refuse."},
       "segments": out}
json.dump(man, open(os.path.join(HERE, "tts_manifest.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("voice_id présent:", bool(vid), "| segments:", len(out), "| écarts>5%:", ecarts)
print("silences:", [(o["id"], o["silence_apres_s"]) for o in out if o["silence_apres_s"] != 0.45])
print("balises/segment:", {o["id"]: re.findall(r"\[([a-z]+)\]", o["texte_tts"]) for o in out})
print("caractères envoyés:", sum(len(o["texte_tts"]) for o in out))
