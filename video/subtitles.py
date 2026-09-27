# -*- coding: utf-8 -*-
"""Sous-titres, construits sur l'alignement caractere par caractere d'ElevenLabs.

Les fichiers `audio/alignments/Sxx.json` portent le temps de chaque caractere
prononce. C'est la seule source de calage exacte dont on dispose : on s'en sert
plutot que de repartir la duree au prorata des mots.
"""

import json
import re

MAX_CHARS = 42        # largeur d'une ligne de sous-titre
MAX_LINES = 2
MAX_CARD = 74         # longueur au-dela de laquelle on coupe le carton
MERGE_MAX = 84        # tolerance quand on recolle un carton orphelin
MIN_DUR = 0.9         # en dessous, le carton passe trop vite pour etre lu
MAX_DUR = 6.0         # duree maximale d'un carton
GAP = 0.60            # silence a partir duquel on coupe


def _clean(chars, starts, ends):
    """Retire les balises de jeu ElevenLabs : [curious], [thoughtful]...

    Elles figurent dans le texte envoye a l'API et donc dans l'alignement,
    mais ne sont pas prononcees. Les garder decalerait tout le sous-titre.
    """
    out = []
    depth = 0
    for c, s, e in zip(chars, starts, ends):
        if c == "[":
            depth += 1
            continue
        if c == "]":
            depth = max(0, depth - 1)
            continue
        if depth == 0:
            out.append((c, float(s), float(e)))
    return out


def _words(items):
    words, cur = [], None
    for c, s, e in items:
        if c.isspace():
            if cur:
                words.append(cur)
                cur = None
            continue
        if cur is None:
            cur = {"text": c, "start": s, "end": e}
        else:
            cur["text"] += c
            cur["end"] = e
    if cur:
        words.append(cur)
    return words


def _cards(words):
    """Regroupe les mots en cartons de deux lignes au plus."""
    cards, cur = [], None
    for w in words:
        if cur is None:
            cur = {"text": w["text"], "start": w["start"], "end": w["end"]}
            continue
        too_long = len(cur["text"]) + 1 + len(w["text"]) > MAX_CARD
        too_slow = w["end"] - cur["start"] > MAX_DUR
        breath = w["start"] - cur["end"] > GAP
        ends_clause = cur["text"].endswith((".", "?", "!", ":", ";"))
        if too_long or too_slow or breath or ends_clause:
            cards.append(cur)
            cur = {"text": w["text"], "start": w["start"], "end": w["end"]}
        else:
            cur["text"] += " " + w["text"]
            cur["end"] = w["end"]
    if cur:
        cards.append(cur)

    # Un carton d'un ou deux mots qui passe en une demi-seconde ne se lit pas :
    # on le recolle au precedent quand la place le permet.
    merged = []
    for c in cards:
        if (merged and c["end"] - c["start"] < MIN_DUR
                and len(merged[-1]["text"]) + 1 + len(c["text"]) <= MERGE_MAX
                and c["start"] - merged[-1]["end"] < GAP):
            merged[-1]["text"] += " " + c["text"]
            merged[-1]["end"] = c["end"]
        else:
            merged.append(c)
    return merged


# Mots qui appellent la suite : couper juste apres oblige l'oeil a redescendre
# au milieu d'un groupe. On les penalise comme fin de premiere ligne.
LIAISON = {
    "de", "du", "des", "d'un", "d'une", "le", "la", "les", "l'", "un", "une",
    "au", "aux", "a", "à", "en", "et", "ou", "qui", "que", "qu'il", "qu'elle",
    "dans", "pour", "sur", "par", "avec", "sans", "sous", "vers", "chez",
    "son", "sa", "ses", "leur", "leurs", "ce", "cet", "cette", "ces", "mon",
    "votre", "vos", "notre", "nos", "plus", "moins", "ne", "n'", "se", "s'",
}


def _wrap(s):
    """Coupe en deux lignes equilibrees, de preference a une jointure de sens.

    Un remplissage glouton laisse une premiere ligne pleine et un mot orphelin
    sur la seconde. On cherche donc le point de coupe qui egalise les deux
    lignes, en preferant une virgule et en evitant de separer un determinant
    ou une preposition de ce qu'il introduit.
    """
    if len(s) <= MAX_CHARS:
        return s
    words = s.split()
    if len(words) < 2:
        return s
    cands = []
    for i in range(1, len(words)):
        a, b = " ".join(words[:i]), " ".join(words[i:])
        width = max(len(a), len(b))
        score = width
        if a.endswith((",", ":", ";")):
            score -= 6
        if words[i - 1].strip(",").lower() in LIAISON:
            score += 8
        cands.append((width <= MAX_CHARS, score, width, i))

    # On choisit d'abord parmi les coupes qui tiennent dans la largeur ; la
    # ponctuation ne departage que celles-la. Si aucune ne tient, on prend la
    # plus equilibree sans se soucier de la ponctuation : une prime a la
    # virgule pourrait sinon faire deborder une ligne de plusieurs mots.
    fitting = [c for c in cands if c[0]]
    if fitting:
        _, _, _, cut = min(fitting, key=lambda c: (c[1], c[2]))
    else:
        _, _, _, cut = min(cands, key=lambda c: c[2])
    return " ".join(words[:cut]) + "\n" + " ".join(words[cut:])


def _ts(t):
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    ms = int(round((t - int(t)) * 1000))
    if ms == 1000:
        s, ms = s + 1, 0
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def build_srt(align_dir, order, offsets, out_path):
    """Ecrit un .srt cale sur le montage final. `offsets` : debut de chaque segment."""
    cards = []
    for sid in order:
        p = align_dir / f"{sid}.json"
        if not p.exists():
            continue
        a = json.loads(p.read_text(encoding="utf-8"))
        items = _clean(a["characters"],
                       a["character_start_times_seconds"],
                       a["character_end_times_seconds"])
        off = offsets[sid]
        for c in _cards(_words(items)):
            cards.append({"text": _wrap(c["text"]),
                          "start": c["start"] + off,
                          "end": c["end"] + off})

    lines = []
    for i, c in enumerate(cards, 1):
        end = max(c["end"], c["start"] + 0.7)
        if i < len(cards):
            end = min(end, cards[i]["start"] - 0.02)
        lines += [str(i), f"{_ts(c['start'])} --> {_ts(max(end, c['start'] + 0.4))}",
                  c["text"], ""]
    out_path.write_text("\n".join(lines), encoding="utf-8-sig")
    return len(cards)
