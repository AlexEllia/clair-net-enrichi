# -*- coding: utf-8 -*-
"""Durees des segments et timeline absolue de l'episode.

`audio/durations.json` existe sous deux formes :

    ancien  {"S01": 18.4}
    nouveau {"S01": {"duree_audio_s": 18.4, "silence_apres_s": 0.45,
                     "duree_totale_s": 18.85}}

L'ancien se lit comme une duree de voix sans silence : l'EP001 continue de se
construire tel quel.

Le plan d'un segment dure `duree_audio_s` ; pendant `silence_apres_s` la
derniere image est tenue. Le debut absolu d'un segment est la somme des
`duree_totale_s` qui le precedent : les silences comptent.

`build/timeline.json` fait foi pour tous les timecodes de l'episode. Ceux de
metadonnees.md sont calcules en amont et peuvent deriver.
"""

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

TOL = 0.011     # ecart tolere entre audio + silence et total, en secondes
ECRAN_FIN_MIN = 20.0    # un ecran de fin dure au moins la duree maximale des elements
                        # de fin de YouTube : prolonge en silence apres la voix


@dataclass
class Duree:
    audio: float
    silence: float
    total: float


def warn(msg):
    print(f"[ATTENTION] {msg}", file=sys.stderr, flush=True)


def load_durations(path):
    """{sid: Duree}. Les cles commencant par `_` (metadonnees) sont ignorees."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    out = {}
    for sid, v in raw.items():
        if sid.startswith("_"):
            continue
        if isinstance(v, (int, float)):
            out[sid] = Duree(float(v), 0.0, float(v))
            continue
        audio = float(v["duree_audio_s"])
        silence = float(v.get("silence_apres_s", 0.0))
        total = float(v.get("duree_totale_s", audio + silence))
        if abs(audio + silence - total) > TOL:
            warn(f"{sid} : audio {audio:.2f} + silence {silence:.2f} "
                 f"!= total {total:.2f} ; le total fait foi pour la timeline")
        out[sid] = Duree(audio, silence, total)
    return out


def ajuster(script, durations):
    """Durees de montage : celles de la voix, sauf pour un plan `ecran_fin`,
    prolonge en silence jusqu'a ECRAN_FIN_MIN. Idempotent."""
    out = dict(durations)
    for s in script["segments"]:
        d = out.get(s["id"])
        if s.get("type_visuel") == "ecran_fin" and d is not None and d.total < ECRAN_FIN_MIN:
            out[s["id"]] = Duree(d.audio, ECRAN_FIN_MIN - d.audio, ECRAN_FIN_MIN)
    return out


def fmt_tc(t):
    """Timecode YouTube : M:SS, ou H:MM:SS au-dela d'une heure. Arrondi vers le
    bas : un chapitre qui s'ouvre dans la respiration precedente plutot qu'apres
    le premier mot."""
    s = int(t + 1e-6)
    h, rem = divmod(s, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


# --- Chapitres ---------------------------------------------------------------
# Un chapitre commence a chaque changement de `role` dans le script ; les
# roles de fin - mention, ouverture, cta - ne forment qu'un chapitre, qui
# commence au premier d'entre eux. Les titres viennent de metadonnees.md (bloc
# "Chapitres"), sinon du bloc "Chapitres" de la description YouTube
# (script.json), sinon de audio/timecodes.json ; leurs timecodes sont ignores,
# on ne garde que l'ordre. En build (strict) : un nombre de titres different
# du nombre de chapitres, ou un chapitre de moins de CHAPITRE_MIN, bloque.

_TC_LINE = re.compile(r"^\s*-?\s*(\d{1,2}:)?\d{1,2}:\d{2}\s+(.+?)\s*$")
ROLES_FIN = ("mention", "ouverture", "cta")
CHAPITRE_MIN = 10.0     # regle YouTube : un chapitre dure au moins 10 s


def _chapitre(role):
    return "fin" if role in ROLES_FIN else role


def _titres_meta(ep_dir):
    """[(timecode, titre)] du premier bloc « Chapitres » de metadonnees.md."""
    p = ep_dir / "metadonnees.md"
    if not p.exists():
        return []
    out, dans = [], False
    for l in p.read_text(encoding="utf-8").splitlines():
        if not dans:
            dans = l.strip().lstrip("#").strip().startswith("Chapitres")
            continue
        m = _TC_LINE.match(l)
        if m:
            out.append((l.strip().split()[0], m.group(2)))
        elif out and not l.strip():
            break
    return out


def _titles(script, ep_dir):
    meta = _titres_meta(ep_dir)
    if meta:
        return [t for _, t in meta], "metadonnees.md"
    desc = (script.get("meta") or {}).get("description_youtube") or ""
    if "Chapitres" in desc:
        block = desc.split("Chapitres", 1)[1].strip().split("\n\n", 1)[0]
        titles = [m.group(2) for m in map(_TC_LINE.match, block.splitlines()) if m]
        if titles:
            return titles, "script.json (description_youtube)"
    tc = ep_dir / "audio" / "timecodes.json"
    if tc.exists():
        rows = json.loads(tc.read_text(encoding="utf-8")).get("chapitres") or []
        titles = [m.group(2) for m in map(_TC_LINE.match, rows) if m]
        if titles:
            return titles, "audio/timecodes.json"
    return [], None


def build_timeline(ep, script, durations, ep_dir, strict=False):
    segments = script["segments"]
    durations = ajuster(script, durations)
    missing = [s["id"] for s in segments if s["id"] not in durations]
    if missing:
        raise SystemExit(f"durees audio manquantes : {missing}")

    rows, acc = [], 0.0
    for s in segments:
        d = durations[s["id"]]
        rows.append({
            "id": s["id"],
            "role": s.get("role"),
            "debut_s": round(acc, 3),
            "fin_voix_s": round(acc + d.audio, 3),
            "fin_s": round(acc + d.total, 3),
            "duree_audio_s": d.audio,
            "silence_apres_s": d.silence,
            "duree_totale_s": d.total,
        })
        acc += d.total

    # Le mid-roll tombe a la fin du segment marque, respiration comprise : la
    # coupure ne mange pas le silence qui clot l'acte.
    midrolls = [{"apres": r["id"], "t_s": r["fin_s"], "tc": fmt_tc(r["fin_s"])}
                for r, s in zip(rows, segments) if s.get("midroll_apres")]
    if len(midrolls) != 3:
        warn(f"{ep} : {len(midrolls)} mid-roll(s) marque(s) dans le script, 3 attendus")

    starts = [r for i, r in enumerate(rows)
              if i == 0 or _chapitre(r["role"]) != _chapitre(rows[i - 1]["role"])]
    titles, src = _titles(script, ep_dir)
    if titles and len(titles) != len(starts):
        msg = (f"{ep} : {len(titles)} titres de chapitre ({src}) pour {len(starts)} "
               f"chapitres calcules")
        if strict:
            raise SystemExit(msg + " - corriger les titres ou les roles avant le build")
        warn(msg + " ; titres remplaces par les roles")
        titles = []
    if strict:
        bornes = [r["debut_s"] for r in starts] + [acc]
        courts = [(r["id"], round(b - a, 2)) for r, a, b in zip(starts, bornes, bornes[1:])
                  if b - a < CHAPITRE_MIN]
        if courts:
            raise SystemExit(f"{ep} : chapitre(s) de moins de {CHAPITRE_MIN:.0f} s "
                             f"(regle YouTube) : {courts}")
    if not titles:
        titles = [r["role"] or r["id"] for r in starts]
    chapters = [{"debut_s": r["debut_s"], "tc": fmt_tc(r["debut_s"]), "segment": r["id"],
                 "titre": t} for r, t in zip(starts, titles)]

    return {
        "episode": ep,
        "duree_totale_s": round(acc, 3),
        "duree_voix_s": round(sum(durations[s["id"]].audio for s in segments), 3),
        "segments": rows,
        "midrolls": midrolls,
        "chapitres": chapters,
    }


def write_timeline(tl, build_dir):
    build_dir.mkdir(parents=True, exist_ok=True)
    (build_dir / "timeline.json").write_text(
        json.dumps(tl, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (build_dir / "chapitres.txt").write_text(
        "".join(f"{c['tc']} {c['titre']}\n" for c in tl["chapitres"]), encoding="utf-8")


def print_timeline(tl):
    mid = {m["apres"] for m in tl["midrolls"]}
    print(f"\n{tl['episode']}  -  {len(tl['segments'])} segments\n")
    print(f"  {'seg':<4} {'role':<8} {'debut':>8} {'fin voix':>9} {'fin':>8}"
          f" {'audio':>7} {'silence':>8}")
    for r in tl["segments"]:
        print(f"  {r['id']:<4} {(r['role'] or ''):<8} {r['debut_s']:8.2f} {r['fin_voix_s']:9.2f}"
              f" {r['fin_s']:8.2f} {r['duree_audio_s']:7.2f} {r['silence_apres_s']:8.2f}"
              + ("   << mid-roll" if r["id"] in mid else ""))
    tot = tl["duree_totale_s"]
    print(f"\n  duree totale : {fmt_tc(tot)} ({tot:.2f} s), voix seule {tl['duree_voix_s']:.2f} s,"
          f" silences {tot - tl['duree_voix_s']:.2f} s")
    for k, m in enumerate(tl["midrolls"], 1):
        print(f"  mid-roll {k}   : {m['tc']}  ({m['t_s']:.2f} s, apres {m['apres']})")
    print("\n  chapitres :")
    for c in tl["chapitres"]:
        print(f"    {c['tc']} {c['titre']}")
    if tot < 480:
        print("\n  ATTENTION : sous 8 minutes, les coupures intermediaires ne se debloquent pas")
