# -*- coding: utf-8 -*-
"""Non-regression des calendriers, sans rendu.

    python video/non_regression.py                 compare aux references
    python video/non_regression.py --fige          ecrit les references manquantes
                                                   (jamais celles des plans valides)
    python video/non_regression.py --nouvelle-version EP001b_S09 --motif "..."
                                                   archive la version courante d'un
                                                   plan valide et fige le calendrier
                                                   actuel comme version suivante
    python video/non_regression.py --valider EP001c_S02 --motif "..."
                                                   fige la premiere version d'un plan
                                                   qui vient d'etre valide a l'ecran

Par ordre d'importance :

1. Les plans VALIDES A L'ECRAN - approuves par un oeil humain (S09 et S17 de
   l'EP001b ; S02 et S12 de l'EP001c, pilotes de Comparaison et Flux, rendus
   depuis leur brief de video/pilotes/ et non depuis script.json). Leur reference est versionnee : chaque version garde sa date,
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
    "EP001c_S02": {
        "frame_end": "construction du cadre, fin",
        "jauge_1_debut": "jauge 55 EUR : depart", "jauge_1_fin": "55 EUR ecrit",
        "jauge_2_debut": "jauge 2 400 EUR : depart", "jauge_2_fin": "2 400 EUR ecrit",
        "pictos_debut": "12 mois : premier picto", "pictos_fin": "12 mois : dernier picto",
        "ecart": "ecart", "mise_en_avant": "mise en avant des interets",
        "suite_debut": "suite : depart", "suite_fin": "suite : arrivee",
    },
    "EP001c_S12": {
        "noeud_vous": "noeud Vous", "case_depart": "noeud et lien Case depart",
        "courant_depart": "argent de la case depart, debut",
        "maisons": "noeud Maisons", "hotels": "noeud Hotels",
        "loyers": "liens Loyers", "courant_loyers": "argent des loyers, debut",
        "mise_en_avant": "mise en avant des loyers",
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


def _pilot(name):
    brief = HERE / "pilotes" / f"{name}.json"
    return brief if brief.exists() else None


def _shot(name, voix_s=None):
    """Calendrier d'un plan de reference.

    Un plan pilote (video/pilotes/<nom>.json) se rend depuis son brief, avec
    les temps qui y sont ecrits et la duree de voix figee dans sa reference
    (`voix_s`) : il a ete valide sur une voix que l'episode peut regenerer
    depuis. Sa reference ne depend donc ni de audio/ ni de script.json."""
    ep, sid = name.split("_")
    seg, dur = _segment(ep, sid)
    brief = _pilot(name)
    if brief is not None:
        import copy
        b = json.loads(brief.read_text(encoding="utf-8"))
        seg = copy.deepcopy(seg)
        for k in ("type_visuel", "manim_brief", "overlay_texte"):
            seg[k] = copy.deepcopy(b["remplace"][k])
        seg["_pilote"] = True
        if voix_s is not None:
            dur = float(voix_s)
    return _calendar(seg, dur)


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


def values_S02(rows, cues):
    """EP001c S02, Comparaison."""
    grows = [r for r in rows if r[2] == "GrowBar"]
    labels = sorted(r[0] for r in rows if r[2] == "FadeIn" and abs(r[1] - 0.3) < 1e-6)
    pic = next((r for r in rows if r[2] == "FillPictos"), None)
    gap = next((r for r in rows if r[2] == "Create+Create"), None)
    hl = next((r for r in rows if r[2].startswith("Create+Restyle")), None)
    v = {"frame_end": round(cues.meta.get("frame_end"), 3)}
    for k, g in enumerate(grows[:2], 1):
        end = round(g[0] + g[1], 3)
        v[f"jauge_{k}_debut"] = g[0]
        # La valeur s'ecrit a l'arrivee de la jauge, pas avant.
        v[f"jauge_{k}_fin"] = end if any(abs(f - end) < 0.005 for f in labels) else None
    v["pictos_debut"] = pic[0] if pic else None
    v["pictos_fin"] = round(pic[0] + pic[1], 3) if pic else None
    v["ecart"] = gap[0] if gap else None
    v["mise_en_avant"] = hl[0] if hl else None
    s = grows[2] if len(grows) > 2 else None
    v["suite_debut"] = s[0] if s else None
    v["suite_fin"] = round(s[0] + s[1], 3) if s else None
    return v


def values_S12(rows, cues):
    """EP001c S12, Flux. Les noeuds surgissent en 1,5 s au plus (les overlays en
    0,5 s) ; les liens se tracent (Create+FadeIn), puis l'argent circule."""
    nodes = sorted(r[0] for r in rows if r[2] == "FadeIn" and abs(r[1] - 0.5) > 1e-6)
    links = sorted(r[0] for r in rows if r[2] == "Create+FadeIn")
    flows = sorted(r[0] for r in rows if r[2] == "Courant")
    hl = next((r[0] for r in rows if r[2].startswith("Restyle")), None)
    return {"noeud_vous": nodes[0] if nodes else None,
            "case_depart": links[0] if links else None,
            "courant_depart": flows[0] if flows else None,
            "maisons": nodes[2] if len(nodes) > 2 else None,
            "hotels": nodes[3] if len(nodes) > 3 else None,
            "loyers": links[1] if len(links) > 1 else None,
            "courant_loyers": flows[1] if len(flows) > 1 else None,
            "mise_en_avant": hl}


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
    if "voix_s" in version:
        return out      # voix figee : le nombre d'images est celui de la voix d'alors
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
        issues = _check_version(name, cur, *_shot(name, cur.get("voix_s")))
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
            issues = _check_version(name, v, *_shot(name, v.get("voix_s")))
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
    rows, cues = _shot(name, cur.get("voix_s"))
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
    if "voix_s" in cur:
        new["voix_s"] = cur["voix_s"]
        new["images"] = cur["images"]
    doc["versions"].append(new)
    doc["courante"] = new["version"]
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{name} : v{cur['version']} archivee ({motif}), v{new['version']} figee")
    for label, key, value in new["clefs"]:
        print(f"          {label:<34} {value}")


def first_version(name, motif):
    """Fige la premiere version d'un plan qui vient d'etre valide a l'ecran."""
    import components
    path = REF / f"{name}.json"
    if path.exists():
        raise SystemExit(f"{name} : reference deja figee ; une modification approuvee passe "
                         f"par --nouvelle-version")
    if name not in LIBELLES:
        raise SystemExit(f"{name} : ajouter d'abord ses valeurs clefs a LIBELLES")
    ep, sid = name.split("_")
    voix_s = None
    if _pilot(name) is not None:
        # Le brief doit porter les temps de la voix sur laquelle le plan a ete
        # vu : ce sont eux, et cette duree, que la reference fige.
        import copy
        from pilote import recaler
        b = json.loads(_pilot(name).read_text(encoding="utf-8"))
        items = copy.deepcopy((b["remplace"]["manim_brief"].get("revelations") or [])
                              + b["remplace"]["overlay_texte"])
        al = json.loads((PROJECT / "episodes" / ep / "audio" / "alignments" / f"{sid}.json")
                        .read_text(encoding="utf-8"))
        before = [it.get("t_rel_s") for it in items]
        with contextlib.redirect_stderr(io.StringIO()):
            recaler(sid, items, al, "brief")
        if any(a is None or abs(float(a) - it["t_rel_s"]) > 0.05 for a, it in zip(before, items)):
            raise SystemExit(f"{name} : les t_rel_s du brief ne sont pas ceux de la voix "
                             f"actuelle ; recaler le brief avant de le figer")
        voix_s = _segment(ep, sid)[1]
    rows, cues = _shot(name, voix_s)
    v = _values(name, rows, cues)
    missing = [k for k in LIBELLES[name] if v.get(k) is None]
    if missing:
        raise SystemExit(f"{name} : valeurs clefs introuvables dans le calendrier : {missing}")
    doc = {"statut": "VALIDE A L'ECRAN - ne jamais regenerer sans accord explicite ; une "
                     "modification approuvee ajoute une version, n'en ecrase aucune.",
           "courante": 1,
           "versions": [{"version": 1,
                         "validee_le": datetime.date.today().strftime("%d/%m/%Y"),
                         "motif": motif, "regle_cadre": components.FRAME_RULE,
                         "vue_a_l_ecran": True, "images": frames(ep, sid),
                         "clefs": [[LIBELLES[name][k], k, v[k]] for k in LIBELLES[name]],
                         "calendrier": rows}]}
    if voix_s is not None:
        doc["versions"][0]["voix_s"] = voix_s
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{name} : v1 figee ({motif})")
    for label, key, value in doc["versions"][0]["clefs"]:
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
    if "--valider" in args:
        name = args[args.index("--valider") + 1]
        motif = args[args.index("--motif") + 1] if "--motif" in args else ""
        if not motif:
            raise SystemExit("--motif obligatoire : qu'est-ce qui a ete valide a l'ecran ?")
        first_version(name, motif)
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
