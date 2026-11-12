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


def check_revelations(segments, durations, plans_dir=None, sources=(), ep_dir=None):
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
    from briefs import resolve, still_times, opening, MAX_STILL, with_voice
    from components import COMPONENTS, Cues
    from scenes import add_overlays
    import densite

    rows = []
    for s in segments:
        if not (s.get("manim_brief") or {}).get("revelations"):
            continue
        dur = durations[s["id"]].audio
        if ep_dir is not None:
            s = with_voice(s, ep_dir)
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


CHAINE = ("mention", "ecran_fin")


def check_chaine(segments):
    """Un plan de chaine (mention, ecran_fin) est compose par le moteur seul :
    il ne porte ni manim_brief ni overlay_texte. Bloquant, au check comme au
    build. Renvoie la ligne du rapport."""
    fautes = [f"{s['id']} ({s['type_visuel']}) porte {k}" for s in segments
              if s.get("type_visuel") in CHAINE
              for k in ("manim_brief", "overlay_texte") if s.get(k)]
    if fautes:
        raise SystemExit("plans de chaine : " + " ; ".join(fautes)
                         + " - ni manim_brief ni overlay_texte (video/CATALOGUE.md)")
    n = sum(1 for s in segments if s.get("type_visuel") in CHAINE)
    return f"plans de chaine : {n}, sans brief ni overlay" if n else "plans de chaine : aucun"


class _SceneMuette:
    """Tient lieu de scene pour composer un plan de chaine sans le rendre."""

    def add(self, *m):
        return self


def _visible(anim):
    """L'animation touche-t-elle quelque chose qui se voit ? Un encart pose
    hors de l'image (quatrieme encart « centre ») s'anime sans rien montrer."""
    from style import FW, FH
    m = getattr(anim, "mobject", None)
    if m is None:
        return False
    try:
        x, y = m.get_center()[:2]
    except Exception:
        return True
    return abs(x) <= FW / 2 and abs(y) <= FH / 2


def composer(seg, dur, ep_dir=None):
    """Le calendrier du plan (Cues) tel que la scene le jouera, sans rendu."""
    import contextlib
    import io
    from briefs import resolve, with_voice
    from components import COMPONENTS, Cues
    from scenes import add_overlays

    if ep_dir is not None:
        seg = with_voice(seg, ep_dir)
    visual = seg["type_visuel"]
    cues = Cues(dur)
    cues.anchors = {o["ancre"] for o in seg.get("overlay_texte") or []}
    with contextlib.redirect_stderr(io.StringIO()):
        if visual in CHAINE:
            import plans_chaine
            getattr(plans_chaine, visual)(_SceneMuette(), seg, dur, cues)
        else:
            if visual == "manim":
                target, fam = resolve(seg, dur, log=False)
                COMPONENTS[fam](target, cues)
            add_overlays(seg, cues, visual)
    return cues


def calendrier_nouveaute(seg, dur, ep_dir=None):
    """[(debut, fin)] de tout ce qui arrive a l'ecran pendant le plan, tel que
    le moteur le posera : revelations, etiquettes, overlays, mises en avant,
    argent qui circule. Ne compte pas : ce qui s'anime hors de l'image."""
    cues = composer(seg, dur, ep_dir)
    out = []
    for t, anims, rt in cues.items:
        if t >= dur:
            continue
        if any(_visible(a) for a in anims):
            out.append((t, min(t + rt, dur)))
    return sorted(out)


def check_nouveaute(segments, durations, ep_dir):
    """Controle bloquant : aucun intervalle de plus de 4 s sans element
    nouveau, du debut a la fin de la voix de chaque plan, quel que soit son
    type_visuel. Jugee au calendrier du moteur, sans rendu.

    Renvoie (lignes du rapport, fautes) ; l'appelant refuse s'il y a des
    fautes. L'ecran de fin est juge sur toute sa duree, prolongation comprise."""
    from briefs import _gaps, MAX_STILL
    lignes, fautes = [], []
    for s in segments:
        sid, visual = s["id"], s["type_visuel"]
        if visual == "mention":
            # Exception inscrite au catalogue : la carte de mention est une
            # respiration, exclue de R6 au check comme en pixels.
            lignes.append(f"  {sid:<4} {visual:<15} exclue de R6 (exception du catalogue)")
            continue
        if visual == "ecran_fin":
            # Anime par construction jusqu'a la derniere image (courbe
            # parcourue, pictogrammes en derive) : ces mouvements continus ne
            # sont pas au calendrier. Il se juge en pixels, au controle final.
            lignes.append(f"  {sid:<4} {visual:<15} anime en continu par le moteur, juge en "
                          f"pixels au controle final")
            continue
        d = durations[sid]
        dur = d.total if visual == "ecran_fin" else d.audio
        kind = (s.get("manim_brief") or {}).get("composant", "manim") \
            if visual == "manim" else visual
        try:
            cal = calendrier_nouveaute(s, dur, ep_dir)
        except SystemExit as e:
            fautes.append(f"{sid} ({kind}) : calendrier impossible a etablir - {e}")
            lignes.append(f"  {sid:<4} {kind:<15} calendrier impossible")
            continue
        trous = [(a, b) for a, b in _gaps(cal, 0.0, dur) if b - a > MAX_STILL]
        tous = _gaps(cal, 0.0, dur)
        pire = max(tous, key=lambda g: g[1] - g[0]) if tous else (0.0, 0.0)
        lignes.append(f"  {sid:<4} {kind:<15} {len(cal):3d} arrivees, plus long intervalle "
                      f"{pire[1] - pire[0]:5.2f} s (de {pire[0]:.2f} a {pire[1]:.2f} s)"
                      + ("   << REFUS" if trous else ""))
        for a, b in trous:
            fautes.append(f"{sid} ({kind}) : {b - a:.2f} s sans element nouveau, "
                          f"de {a:.2f} a {b:.2f} s")
    return lignes, fautes


def _boite(m):
    return (float(m.get_left()[0]), float(m.get_right()[0]),
            float(m.get_bottom()[1]), float(m.get_top()[1]))


def _chevauche(a, b, marge=0.03):
    """Deux boites (x0, x1, y0, y1) se recouvrent-elles de plus de `marge` ?"""
    return (min(a[1], b[1]) - max(a[0], b[0]) > marge
            and min(a[3], b[3]) - max(a[2], b[2]) > marge)


def _objets(cues):
    """[(objet, premier instant, animation)] de tout ce que le plan pose, les
    groupes d'animations deplies. Les particules qui circulent (Courant) n'ont
    pas de place fixe : leur chemin, deja compte, les represente."""
    from components import Courant
    out, vus = [], set()

    def voir(a, t):
        sous = getattr(a, "animations", None)
        if sous:
            for x in sous:
                voir(x, t)
            return
        m = getattr(a, "mobject", None)
        if m is None or isinstance(a, Courant):
            return
        out.append((m, t, a))

    for t, anims, _ in sorted(cues.items, key=lambda c: c[0]):
        for a in anims:
            voir(a, t)
    for m in cues.static:
        out.append((m, 0.0, None))
    return out


def _nom_element(m):
    x, y = m.get_center()[:2]
    return f"{type(m).__name__} du graphique en ({x:.1f} ; {y:.1f})"


def collisions(seg, dur, ep_dir=None):
    """Fautes de placement d'un plan, jugees sur les boites englobantes de
    tout ce que le moteur y pose :

    - un encart « centre » qui sort de l'image, ou qui recouvre un element du
      graphique, un libelle, ou un autre encart present en meme temps que lui ;
    - un libelle (titre, nom d'axe, d'option, de noeud, de lien, legende,
      source) qui sort de l'image, qui recouvre un autre libelle, ou, pour
      Flux, un noeud, un montant ou le trace d'un lien.

    Un encart est juge sur toute sa presence : de son arrivee a sa sortie en
    fondu (ou a la fin du plan). Le reste du plan est tenu pour present du
    debut a la fin : un encart ne passe pas non plus la ou un element viendra."""
    from style import FW, FH
    from scenes import Efface
    cues = composer(seg, dur, ep_dir)
    objets = _objets(cues)
    sorties = {id(m): t for m, t, a in objets if isinstance(a, Efface)}
    encarts, libelles, graphe, vus = [], [], [], set()
    for m, t, a in objets:
        if id(m) in vus or isinstance(a, Efface):
            continue
        vus.add(id(m))
        if m.width < 1e-6 and m.height < 1e-6:
            continue
        role = getattr(m, "role", None)
        if role == "encart":
            encarts.append((m, t, sorties.get(id(m), dur)))
        elif role == "libelle":
            libelles.append(m)
        else:
            graphe.append(m)
    fautes = []
    bord = (-FW / 2, FW / 2, -FH / 2, FH / 2)

    def hors(b):
        return b[0] < bord[0] or b[1] > bord[1] or b[2] < bord[2] or b[3] > bord[3]

    for i, (e, t0, t1) in enumerate(encarts):
        b = _boite(e)
        if hors(b):
            fautes.append(f"encart {e.nom} sort de l'image")
        touche = [g for g in graphe if _chevauche(b, _boite(g))]
        if touche:
            fautes.append(f"encart {e.nom} recouvre {len(touche)} element(s) du graphique, "
                          f"dont {_nom_element(touche[0])}")
        for l in libelles:
            if _chevauche(b, _boite(l)):
                fautes.append(f"encart {e.nom} recouvre le libelle {l.nom}")
        for f, u0, u1 in encarts[i + 1:]:
            if min(t1, u1) - max(t0, u0) > 1e-6 and _chevauche(b, _boite(f)):
                fautes.append(f"encart {e.nom} recouvre l'encart {f.nom} "
                              f"(ensemble de {max(t0, u0):.2f} a {min(t1, u1):.2f} s)")
    for i, l in enumerate(libelles):
        b = _boite(l)
        if hors(b):
            fautes.append(f"libelle {l.nom} sort de l'image")
        for m in libelles[i + 1:]:
            if _chevauche(b, _boite(m)):
                fautes.append(f"libelle {l.nom} recouvre le libelle {m.nom}")
        if l.nom.startswith(("noeud_", "lien_")):
            noms = sorted({nom for nom, o in getattr(cues, "obstacles", []) if _chevauche(b, o)})
            if noms:
                fautes.append(f"libelle {l.nom} recouvre {', '.join(noms)}")
    # Etiquettes de valeur : chacune au plus pres de ce qu'elle chiffre.
    from components import ANCRE_MAX, ANCRE_TOL, dist_boite, dist_boites
    etiquettes = getattr(cues, "etiquettes", [])
    for lab, cible, serie, nom in etiquettes:
        b = _boite(lab)
        texte = getattr(lab, "text", "?")
        d = dist_boites(b, cible)
        if d > ANCRE_MAX + 1e-6:
            fautes.append(f"etiquette « {texte} » de {nom} a {d:.2f} de son point "
                          f"(maximum {ANCRE_MAX:.2f})")
        for _, autre, _, nom2 in etiquettes:
            if nom2 != nom and autre != cible and dist_boites(b, autre) < d - ANCRE_TOL:
                fautes.append(f"etiquette « {texte} » de {nom} plus proche de {nom2} "
                              f"({dist_boites(b, autre):.2f}) que de son point ({d:.2f})")
        for k, pts in getattr(cues, "courbes", {}).items():
            if isinstance(serie, int) and k != serie:
                dk = min(dist_boite(b, p) for p in pts)
                if dk < d - ANCRE_TOL:
                    fautes.append(f"etiquette « {texte} » de {nom} plus proche de la courbe "
                                  f"de la serie {k + 1} ({dk:.2f}) que de son point ({d:.2f})")
    return fautes, len(encarts), len(libelles)


def check_placement(segments, durations, ep_dir):
    """Controle bloquant : aucun encart ni libelle ne recouvre quoi que ce
    soit ni ne sort de l'image, a aucun instant (voir `collisions`). Les plans
    de chaine, composes par le moteur sans overlay, n'en portent pas.
    Renvoie (lignes du rapport, fautes)."""
    lignes, fautes = [], []
    for s in segments:
        sid, visual = s["id"], s["type_visuel"]
        if visual in CHAINE:
            continue
        kind = (s.get("manim_brief") or {}).get("composant", "manim") \
            if visual == "manim" else visual
        try:
            f, n_e, n_l = collisions(s, durations[sid].audio, ep_dir)
        except SystemExit:
            # Composant que le moteur ne sait pas construire : le build s'y
            # arretera de lui-meme ; rien a juger ici.
            lignes.append(f"  {sid:<4} {kind:<15} non juge : composant non construit")
            continue
        lignes.append(f"  {sid:<4} {kind:<15} {n_e} encart(s), {n_l:2d} libelle(s)"
                      + (f"   << REFUS ({len(f)})" if f else ""))
        fautes += [f"{sid} ({kind}) : {x}" for x in f]
    return lignes, fautes


def refuser_placement(fautes):
    raise SystemExit(f"REFUS : {len(fautes)} faute(s) de placement (encart ou libelle qui "
                     f"recouvre un element ou sort de l'image, controle bloquant) :\n  "
                     + "\n  ".join(fautes)
                     + "\nRaccourcis le libelle ou deplace l'element (video/CATALOGUE.md, "
                       "section 3).")


def refuser_nouveaute(fautes):
    from briefs import MAX_STILL
    raise SystemExit(f"REFUS : {len(fautes)} intervalle(s) de plus de {MAX_STILL:.0f} s sans "
                     f"element nouveau (R6, controle bloquant) :\n  " + "\n  ".join(fautes)
                     + "\nAjoute une revelation ou un overlay visible dans chaque intervalle "
                       "(video/CATALOGUE.md, R6).")


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
    for p in res.get("plages_exclues") or []:
        print(f"              hors R6 (exception du catalogue) : {p['segment']} "
              f"({p['type_visuel']}), {p['duree_s']:.1f} s a partir de "
              f"{p['debut_segment_s']:.1f} s")
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

    from timeline import (load_durations, build_timeline, write_timeline, print_timeline,
                          ajuster, Duree)
    import nombres
    nombres.set_locale(args.locale)

    script = json.loads((ep_dir / "script.json").read_text(encoding="utf-8"))
    # ecran_fin : prolonge en silence jusqu'a 20 s (timeline.ajuster).
    durations = ajuster(script, load_durations(ep_dir / "audio" / "durations.json"))
    segments = script["segments"]
    chaine_line = check_chaine(segments)

    # Contre quelle version du catalogue le script a-t-il ete ecrit ? Un ecart
    # est signale a chaque build, sans rien bloquer.
    cat_line = check_catalogue(args.ep, script)

    # La timeline est la seule source des timecodes : ecrite avant tout rendu,
    # elle sert aussi aux sous-titres et au controle final.
    tl = build_timeline(args.ep, script, durations, ep_dir, strict=True)
    # Les timecodes ecrits dans metadonnees.md doivent etre ceux du montage.
    from timeline import _titres_meta
    ecarts = [(m[0], c["tc"], c["titre"]) for m, c in zip(_titres_meta(ep_dir), tl["chapitres"])
              if m[0] != c["tc"]]
    if ecarts:
        from timeline import warn
        warn(f"{args.ep} : metadonnees.md ne porte pas les timecodes du montage : "
             + "; ".join(f"{a} au lieu de {b} ({t})" for a, b, t in ecarts))
    write_timeline(tl, ep_dir / "build")
    if args.check:
        print_timeline(tl)
        print(f"\n  {cat_line}")
        print(f"  {chaine_line}")
        check_revelations(segments, durations, ep_dir / "video" / "plans_cales",
                          (ep_dir / "script.json", ep_dir / "audio" / "durations.json"),
                          ep_dir=ep_dir)
        print(f"\n  ecrit : {ep_dir / 'build' / 'timeline.json'}")
        print(f"          {ep_dir / 'build' / 'chapitres.txt'}")
        from briefs import MAX_STILL
        lignes, fautes = check_nouveaute(segments, durations, ep_dir)
        print(f"\n  element nouveau : aucun intervalle de plus de {MAX_STILL:.0f} s, tout "
              f"type de plan (bloquant)")
        print("\n".join(lignes))
        lignes_p, fautes_p = check_placement(segments, durations, ep_dir)
        print("\n  placement : aucun encart ni libelle ne recouvre un element ni ne sort de "
              "l'image (bloquant)")
        print("\n".join(lignes_p))
        refus = []
        for f, refuser in ((fautes, refuser_nouveaute), (fautes_p, refuser_placement)):
            if f:
                try:
                    refuser(f)
                except SystemExit as e:
                    refus.append(str(e))
        if refus:
            raise SystemExit("\n".join(refus))
        print("  controles bloquants : passes")
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
            from briefs import with_voice
            # Un ecran de fin s'anime toute sa duree, prolongation comprise :
            # rien n'est tenu fige pendant le silence.
            vit = d.total if seg["type_visuel"] == "ecran_fin" else d.audio
            render_segment(with_voice(seg, ep_dir), vit, scenes_dir, media_dir, w, h)
        cale = Duree(d.total, 0.0, d.total) if seg["type_visuel"] == "ecran_fin" else d
        conform(out, cale, conf_dir / f"{sid}.mp4", frames[sid])
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

    # --- musique de fin et mastering (config/charte.json, musique_fin.py) ---
    import musique_fin
    voix, sr = musique_fin.lire_wav(voice)
    fin = next((r for r in tl["segments"]
                if any(s["id"] == r["id"] and s["type_visuel"] == "ecran_fin"
                       for s in segments)), None)
    piste, rapport, _ = musique_fin.bande_finale(
        voix, sr, fin and fin["fin_voix_s"], musique_fin.duree_image(mute),
        fin and (fin["debut_s"], fin["fin_voix_s"]))
    bande = vdir / "bande.wav"
    musique_fin.ecrire_wav(bande, piste, sr)

    final = vdir / f"{args.ep}.mp4"
    sh(["ffmpeg", "-y", "-loglevel", "error", "-i", str(mute), "-i", str(bande),
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
    if "mastering" in rapport:
        m = rapport["mastering"]
        print(f"mastering   : {m['avant_lufs']} -> {m['apres_lufs']} LUFS, crete "
              f"{m['avant_dbtp']} -> {m['apres_dbtp']} dBTP, gain {m['gain_db']:+.2f} dB, "
              f"limiteur sur {100 * m['part_limitee']:.1f} % des echantillons")
    if "musique_fin" in rapport:
        mf = rapport["musique_fin"]
        f = mf.get("apres_mastering", mf["avant_mastering"])
        print(f"musique fin : des {mf['debut_s']:.2f} s, {f['ecart_sous_voix_db']} dB sous la "
              f"voix, fin a {f['musique_fin_lufs']} LUFS" + (f"  {mf['ATTENTION']}"
                                                              if "ATTENTION" in mf else ""))
    print(f"timeline    : {ep_dir / 'build' / 'timeline.json'}")
    print(f"chapitres   : {ep_dir / 'build' / 'chapitres.txt'}")
    if vd < 480:
        print("ATTENTION : sous 8 minutes, les coupures intermediaires ne se debloquent pas")
    for k, m in enumerate(tl["midrolls"], 1):
        print(f"mid-roll {k} : {m['tc']}  (apres {m['apres']})")
    check_density(final, tl, segments, ep_dir / "build")
    if any(s["type_visuel"] == "ecran_fin" for s in segments):
        import plans_chaine
        z = plans_chaine.exporter_zones(ep_dir / "build" / "ecran_fin_zones.png",
                                        vdir / "_zones")
        shutil.rmtree(vdir / "_zones", ignore_errors=True)
        fin = next(r for r in tl["segments"]
                   if any(s["id"] == r["id"] and s["type_visuel"] == "ecran_fin"
                          for s in segments))
        print(f"ecran fin   : {fin['id']}, voix {fin['duree_audio_s']:.2f} s + "
              f"{fin['silence_apres_s']:.2f} s de prolongation silencieuse ; zones : {z}")


if __name__ == "__main__":
    main()
