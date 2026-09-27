# -*- coding: utf-8 -*-
"""Non-regression des calendriers, sans rendu.

    python video/non_regression.py                 compare aux references
    python video/non_regression.py --fige          ecrit les references manquantes
                                                   (jamais celles des plans valides)
    python video/non_regression.py --nouvelle-version EP001b_S09 --motif "..."
                                                   archive la version courante d'un
                                                   plan valide et fige le calendrier
                                                   actuel comme version suivante

Par ordre d'importance :

1. Les plans VALIDES A L'ECRAN - approuves par un oeil humain (S09 et S17 de
   l'EP001b). Leur reference est versionnee : chaque version garde sa date,
   son motif, la regle de cadre qui l'a produite, ses valeurs clefs, son
   nombre d'images et son calendrier complet. Rien n'est jamais ecrase : une
   nouvelle version s'ajoute, l'ancienne est archivee, et seule une
   modification signalee, previsualisee et approuvee en justifie une.
   Le test verifie la version courante, puis que chaque version archivee
   reste reproductible avec sa propre regle : c'est ce qui garantit le retour
   en arriere. Pour revenir a une version archivee : FRAME_RULE dans
   components.py, et "courante" dans le fichier de reference.
2. Les 12 plans manim de l'EP001.
3. L'exemple a deux courbes.

Un calendrier est la liste (depart, duree, animations) que le composant et
les overlays deposent, telle que la scene la jouera. Les constantes de
rythme sont verifiees aussi : elles ne sont plus des defauts ajustables.
"""

import contextlib
import datetime
import io
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
PROJECT = HERE.parent
REF = HERE / "reference"

# Rythme valide a l'ecran. Ne pas modifier sans accord.
RYTHME = {"FRAME_MAX": 4.0, "FRAME_MIN": 1.0, "CONTINUOUS_MAX": 6.0,
          "PUNCTUAL_MAX": 1.5, "LABEL_RT": 0.3, "GAP": 0.2, "MIN_RT": 0.3}

# Libelles des valeurs clefs, par plan valide.
LIBELLES = {
    "EP001b_S09": {
        "frame_end": "construction du cadre, fin",
        "trace_1_debut": "depart de la courbe a 5 %",
        "label_165": "annee 20, courbe a 5 % (165 %)",
        "label_330": "annee 30, courbe a 5 % (330 %)",
        "trace_2_debut": "courbe a 1 %, debut",
        "trace_2_fin": "courbe a 1 %, fin",
        "label_22": "22 %",
        "facteur": "x4,3",
    },
    "EP001b_S17": {
        "frame_end": "construction du cadre, fin",
        "barre_1_debut": "barre 1 : depart", "barre_1_fin": "barre 1 atteint 42",
        "barre_2_debut": "barre 2 : depart", "barre_2_fin": "barre 2 atteint 28",
        "barre_3_debut": "barre 3 : depart", "barre_3_fin": "barre 3 atteint 15",
        "barre_4_debut": "barre 4 : depart", "barre_4_fin": "barre 4 atteint 9",
    },
}


def _calendar(seg, dur):
    from components import COMPONENTS, Cues
    from scenes import add_overlays
    from briefs import resolve
    with contextlib.redirect_stderr(io.StringIO()):
        target, fam = resolve(seg, dur, log=False)
        cues = Cues(dur)
        cues.anchors = {o["ancre"] for o in seg.get("overlay_texte") or []}
        COMPONENTS[fam](target, cues)
        add_overlays(seg, cues, seg["type_visuel"])
    rows = sorted([round(t, 3), round(min(rt, dur - t), 3),
                   "+".join(type(a).__name__ for a in anims)]
                  for t, anims, rt in cues.items if t < dur)
    return rows, cues


def _load(ep):
    ep_dir = PROJECT / "episodes" / ep
    script = json.loads((ep_dir / "script.json").read_text(encoding="utf-8"))
    from timeline import load_durations
    return script, load_durations(ep_dir / "audio" / "durations.json"), ep_dir


def _segment(ep, sid):
    s, d, _ = _load(ep)
    return next(g for g in s["segments"] if g["id"] == sid), d[sid].audio


def _shot(name):
    ep, sid = name.split("_")
    return _calendar(*_segment(ep, sid))


def values_S09(rows, cues):
    fe = cues.meta.get("frame_end")
    traces = [r for r in rows if r[2] in ("Create", "TracePiece") and r[0] >= fe + 0.2 - 1e-6]
    labels = sorted(r[0] for r in rows
                    if r[2] == "FadeIn" and abs(r[1] - 0.3) < 1e-6 and r[0] >= fe - 1e-6)
    facteur = [r[0] for r in rows if r[2] == "Create+FadeIn"]
    v = {"frame_end": round(fe, 3),
         "trace_1_debut": traces[0][0] if traces else None,
         "trace_2_debut": traces[1][0] if len(traces) > 1 else None,
         "trace_2_fin": round(traces[1][0] + traces[1][1], 3) if len(traces) > 1 else None,
         "facteur": facteur[0] if facteur else None}
    for k, name in enumerate(("label_165", "label_330", "label_22")):
        v[name] = labels[k] if len(labels) > k else None
    return v


def values_S17(rows, cues):
    grows = [r for r in rows if r[2] == "GrowBar"]
    fades = {r[0] for r in rows if r[2] == "FadeIn"}
    v = {"frame_end": round(cues.meta.get("frame_end"), 3)}
    for k, (t, rt, _) in enumerate(grows, 1):
        end = round(t + rt, 3)
        v[f"barre_{k}_debut"] = t
        # La valeur doit apparaitre a l'arrivee de la barre, pas avant.
        v[f"barre_{k}_fin"] = end if any(abs(f - end) < 0.005 for f in fades) else None
    return v


def frames(ep, sid):
    """Nombre d'images du plan, depuis les bornes absolues de la timeline -
    recalculee ici, sans dependre de build/ (hors depot)."""
    from build import FPS
    from timeline import build_timeline
    script, durations, ep_dir = _load(ep)
    with contextlib.redirect_stderr(io.StringIO()):
        tl = build_timeline(ep, script, durations, ep_dir)
    r = next(x for x in tl["segments"] if x["id"] == sid)
    return round(r["fin_s"] * FPS) - round(r["debut_s"] * FPS)


def _values(name, rows, cues):
    return globals()[f"values_{name.split('_')[1]}"](rows, cues)


def _check_version(name, version, rows, cues):
    """Compare un calendrier a une version de reference. Renvoie la liste des ecarts."""
    out = []
    if rows != version["calendrier"]:
        for a, b in zip(version["calendrier"], rows):
            if a != b:
                out.append(f"ref {a}   ->   maintenant {b}")
        if len(rows) != len(version["calendrier"]):
            out.append(f"{len(version['calendrier'])} reperes en reference, {len(rows)} maintenant")
    v = _values(name, rows, cues)
    for label, key, want in version["clefs"]:
        got = v.get(key)
        # Valeurs donnees au centieme : demi-centieme + arrondi du calendrier.
        if got is None or abs(got - want) > 0.0051:
            out.append(f"{label} : {got} au lieu de {want}")
    ep, sid = name.split("_")
    n = frames(ep, sid)
    if n != version["images"]:
        out.append(f"{n} images au lieu de {version['images']}")
    return out


def check_validated(name):
    import components
    doc = json.loads((REF / f"{name}.json").read_text(encoding="utf-8"))
    ok = True
    rule_now = components.FRAME_RULE
    cur = doc["versions"][doc["courante"] - 1]
    if cur["regle_cadre"] != rule_now:
        print(f"ECART   !!! {name} v{cur['version']} attend FRAME_RULE = {cur['regle_cadre']!r}, "
              f"le code est en {rule_now!r}")
        ok = False
    else:
        issues = _check_version(name, cur, *_shot(name))
        if issues:
            ok = False
            print(f"ECART   !!! REFERENCE VALIDEE A L'ECRAN !!!  {name} v{cur['version']}")
            for i in issues:
                print(f"          {i}")
        else:
            vu = "" if cur.get("vue_a_l_ecran", True) else "  (pas encore vue a l'ecran)"
            print(f"ok      {name} v{cur['version']} : calendrier, {len(cur['clefs'])} valeurs "
                  f"clefs, {cur['images']} images{vu}")
    # Chaque version archivee doit rester reproductible avec sa regle.
    for v in doc["versions"]:
        if v is cur:
            continue
        components.FRAME_RULE = v["regle_cadre"]
        try:
            issues = _check_version(name, v, *_shot(name))
        finally:
            components.FRAME_RULE = rule_now
        if issues:
            ok = False
            print(f"ECART   {name} v{v['version']} (archive) n'est plus reproductible "
                  f"avec FRAME_RULE = {v['regle_cadre']!r} :")
            for i in issues:
                print(f"          {i}")
        else:
            print(f"ok      {name} v{v['version']} (archive du {v.get('archivee_le')}) : "
                  f"reproductible avec FRAME_RULE = {v['regle_cadre']!r}")
    return ok


def new_version(name, motif, vue):
    """Archive la version courante et fige le calendrier actuel comme suivante."""
    import components
    path = REF / f"{name}.json"
    doc = json.loads(path.read_text(encoding="utf-8"))
    cur = doc["versions"][doc["courante"] - 1]
    rows, cues = _shot(name)
    if rows == cur["calendrier"]:
        raise SystemExit(f"{name} : calendrier identique a la v{cur['version']}, rien a figer")
    today = datetime.date.today().strftime("%d/%m/%Y")
    cur["archivee_le"] = today
    cur["archivee_pour"] = motif
    v = _values(name, rows, cues)
    ep, sid = name.split("_")
    new = {"version": len(doc["versions"]) + 1, "validee_le": today, "motif": motif,
           "regle_cadre": components.FRAME_RULE, "vue_a_l_ecran": vue,
           "images": frames(ep, sid),
           "clefs": [[LIBELLES[name][k], k, v[k]] for k in LIBELLES[name]],
           "calendrier": rows}
    doc["versions"].append(new)
    doc["courante"] = new["version"]
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{name} : v{cur['version']} archivee ({motif}), v{new['version']} figee")
    for label, key, value in new["clefs"]:
        print(f"          {label:<34} {value}")


def calendars_unvalidated():
    out = {}
    s, d, _ = _load("EP001")
    for g in s["segments"]:
        if g["type_visuel"] == "manim":
            out[f"EP001_{g['id']}"] = _calendar(g, d[g["id"]].audio)[0]
    import exemple_deux_courbes as ex
    out["exemple_deux_courbes"] = _calendar(ex.SEGMENT, ex.DUREE)[0]
    return out


def main():
    args = sys.argv[1:]
    if "--nouvelle-version" in args:
        name = args[args.index("--nouvelle-version") + 1]
        motif = args[args.index("--motif") + 1] if "--motif" in args else ""
        if not motif:
            raise SystemExit("--motif obligatoire : pourquoi cette nouvelle version ?")
        new_version(name, motif, vue="--pas-vue" not in args)
        return
    fige = "--fige" in args
    REF.mkdir(exist_ok=True)
    ok = True

    import components
    import briefs
    for k, v in RYTHME.items():
        got = getattr(components, k, None)
        if got != v:
            ok = False
            print(f"RYTHME  {k} = {got}, attendu {v}")
    if briefs.GAP != RYTHME["GAP"]:
        ok = False
        print(f"RYTHME  briefs.GAP = {briefs.GAP}, attendu {RYTHME['GAP']}")

    for name in LIBELLES:
        ok = check_validated(name) and ok

    for name, rows in calendars_unvalidated().items():
        path = REF / f"{name}.json"
        if not path.exists():
            if fige:
                path.write_text(json.dumps({"calendrier": rows}, ensure_ascii=False, indent=1)
                                + "\n", encoding="utf-8")
                print(f"fige    {name}  ({len(rows)} reperes)")
            else:
                ok = False
                print(f"MANQUE  {name} : pas de reference (lancer --fige)")
            continue
        ref = json.loads(path.read_text(encoding="utf-8"))["calendrier"]
        if rows == ref:
            print(f"ok      {name}")
            continue
        ok = False
        print(f"ECART   {name}")
        for a, b in zip(ref, rows):
            if a != b:
                print(f"          ref {a}   ->   maintenant {b}")

    print("\nNON-REGRESSION : OK" if ok else "\nNON-REGRESSION : ECHEC")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
