# -*- coding: utf-8 -*-
"""Rendu d'un plan pilote : une famille hors catalogue, sur la voix actuelle.

    python video/pilote.py video/pilotes/EP001c_S02.json            960x540
    python video/pilote.py video/pilotes/EP001c_S02.json --full     1920x1080

Le brief pilote remplace, pour ce seul rendu, les champs visuels du segment
(`type_visuel`, `manim_brief`, `overlay_texte`). script.json n'est ni lu en
ecriture ni modifie : le script reste valide cote redaction.

Chaque revelation et chaque overlay qui porte un `declencheur` est recale sur
l'alignement reel de la voix (audio/alignments/Sxx.json), comme le fait la
skill apres la generation audio : le declencheur doit figurer une seule fois
dans le texte prononce. Un `t_rel_s` du brief qui s'en ecarte est signale.

Sorties :
  episodes/EPxxx/video/pilotes/Sxx.mp4           le plan, avec sa voix
  episodes/EPxxx/build/pilotes/Sxx_densite.*     sa carte de densite
"""

import argparse
import copy
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
PROJECT = ROOT.parent


def recaler(sid, items, align, quoi):
    """Recale `t_rel_s` sur le debut du declencheur dans l'alignement."""
    texte = "".join(align["characters"])
    starts = align["character_start_times_seconds"]
    for it in items:
        d = it.get("declencheur")
        if not d:
            continue
        n = texte.count(d)
        if n != 1:
            raise SystemExit(f"{sid} : declencheur {d!r} ({quoi}) trouve {n} fois dans la voix ; "
                             f"il doit y figurer exactement une fois")
        t = round(starts[texte.index(d)], 2)
        if it.get("t_rel_s") is not None and abs(float(it["t_rel_s"]) - t) > 0.05:
            print(f"[RECALAGE] {sid} : {quoi} {d!r} : {it['t_rel_s']} -> {t}", file=sys.stderr)
        it["t_rel_s"] = t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("brief")
    ap.add_argument("--full", action="store_true", help="1920x1080 au lieu de 960x540")
    args = ap.parse_args()

    brief = json.loads(Path(args.brief).read_text(encoding="utf-8"))
    ep, sid = brief["episode"], brief["segment"]
    ep_dir = PROJECT / "episodes" / ep
    script = json.loads((ep_dir / "script.json").read_text(encoding="utf-8"))
    seg = copy.deepcopy(next(s for s in script["segments"] if s["id"] == sid))
    for k in ("type_visuel", "manim_brief", "overlay_texte"):
        seg[k] = copy.deepcopy(brief["remplace"][k])
    seg["_pilote"] = True

    align = json.loads((ep_dir / "audio" / "alignments" / f"{sid}.json").read_text(encoding="utf-8"))
    recaler(sid, seg["manim_brief"].get("revelations") or [], align, "revelation")
    recaler(sid, seg["overlay_texte"], align, "overlay")

    import build
    import densite
    import nombres
    from briefs import resolve, still_times
    from components import COMPONENTS, Cues
    from scenes import add_overlays
    from timeline import load_durations
    nombres.set_locale("fr")
    d = load_durations(ep_dir / "audio" / "durations.json")[sid]

    print(f"{ep} {sid} : {seg['manim_brief']['composant']}, voix {d.audio:.2f} s "
          f"+ {d.silence:.2f} s tenus")
    for r in sorted(seg["manim_brief"].get("revelations") or [], key=lambda r: r["t_rel_s"]):
        print(f"  {r['t_rel_s']:6.2f} s  {r['element']:<12} {r.get('declencheur', '')}")
    for o in sorted(seg["overlay_texte"], key=lambda o: o["t_rel_s"]):
        print(f"  {o['t_rel_s']:6.2f} s  [{o['ancre']}] {o['texte_fr']}")

    # Calendrier : R6 tel que le moteur le pose (sans rendu).
    target, fam = resolve(seg, d.audio, log=False)
    cues = Cues(d.audio)
    cues.anchors = {o["ancre"] for o in seg["overlay_texte"]}
    COMPONENTS[fam](target, cues)
    add_overlays(seg, cues, "manim")
    cal = still_times(target, d.audio, [(t, t + rt) for t, _, rt in cues.items])

    vdir = ep_dir / "video" / "pilotes"
    media = vdir / "_manim"
    vdir.mkdir(parents=True, exist_ok=True)
    w, h = (1920, 1080) if args.full else (960, 540)
    raw = build.render_segment(seg, d.audio, vdir, media, w, h)
    frames = round(d.total * build.FPS)
    plan = build.conform(raw, d, vdir / f"{sid}_image.mp4", frames)
    raw.unlink(missing_ok=True)
    out = vdir / f"{sid}.mp4"
    build.sh(["ffmpeg", "-y", "-loglevel", "error", "-i", str(plan),
              "-i", str(ep_dir / "audio" / f"{sid}.wav"),
              "-af", f"apad=whole_dur={d.total:.3f}", "-c:v", "copy", "-c:a", "aac",
              "-b:a", "192k", "-t", f"{d.total:.3f}", str(out)])
    import shutil
    shutil.rmtree(media, ignore_errors=True)

    res = densite.carte(plan, [{"id": sid, "type_visuel": fam, "debut_s": 0.0,
                                "fin_s": d.total}],
                        ep_dir / "build" / "pilotes", nom=f"{sid}_densite")
    plan.unlink(missing_ok=True)
    print(f"\nplan    : {out}")
    print(f"densite : {ep_dir / 'build' / 'pilotes' / (sid + '_densite.png')}")
    print(f"R6, calendrier : " + ("; ".join(f"{l:.2f} s a {t:.2f} s" for _, _, t, l in cal) or "aucun temps mort"))
    fig = res["plages"]
    print(f"ecran fige > {densite.MAX_STILL:.0f} s (pixels) : "
          + ("; ".join(f"{p['duree_s']:.1f} s a {p['debut_s']:.1f} s" for p in fig) or "aucun"))
    seg_r = res["segments"][0]
    print(f"part inactive : {100 * seg_r['part_inactive']:.0f} %")


if __name__ == "__main__":
    main()
