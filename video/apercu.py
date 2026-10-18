# -*- coding: utf-8 -*-
"""Apercu d'un plan Bars, a cote du montage, avec le tableau de ses barres.

    python video/apercu.py EP001b S17
    python video/apercu.py EP001c S17 --regle v3-phrase --brief video/pilotes/X.json

Rend le plan en 960x540 avec sa voix dans episodes/EPxxx/build/apercus/
(jamais dans video/plans : le montage n'est pas touche), puis ecrit le
tableau : barre, debut de croissance, arrivee, fin de la phrase precedente,
apparition de la source, et plus long intervalle fige mesure en pixels.

--regle  BARS_RULE le temps de l'apercu (v3 par defaut, celle du code).
--brief  un brief de video/pilotes/ qui remplace les champs visuels du
         segment, sans toucher a script.json.
"""

import argparse
import copy
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
PROJECT = ROOT.parent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ep")
    ap.add_argument("sid")
    ap.add_argument("--regle", default=None)
    ap.add_argument("--brief", default=None)
    ap.add_argument("--nom", default=None, help="nom du fichier (sans extension)")
    a = ap.parse_args()

    import build
    import components
    import densite
    import nombres
    from briefs import resolve, with_voice
    from components import COMPONENTS, Cues, _bar_release
    from scenes import add_overlays
    from timeline import load_durations
    nombres.set_locale("fr")
    if a.regle:
        components.BARS_RULE = a.regle
    regle = components.BARS_RULE

    ep_dir = PROJECT / "episodes" / a.ep
    script = json.loads((ep_dir / "script.json").read_text(encoding="utf-8"))
    seg = copy.deepcopy(next(s for s in script["segments"] if s["id"] == a.sid))
    if a.brief:
        b = json.loads(Path(a.brief).read_text(encoding="utf-8"))
        for k in ("type_visuel", "manim_brief", "overlay_texte"):
            seg[k] = copy.deepcopy(b["remplace"][k])
        seg["_pilote"] = True
    seg = with_voice(seg, ep_dir)
    d = load_durations(ep_dir / "audio" / "durations.json")[a.sid]

    # Calendrier, sans rendu.
    target, fam = resolve(seg, d.audio, log=False)
    cues = Cues(d.audio)
    cues.anchors = {o["ancre"] for o in seg.get("overlay_texte") or []}
    COMPONENTS[fam](target, cues)
    add_overlays(seg, cues, "manim")
    grows = sorted((t, rt) for t, anims, rt in cues.items
                   if any(type(x).__name__ == "GrowBar" for x in anims))
    elements = target.get("_elements") or {}
    revs = sorted((r for r in target["manim_brief"].get("revelations") or []
                   if str(elements.get(r["element"], r["element"])).startswith("bar_")),
                  key=lambda r: float(r["t_rel_s"]))
    keys = [elements.get(r["element"], r["element"]) for r in revs]
    src_texts = {o["ancre"]: o["texte_fr"] for o in seg.get("overlay_texte") or []
                 if o["ancre"].startswith("source_")}

    out_dir = ep_dir / "build" / "apercus"
    out_dir.mkdir(parents=True, exist_ok=True)
    nom = a.nom or f"{a.sid}_{regle}"
    media = out_dir / "_manim"
    raw = build.render_segment(seg, d.audio, out_dir, media, 960, 540)
    plan = build.conform(raw, d, out_dir / f"{nom}_image.mp4", round(d.total * build.FPS))
    raw.unlink(missing_ok=True)
    (out_dir / f"{a.sid}.anchors.json").unlink(missing_ok=True)
    mp4 = out_dir / f"{nom}.mp4"
    build.sh(["ffmpeg", "-y", "-loglevel", "error", "-i", str(plan),
              "-i", str(ep_dir / "audio" / f"{a.sid}.wav"),
              "-af", f"apad=whole_dur={d.total:.3f}", "-c:v", "copy", "-c:a", "aac",
              "-b:a", "192k", "-t", f"{d.total:.3f}", str(mp4)])
    shutil.rmtree(media, ignore_errors=True)
    actif, _ = densite.mesurer(plan)
    figes = densite.plages(actif, minimum=0.0)
    plus_long = max(figes, key=lambda p: p[1]) if figes else (0.0, 0.0)
    plan.unlink(missing_ok=True)

    lignes = [f"{a.ep} {a.sid} - BARS_RULE {regle} - voix {d.audio:.2f} s",
              "| Barre | Debut de croissance | Arrivee | Fin de phrase precedente | Source | "
              "Mise en avant |",
              "|---|---|---|---|---|---|"]
    mises = {k: (c, f) for k, c, f in cues.meta.get("mises_en_avant") or []}
    for i, (k, r) in enumerate(zip(keys, revs)):
        t0, rt = grows[i] if i < len(grows) else (None, None)
        fin = (_bar_release(seg.get("_voix"), revs[i - 1].get("declencheur"),
                            r.get("declencheur"), "v3") if i else None)
        g = k.split("_")[1]
        src = (f"{cues.anchor_times.get('source_' + g, 0):.2f} s"
               if f"source_{g}" in src_texts else "-")
        surgit = " (surgit)" if rt is not None and abs(rt - components.LABEL_RT) < 1e-6 and i else ""
        mav = f"{mises[k][0]:.2f} s / {mises[k][1]:.2f} s" if k in mises else "-"
        lignes.append(f"| {k} | {t0:.2f} s{surgit} | {float(r['t_rel_s']):.2f} s | "
                      f"{'-' if fin is None else f'{fin:.2f} s'} | {src} | {mav} |")
    lignes.append(f"Plus long intervalle fige (pixels) : {plus_long[1]:.1f} s, a partir de "
                  f"{plus_long[0]:.1f} s")
    lignes.append("Intervalles figes de plus de 4 s : " + ("; ".join(
        f"{d:.1f} s a {t:.1f} s" for t, d in figes if d > densite.MAX_STILL) or "aucun"))
    (out_dir / f"{nom}.md").write_text("\n".join(lignes) + "\n", encoding="utf-8")
    print("\n".join(lignes))
    print(f"apercu : {mp4}")


if __name__ == "__main__":
    main()
