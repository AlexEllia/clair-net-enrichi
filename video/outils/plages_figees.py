# -*- coding: utf-8 -*-
"""Les fins (et milieux) de plan a tenir par une revelation de sens.

    python video/outils/plages_figees.py EP004 [--seuil 3.5]

Pour chaque plan manim de l'episode, simule SANS ses encarts « centre »
(deux au plus desormais, et ce n'est plus a eux de tenir l'ecran), ecrit dans
episodes/EPxxx/build/plages_figees.md :
- les plages de plus de `seuil` secondes sans rien de nouveau a l'ecran, au
  calendrier du moteur (sans rendu), avec debut et fin ;
- les mots que la voix prononce pendant chacune (audio/alignments/) ;
- les elements du plan qui peuvent y etre reveles : ceux de sa famille, et
  les cles que `accents` accepte.
Ne touche ni au script ni aux rendus.
"""
import argparse
import contextlib
import copy
import io
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
PROJECT = ROOT.parent

# Ce que chaque famille sait souligner, tel que le brief l'ecrit (CATALOGUE.md,
# « Tenir une fin de plan »).
PROPRES = {
    "LineChart": ['`crossing` (`"croisement": true`)',
                  '`gap` (`"ecart": {"x": …, "valeur": …, "format": …}`)',
                  '`factor` (`"facteur": {"serie": 1, "x": …, "valeur": …}`)'],
    "Bars": ['`highlight` (`"mise_en_avant": {"barre": g}`)',
             '`reference` (`"repere": {"valeur": v}`)',
             '`annotation` (`"annotation": {"barre": g, "valeur": v, "format": "facteur"}`)'],
    "Areas": [],
    "Comparaison": ['`gap` (`"ecart": {"entre": [g1, g2], "valeur": v, "format": f}`)',
                    '`highlight` (`"mise_en_avant": {"option": k}`)',
                    '`suite` (`"suite": {"option": k}`)'],
    "Flux": ['`highlight` (`"mise_en_avant": {"liens": [k, …]}`)'],
    "Erosion": ['`reste`', '`cumul` (`"cumul": {"montant": v, "format": f}`)'],
    "Cascade": [],
    "Grille": ['`valeur_k` (la valeur exacte, posée après la vague)'],
    "Distribution": ['`zone` (`"part_negative": {"valeur": v, "format": "pct"}`)',
                     '`mediane` (`"mediane": {"valeur": v}`)', '`cas` (`"cas": {"valeur": v}`)'],
}


def mots_entre(align, a, b):
    """Les mots dont le debut tombe entre a et b, balises [..] exclues."""
    chars, debuts = align["characters"], align["character_start_times_seconds"]
    out, mot, t_mot, dans_balise = [], "", None, False
    for c, t in list(zip(chars, debuts)) + [(" ", 1e9)]:
        if c == "[":
            dans_balise = True
        if dans_balise:
            if c == "]":
                dans_balise = False
            continue
        if c.isspace():
            if mot and t_mot is not None and a - 1e-6 <= t_mot < b:
                out.append(mot)
            mot, t_mot = "", None
        else:
            if not mot:
                t_mot = t
            mot += c
    return " ".join(out)


def main():
    ap = argparse.ArgumentParser(description="Plages figees d'un episode, sans encarts")
    ap.add_argument("ep")
    ap.add_argument("--seuil", type=float, default=3.5)
    args = ap.parse_args()

    import build
    import nombres
    from briefs import _gaps
    from timeline import load_durations, ajuster
    nombres.set_locale("fr")
    ep_dir = PROJECT / "episodes" / args.ep
    script = json.loads((ep_dir / "script.json").read_text(encoding="utf-8"))
    durations = ajuster(script, load_durations(ep_dir / "audio" / "durations.json"))

    seuil = f"{args.seuil:g}".replace(".", ",")
    L = [f"# {args.ep} — plages figées, plans simulés sans encarts", "",
         f"Écrit par `python video/outils/plages_figees.py {args.ep}`. Plans `manim` seulement, "
         f"simulés **sans leurs encarts `centre`**, au calendrier du moteur (sans rendu). Une "
         f"plage est un intervalle de plus de {seuil} s où rien de nouveau n'arrive à "
         f"l'écran ; `make check` refuse au-delà de 4 s (R6). Les instants sont relatifs au "
         f"début du segment.", "",
         "Chaque plage se tient par une **révélation de sens** calée sur les mots que la voix "
         "y prononce : un élément de la famille, ou un accent (`accents` + `accent_k`, deux au "
         "plus par plan). Voir `video/CATALOGUE.md`, « Tenir une fin de plan ».", ""]
    bilan = []
    unites = []
    for seg in script["segments"]:
        if seg["type_visuel"] != "manim":
            continue
        try:
            sp = build.plans_du_segment(seg, durations[seg["id"]].audio, ep_dir)
        except SystemExit as e:
            L += [f"## {seg['id']} — deux plans", "", f"Découpe impossible : {e}", ""]
            continue
        if sp:
            # Deux plans : chacun est un plan entier, sur sa propre durée.
            unites += [(plan, d, t0, seg["id"], None) for plan, t0, d in sp[0]]
        else:
            unites.append((seg, durations[seg["id"]].audio, 0.0, seg["id"], ep_dir))
    for seg, dur, decalage, sid_voix, ep_dir_plan in unites:
        sid, fam = seg["id"], seg["manim_brief"]["composant"]
        nu = copy.deepcopy(seg)
        nu["overlay_texte"] = [o for o in nu.get("overlay_texte") or [] if o["ancre"] != "centre"]
        n_enc = len(seg.get("overlay_texte") or []) - len(nu["overlay_texte"])
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                cal = build.calendrier_nouveaute(nu, dur, ep_dir_plan)
                cues = build.composer(nu, dur, ep_dir_plan)
        except SystemExit as e:
            L += [f"## {sid} — {fam}", "", f"Plan non construit : {e}", ""]
            continue
        plages = [(a, b) for a, b in _gaps(cal, 0.0, dur) if b - a > args.seuil]
        titres = sorted(t for m, t, a in build._objets(cues)
                        if str(getattr(m, "nom", "")).startswith("titre_haut "))
        titre = "absent" if not titres else f"posé à {titres[0]:.2f} s" + (
            "" if titres[0] <= build.TITRE_AVANT else " (trop tard : 1,0 s au plus)")
        align_p = ep_dir / "audio" / "alignments" / f"{sid_voix}.json"
        align = json.loads(align_p.read_text(encoding="utf-8")) if align_p.exists() else None
        deja = {r["element"] for r in seg["manim_brief"].get("revelations") or []}
        mb = seg["manim_brief"]
        if fam == "Comparaison" and mb.get("reference"):
            propres = []
        else:
            propres = PROPRES.get(fam, [])
        libres = [p for p in propres if re.match(r"`(\w+)`", p).group(1) not in deja]
        L += [f"## {sid} — {fam} ({dur:.2f} s"
              + (f", à partir de {decalage:.2f} s du segment" if decalage else "") + ")", "",
              f"- Titre : {titre}. Encarts actuels : {n_enc} (deux au plus).",
              f"- Révélations déjà écrites : {', '.join(f'`{r}`' for r in sorted(deja)) or 'aucune'}.",
              f"- Éléments de la famille encore libres : {' ; '.join(libres) or 'aucun'}.",
              f"- Clés acceptées par `accents` : "
              f"{', '.join(f'`{c}`' for c in sorted(cues.parties)) or 'aucune'}.", ""]
        if not plages:
            L += [f"Aucune plage de plus de {seuil} s : le graphique tient seul.", ""]
        else:
            L += ["| Début | Fin | Durée | R6 | Ce que dit la voix pendant la plage |",
                  "|---|---|---|---|---|"]
            for a, b in plages:
                dit = mots_entre(align, a + decalage, b + decalage) if align \
                    else "(pas d'alignement)"
                L.append(f"| {a:.2f} s | {b:.2f} s | {b - a:.1f} s | "
                         f"{'refus' if b - a > 4.0 else 'limite'} | {dit or '(silence)'} |")
            L.append("")
        bilan.append((sid, fam, plages))
    n_ref = sum(1 for _, _, p in bilan if any(b - a > 4.0 for a, b in p))
    L[4:4] = [f"**Bilan** : {len(bilan)} plans manim ; {sum(1 for _, _, p in bilan if p)} "
              f"portent au moins une plage de plus de {seuil} s, dont {n_ref} seraient "
              f"refusés par R6 (plus de 4 s) ; "
              f"{sum(len(p) for _, _, p in bilan)} plages en tout, "
              f"{sum(b - a for _, _, p in bilan for a, b in p):.0f} s.", ""]
    dest = ep_dir / "build" / "plages_figees.md"
    dest.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(L[4])
    print(dest)


if __name__ == "__main__":
    main()
