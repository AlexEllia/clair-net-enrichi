# -*- coding: utf-8 -*-
"""Montage d'un episode : rendu des plans, collage, mixage.

    python video/build.py --ep EP001
    python video/build.py --ep EP001 --only S01 S26 --preview

La duree de chaque plan est celle de son fichier audio. Rien d'autre ne decide
du montage : le script fixe le contenu, la voix fixe le tempo.
"""

import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

PROJECT = ROOT.parent
FPS = 30


def sh(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", **kw)
    if r.returncode != 0:
        sys.stderr.write((r.stderr or "")[-4000:] + "\n")
        raise SystemExit(f"echec : {' '.join(str(c) for c in cmd[:6])}...")
    return r


def probe(path):
    r = sh(["ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "csv=p=0", str(path)])
    return float(r.stdout.strip())


# --- Rendu d'un plan ---------------------------------------------------------

def render_segment(seg, dur, out_dir, media_dir, width, height):
    from manim import tempconfig
    from scenes import SegmentScene
    from style import BG

    dest = out_dir / f"{seg['id']}.mp4"
    with tempconfig({
        "pixel_width": width,
        "pixel_height": height,
        "frame_rate": FPS,
        "media_dir": str(media_dir),
        "output_file": seg["id"],
        "disable_caching": True,
        "flush_cache": True,
        "verbosity": "ERROR",
        "progress_bar": "none",
        "background_color": BG,
    }):
        scene = SegmentScene(seg=seg, dur=dur,
                             anchors_path=out_dir / f"{seg['id']}.anchors.json")
        scene.render()
        src = Path(scene.renderer.file_writer.movie_file_path)
    shutil.move(str(src), str(dest))
    return dest


def conform(src, d, dest, frames):
    """Cale le plan sur sa voix puis tient la derniere image pendant le silence.

    Le rendu est coupe a `d.audio` - rien ne bouge apres le dernier mot - puis
    la derniere image est clonee jusqu'a la fin du plan. Un rendu trop court est
    prolonge de la meme facon.

    La longueur est donnee en images, pas en secondes : `frames` vient des
    bornes absolues de la timeline arrondies a l'image, pour que les arrondis
    ne s'accumulent pas d'un plan a l'autre."""
    sh(["ffmpeg", "-y", "-loglevel", "error", "-i", str(src),
        "-vf", f"trim=duration={d.audio:.3f},setpts=PTS-STARTPTS,"
               f"tpad=stop_mode=clone:stop_duration={d.total + 3:.3f}",
        "-r", str(FPS), "-frames:v", str(frames),
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-an", str(dest)])
    return dest


# --- Montage -----------------------------------------------------------------

def concat(paths, dest, extra=None):
    lst = dest.parent / (dest.stem + "_list.txt")
    lst.write_text("".join(f"file '{Path(p).resolve().as_posix()}'\n" for p in paths), encoding="utf-8")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
           "-i", str(lst)] + (extra or []) + [str(dest)]
    sh(cmd)
    lst.unlink(missing_ok=True)
    return dest


def voice_track(ep_dir, order, durations, dest):
    """Les voix bout a bout, chacune suivie de sa respiration."""
    tmp = dest.parent / "_silences"
    tmp.mkdir(exist_ok=True)
    parts = []
    for sid in order:
        parts.append(ep_dir / "audio" / f"{sid}.wav")
        sil = durations[sid].silence
        if sil > 0:
            p = tmp / f"sil_{sil:.3f}.wav"
            if not p.exists():
                sh(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
                    "-i", "anullsrc=r=44100:cl=mono", "-t", f"{sil:.3f}",
                    "-c:a", "pcm_s16le", str(p)])
            parts.append(p)
    # Re-encodage en PCM plutot que -c copy : les silences et les voix doivent
    # partager le meme format, et la duree des silences doit etre exacte.
    concat(parts, dest, extra=["-c:a", "pcm_s16le", "-ar", "44100", "-ac", "1"])
    shutil.rmtree(tmp, ignore_errors=True)
    return dest


def _md5_variants(data):
    """Empreintes md5 d'un meme contenu en fins de ligne d'origine, LF et
    CRLF : git rend le catalogue en CRLF sur Windows et le garde en LF, sans
    que son contenu change."""
    import hashlib
    lf = data.replace(b"\r\n", b"\n")
    return {hashlib.md5(v).hexdigest() for v in (data, lf, lf.replace(b"\n", b"\r\n"))}


def _catalogue_commit(md5):
    """(commit, date) de la version de video/CATALOGUE.md dont l'empreinte est
    `md5`, cherchee dans l'historique git - lecture seule. None si aucune."""
    try:
        log = subprocess.run(["git", "log", "--format=%h %ad", "--date=short", "--",
                              "video/CATALOGUE.md"], cwd=PROJECT, capture_output=True,
                             text=True, timeout=20)
        for line in log.stdout.split("\n"):
            if not line.strip():
                continue
            h, date = line.split(" ", 1)
            blob = subprocess.run(["git", "show", f"{h}:video/CATALOGUE.md"], cwd=PROJECT,
                                  capture_output=True, timeout=20)
            if blob.returncode == 0 and md5 in _md5_variants(blob.stdout):
                return h, date
    except (OSError, subprocess.SubprocessError):
        pass
    return None


def check_catalogue(ep, script):
    """Le script a-t-il ete ecrit contre la version actuelle du catalogue ?

    Chaque script.json porte meta.catalogue_md5, l'empreinte de
    video/CATALOGUE.md que la redaction a lu. Un ecart n'est pas bloquant :
    le catalogue a change depuis, et le script peut ne plus en suivre toutes
    les regles. Renvoie la ligne a afficher dans le rapport de make check.
    """
    want = str((script.get("meta") or {}).get("catalogue_md5") or "").strip().lower()
    if not want:
        return "catalogue : le script ne porte pas meta.catalogue_md5, version d'origine inconnue"
    if want in _md5_variants((ROOT / "CATALOGUE.md").read_bytes()):
        return f"catalogue : script ecrit contre la version actuelle ({want[:8]})"
    found = _catalogue_commit(want)
    if found:
        where = (f"celle du commit {found[0]} ({found[1]}) ; ce qui a change depuis : "
                 f"git diff {found[0]} -- video/CATALOGUE.md")
    else:
        where = "une version absente de l'historique git (catalogue non commite ?)"
    msg = (f"{ep} : le script a ete ecrit contre une autre version du catalogue - {where}. "
           f"Il peut ne plus en suivre toutes les regles.")
    from timeline import warn
    warn(msg)
    return f"catalogue : AUTRE VERSION ({want[:8]}) - {where}"


def check_revelations(segments, durations, plans_dir=None, sources=()):
    """Deux defauts distincts des plans manim :

    - l'ouverture inerte : le cadre est construit, aucune donnee ne bouge
      encore (correctif : premiere donnee plus tot dans le script) ;
    - R6, les temps morts internes de plus de 4 s entre la premiere donnee et
      la derniere revelation (correctif : rapprocher ou ajouter des
      revelations).

    R6 se juge sur ce que voit le spectateur : quand le plan est deja rendu
    (`plans_dir`/Sxx.mp4) et plus recent que `sources` (script, durees de la
    voix), ses temps morts sont mesures en pixels (densite.py)
    et ce sont eux qui declenchent l'avertissement. Sinon, ou en complement,
    le calendrier : exact quand le composant se construit (animations
    reellement posees, overlays compris), estime depuis le script sinon. La
    mesure en pixels voit un temps mort ~0,5 s plus long que le calendrier :
    un fondu adouci ne se voit qu'a ~20 % d'opacite."""
    import contextlib
    import io
    from briefs import resolve, still_times, opening, MAX_STILL
    from components import COMPONENTS, Cues
    from scenes import add_overlays
    import densite

    rows = []
    for s in segments:
        if not (s.get("manim_brief") or {}).get("revelations"):
            continue
        dur = durations[s["id"]].audio
        intervals, target, meta = None, s, None
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                target, fam = resolve(s, dur, log=False)
                cues = Cues(dur)
                cues.anchors = {o["ancre"] for o in s.get("overlay_texte") or []}
                COMPONENTS[fam](target, cues)
                add_overlays(s, cues, "manim")
            intervals = [(t, t + rt) for t, _, rt in cues.items]
            meta = cues.meta
        except SystemExit:
            pass
        op = opening(target, meta, dur)
        stills = still_times(target, dur, intervals)
        pixels, perime = None, False
        plan = plans_dir / f"{s['id']}.mp4" if plans_dir else None
        if plan is not None and plan.exists():
            # Un rendu plus ancien que le script ou que la voix montre un autre
            # plan : on ne le mesure pas, le calendrier fait foi.
            perime = any(p.exists() and plan.stat().st_mtime < p.stat().st_mtime
                         for p in sources)
            if not perime:
                times = sorted(float(r["t_rel_s"]) for r in s["manim_brief"]["revelations"])
                first = op[1] if op and op[1] is not None else times[0]
                pixels = densite.plages_plan(plan, first, times[-1])
        rows.append((s["id"], op, stills, intervals is None, pixels, perime))

    print(f"\n  plans manim : ouverture inerte et temps morts internes (> {MAX_STILL:.0f} s)")
    print(f"  {'seg':<4} {'cadre':>6} {'1re donnee':>11} {'ouverture':>10}  "
          f"{'R6, calendrier':<34} {'R6, pixels du plan rendu':<28} calendrier")
    for sid, op, stills, est, pixels, perime in rows:
        f, d, inert, _ = op if op else (0, 0, 0, est)
        internal = "; ".join(f"{l:.2f} s ({a} -> {b})" for a, b, _, l in stills) or "-"
        if perime:
            vu = "rendu perime, non mesure"
        elif pixels is None:
            vu = "pas de rendu"
        else:
            vu = "; ".join(f"{l:.1f} s a {a:.1f} s" for a, l in pixels) or "-"
        print(f"  {sid:<4} {f:5.2f}s {d:10.2f}s {inert:9.2f}s  {internal:<34} {vu:<28} "
              f"{'estime' if est else 'exact'}")
        if inert > MAX_STILL:
            print(f"[ATTENTION] {sid} : ouverture inerte de {inert:.2f} s", file=sys.stderr)
        if pixels is not None:
            for a, l in pixels:
                print(f"[ATTENTION] {sid} : ecran fige {l:.1f} s a partir de {a:.1f} s "
                      f"(R6, mesure en pixels sur le plan rendu)", file=sys.stderr)
        else:
            for a, b, _, l in stills:
                print(f"[ATTENTION] {sid} : ecran fige {l:.2f} s entre {a!r} et {b!r} "
                      f"(R6, calendrier : aucun plan rendu a jour a mesurer)", file=sys.stderr)
    if any(r[3] for r in rows):
        print("  estime = segment pas encore traduit : type de chaque partie devine sur son "
              "nom ; une barre monte jusqu'a 6 s avant son mot, une courbe, une aire ou une "
              "bande est supposee ne rien anticiper (prudent)")
    if any(r[4] is not None for r in rows):
        print("  R6 se juge en pixels quand le plan est rendu (video/densite.py) : un fondu ne "
              "se voit qu'a ~20 % d'opacite, la mesure compte donc ~0,5 s de plus que le "
              "calendrier.")


def check_density(final, tl, segments, dest):
    """Controle final : carte de densite de l'episode monte, en pixels.

    Avertit pour chaque plage figee de plus de 4 s, quel que soit le type de
    plan. Ne bloque rien : le montage est deja ecrit."""
    import densite
    kinds = {s["id"]: (s.get("manim_brief") or {}).get("composant", "manim")
             if s["type_visuel"] == "manim" else s["type_visuel"] for s in segments}
    segs = [{"id": r["id"], "type_visuel": kinds.get(r["id"], "?"),
             "debut_s": r["debut_s"], "fin_s": r["fin_s"]} for r in tl["segments"]]
    res = densite.carte(final, segs, dest)
    print(f"densite     : {dest / 'densite.png'}  (ecran fige > {densite.MAX_STILL:.0f} s : "
          f"{res['total_fige_s']:.0f} s sur {res['duree_s']:.0f} s, "
          f"{100 * res['part_fige']:.0f} %, {len(res['plages'])} plages)")
    for p in res["plages"]:
        print(f"[ATTENTION] {p['segment']} ({p['type_visuel']}) : ecran fige {p['duree_s']:.1f} s "
              f"a partir de {p['debut_segment_s']:.1f} s", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ep", required=True)
    ap.add_argument("--only", nargs="*", default=None,
                    help="ne rendre que ces segments (le montage est alors partiel)")
    ap.add_argument("--preview", action="store_true", help="960x540, rendu rapide")
    ap.add_argument("--skip-render", action="store_true",
                    help="reutilise les plans deja rendus")
    ap.add_argument("--check", action="store_true",
                    help="ecrit et affiche la timeline, sans aucun rendu")
    ap.add_argument("--locale", default="fr",
                    help="typographie des nombres a l'ecran (fr, en)")
    args = ap.parse_args()

    ep_dir = PROJECT / "episodes" / args.ep
    if not ep_dir.exists():
        raise SystemExit(f"episode introuvable : {ep_dir}")

    from timeline import load_durations, build_timeline, write_timeline, print_timeline
    import nombres
    nombres.set_locale(args.locale)

    script = json.loads((ep_dir / "script.json").read_text(encoding="utf-8"))
    durations = load_durations(ep_dir / "audio" / "durations.json")
    segments = script["segments"]

    # Contre quelle version du catalogue le script a-t-il ete ecrit ? Un ecart
    # est signale a chaque build, sans rien bloquer.
    cat_line = check_catalogue(args.ep, script)

    # La timeline est la seule source des timecodes : ecrite avant tout rendu,
    # elle sert aussi aux sous-titres et au controle final.
    tl = build_timeline(args.ep, script, durations, ep_dir)
    write_timeline(tl, ep_dir / "build")
    if args.check:
        print_timeline(tl)
        print(f"\n  {cat_line}")
        check_revelations(segments, durations, ep_dir / "video" / "plans_cales",
                          (ep_dir / "script.json", ep_dir / "audio" / "durations.json"))
        print(f"\n  ecrit : {ep_dir / 'build' / 'timeline.json'}")
        print(f"          {ep_dir / 'build' / 'chapitres.txt'}")
        return

    vdir = ep_dir / "video"
    scenes_dir, conf_dir, media_dir = vdir / "plans", vdir / "plans_cales", vdir / "_manim"
    for d in (scenes_dir, conf_dir, media_dir):
        d.mkdir(parents=True, exist_ok=True)

    w, h = (960, 540) if args.preview else (1920, 1080)
    todo = [s for s in segments if not args.only or s["id"] in args.only]
    frames = {r["id"]: round(r["fin_s"] * FPS) - round(r["debut_s"] * FPS)
              for r in tl["segments"]}

    # --- rendu ---------------------------------------------------------------
    t0 = time.time()
    for i, seg in enumerate(todo, 1):
        sid = seg["id"]
        d = durations[sid]
        out = scenes_dir / f"{sid}.mp4"
        if args.skip_render and out.exists():
            print(f"[{i:2d}/{len(todo)}] {sid}  (deja rendu)", flush=True)
        else:
            comp = seg["manim_brief"]["composant"] if seg["type_visuel"] == "manim" else seg["type_visuel"]
            print(f"[{i:2d}/{len(todo)}] {sid}  {comp:<18} {d.audio:5.2f}s"
                  f" + {d.silence:.2f}s tenus", flush=True)
            # La scene ne dure que le temps de la voix : aucune animation ne
            # peut partir pendant la respiration, qui est ajoutee au calage.
            render_segment(seg, d.audio, scenes_dir, media_dir, w, h)
        conform(out, d, conf_dir / f"{sid}.mp4", frames[sid])
    print(f"-- plans rendus en {time.time() - t0:.0f}s", flush=True)

    if args.only:
        print("montage partiel : plans dans", conf_dir)
        return

    # --- bande son -----------------------------------------------------------
    order = [s["id"] for s in segments]
    voice = voice_track(ep_dir, order, durations, vdir / "voix.wav")
    offsets = {r["id"]: r["debut_s"] for r in tl["segments"]}

    # --- sous-titres ---------------------------------------------------------
    from subtitles import build_srt
    n_cards = build_srt(ep_dir / "audio" / "alignments", order, offsets,
                        vdir / f"{args.ep}.srt")

    # --- image + son ---------------------------------------------------------
    mute = vdir / "_image.mp4"
    concat([conf_dir / f"{sid}.mp4" for sid in order], mute, extra=["-c", "copy"])

    final = vdir / f"{args.ep}.mp4"
    sh(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mute), "-i", str(voice),
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
        "-movflags", "+faststart", "-shortest", str(final)])
    mute.unlink(missing_ok=True)
    shutil.rmtree(media_dir, ignore_errors=True)

    # --- controle ------------------------------------------------------------
    vd, ad = probe(final), tl["duree_totale_s"]
    mm, ss = divmod(int(vd), 60)
    print()
    print(f"video   : {final}")
    print(f"duree   : {mm}:{ss:02d}  ({vd:.2f}s, timeline {ad:.2f}s, ecart {vd - ad:+.2f}s)")
    print(f"sous-titres : {vdir / (args.ep + '.srt')}  ({n_cards} cartons)")
    print(f"timeline    : {ep_dir / 'build' / 'timeline.json'}")
    print(f"chapitres   : {ep_dir / 'build' / 'chapitres.txt'}")
    if vd < 480:
        print("ATTENTION : sous 8 minutes, les coupures intermediaires ne se debloquent pas")
    for k, m in enumerate(tl["midrolls"], 1):
        print(f"mid-roll {k} : {m['tc']}  (apres {m['apres']})")
    check_density(final, tl, segments, ep_dir / "build")


if __name__ == "__main__":
    main()
