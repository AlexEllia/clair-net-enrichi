# -*- coding: utf-8 -*-
"""Extrait, pour chaque segment, le début réel de chaque mot prononcé (balises exclues) depuis audio/alignments."""
import json, os, re
HERE = os.path.dirname(os.path.abspath(__file__))
TOK = re.compile(r"[0-9]+|[^\W\d_]+(?:['’\-][^\W\d_]+)*", re.UNICODE)
out = {}
for f in sorted(os.listdir(os.path.join(HERE, "audio", "alignments"))):
    a = json.load(open(os.path.join(HERE, "audio", "alignments", f), encoding="utf-8"))
    txt = "".join(a["characters"]); st = a["character_start_times_seconds"]
    tags = [(m.start(), m.end()) for m in re.finditer(r"\[[a-z ]+\]", txt)]
    words = []
    for m in TOK.finditer(txt):
        if any(s <= m.start() < e for s, e in tags): continue
        words.append([m.group(), round(st[m.start()], 3)])
    out[f[:-5]] = words
json.dump(out, open(os.path.join(HERE, "audio", "word_times.json"), "w", encoding="utf-8"), ensure_ascii=False)
print({k: len(v) for k, v in out.items()})
