# -*- coding: utf-8 -*-
"""Du `manim_brief` du script a l'appel d'un composant.

Deux traductions, parce que les deux cotes ne parlent pas la meme langue :

1. Le composant. Un nom de famille de CATALOGUE.md (`LineChart`...) est pris
   tel quel. Un nom d'usage (`two_growth_curves`) passe par traductions.json -
   heritage de l'EP001b, gele - qui donne la famille, ses parametres par
   defaut et le nom de chaque element. Chaque traduction est journalisee.

2. Les revelations. Le script ecrit

       revelations[].element  ->  target   (partie du composant)
       revelations[].t_rel_s  ->  at
       revelations[].declencheur           ignore : repere de relecture humaine

   Le cadre (`frame`) est du decor : il n'est pas une revelation et ne borne
   rien ; il se construit pendant l'attente de la premiere donnee, 4 s au
   plus. Les autres recoivent un plafond `max_rt` :
   le temps jusqu'a la revelation suivante moins 0,2 s, ou jusqu'a la fin de
   la voix pour la derniere. Le composant en tire

       run_time = clamp(max_rt, 0.3, maximum de la partie)

   ou le maximum est de 6 s pour ce qui se trace (courbe, aire, bande) et de
   1,5 s pour ce qui surgit (barre, repere, accolade) : l'animation remplit
   son intervalle au lieu de finir tot. Deux revelations au meme instant
   forment une seule apparition.
"""

import copy
import json
import sys
from pathlib import Path

from components import COMPONENTS, CONTINUOUS_MAX, PUNCTUAL_MAX, MIN_RT, PILOTES

GAP = 0.2          # respiration entre deux apparitions successives
MAX_STILL = 4.0    # au-dela, l'ecran reste fige trop longtemps
DECOR = {"frame"}  # parties posees des la premiere image
TABLE = Path(__file__).resolve().parent / "traductions.json"


def _warn(msg):
    print(f"[ATTENTION] {msg}", file=sys.stderr, flush=True)


def _table():
    return {k: v for k, v in json.loads(TABLE.read_text(encoding="utf-8")).items()
            if not k.startswith("_")}


def is_decor(element, target):
    # `_frame` : convention de nommage de l'EP001b (grid_frame, bars_frame,
    # chart_frame), pour les segments dont le composant n'est pas encore traduit.
    return target in DECOR or str(element).endswith("_frame")


def revelations_to_reveals(sid, revelations, elements, dur):
    """Liste `reveals` (target, at, max_rt) depuis `revelations`, decor exclu."""
    rows = [r for r in sorted(revelations, key=lambda r: float(r["t_rel_s"]))
            if not is_decor(r["element"], elements.get(r["element"], r["element"]))
            and not (r["element"] in elements and elements[r["element"]] is None)]
    times = [float(r["t_rel_s"]) for r in rows]
    out = []
    for r, t in zip(rows, times):
        el = r["element"]
        if el in elements and elements[el] is None:
            continue                     # ignore par la table de traduction
        target = elements.get(el, el)
        if elements and el not in elements:
            _warn(f"{sid} : element {el!r} absent de traductions.json, passe tel quel")
        nxt = next((u for u in times if u > t + 1e-6), None)
        cap = (nxt - t - GAP) if nxt is not None else (dur - t)
        if t >= dur:
            _warn(f"{sid} : {el!r} a {t:.2f} s tombe apres la fin de la voix ({dur:.2f} s)")
        out.append({"target": target, "at": t, "max_rt": round(cap, 3)})
    return out


def resolve(seg, dur, log=True):
    """(segment pret pour le composant, nom de la famille)."""
    seg = copy.deepcopy(seg)
    sid = seg["id"]
    mb = seg["manim_brief"]
    name = mb["composant"]
    elements = {}
    if name in PILOTES and not seg.get("_pilote"):
        raise SystemExit(f"{sid} : {name} est une famille pilote, en attente de validation a "
                         f"l'ecran et hors catalogue ; seul video/pilote.py la rend, depuis "
                         f"un brief de video/pilotes/")
    if name in COMPONENTS:
        fam = name
    else:
        entry = _table().get(name)
        if entry is None:
            raise SystemExit(f"{sid} : composant {name!r} inconnu. Familles "
                             f"disponibles : {', '.join(COMPONENTS)} (video/CATALOGUE.md)")
        fam = entry["famille"]
        defaults = [k for k in entry.get("parametres", {}) if k not in mb]
        for k in defaults:
            mb[k] = entry["parametres"][k]
        elements = entry.get("elements", {})
        used = {r["element"]: elements[r["element"]] for r in mb.get("revelations") or []
                if r["element"] in elements}
        if log:
            print(f"[TRADUCTION] {sid} : {name} -> {fam} (heritage EP001b) ; "
                  f"parametres par defaut : {', '.join(defaults) or 'aucun'} ; "
                  f"elements : {', '.join(f'{a}->{b or 'ignore'}' for a, b in used.items()) or 'aucun'}",
                  file=sys.stderr, flush=True)
    if mb.get("revelations"):
        if mb.get("reveals"):
            _warn(f"{sid} : 'reveals' et 'revelations' tous deux presents ; "
                  f"'revelations' l'emporte")
        mb["reveals"] = revelations_to_reveals(sid, mb["revelations"], elements, dur)
    seg["_elements"] = elements
    return seg, fam


# --- Temps morts -------------------------------------------------------------
# Un temps mort est un intervalle ou rien ne bouge a l'ecran - ni trace, ni
# etiquette, ni overlay - entre la premiere donnee reelle et la derniere
# revelation. Le decor ne compte pas : il est la des la premiere image.

def _gaps(intervals, start, end):
    """Trous de l'union des intervalles, dans [start, end]."""
    out, cur = [], start
    for a, b in sorted(intervals):
        if b <= cur:
            continue
        if a > cur and a <= end:
            out.append((cur, min(a, end)))
        cur = max(cur, b)
        if cur >= end:
            break
    if cur < end:
        out.append((cur, end))
    return [(a, b) for a, b in out if b - a > 1e-6]


def _name_gap(rows, a, b):
    before = [r["element"] for r in rows if float(r["t_rel_s"]) <= a + 1e-6]
    after = [r["element"] for r in rows if float(r["t_rel_s"]) >= b - 1e-6]
    return (before[-1] if before else "debut", after[0] if after else "fin")


def _data_rows(seg):
    mb = seg.get("manim_brief") or {}
    return [r for r in sorted(mb.get("revelations") or [], key=lambda r: float(r["t_rel_s"]))
            if not is_decor(r["element"], (seg.get("_elements") or {}).get(r["element"], ""))]


_BAR_WORDS = ("bar", "barre")
_CONTINUOUS_WORDS = ("curve", "line", "area", "band", "courbe", "ligne", "aire", "bande")
_PUNCTUAL_WORDS = ("marker", "bracket", "label", "ratio", "repere", "accolade", "annotation")


def _motion_by_name(element):
    """Estimation seulement, pour un segment dont le composant n'est pas
    encore traduit : (temps de mouvement avant le mot, duree apres le mot).

    - barre : elle monte de zero, jusqu'a 6 s avant son mot ; sa valeur
      apparait sur le mot (0,3 s) ;
    - courbe, aire, bande : sans traduction, on ignore quelle part du trace
      precede le point enonce (aucune, si c'est son premier point) :
      estimation prudente, rien avant le mot, jusqu'a 6 s apres ;
    - marqueur, accolade, annotation : rien avant, 1,5 s apres.
    Les mots de ce qui surgit l'emportent (`ratio_marker` est un marqueur).
    """
    from components import LABEL_RT
    name = str(element).lower()
    if any(w in name for w in _PUNCTUAL_WORDS):
        return 0.0, PUNCTUAL_MAX
    if any(w in name for w in _BAR_WORDS):
        return CONTINUOUS_MAX, LABEL_RT
    if any(w in name for w in _CONTINUOUS_WORDS):
        return 0.0, CONTINUOUS_MAX
    return 0.0, PUNCTUAL_MAX


def _estimate(seg, dur):
    """(fin du cadre, debut du premier mouvement, intervalles) estimes depuis
    le script, en suivant les regles du moteur : cadre jusqu'a 4 s, mouvement
    planifie a rebours la ou il peut l'etre, 0,2 s entre deux animations."""
    from components import _frame_end
    rows = _data_rows(seg)
    if not rows:
        return None
    times = [float(r["t_rel_s"]) for r in rows]
    # Meme regle de cadre que le moteur : une barre part de zero (fraction 1
    # a parcourir) ; un element qui n'anticipe pas ne reclame rien au cadre.
    before0, _ = _motion_by_name(rows[0]["element"])
    frame_end = _frame_end({"estimation": [(1.0 if before0 else 0.0, times[0])]})
    busy, first, intervals = frame_end, None, []
    for r, t in zip(rows, times):
        before, after = _motion_by_name(r["element"])
        nxt = next((u for u in times if u > t + 1e-6), None)
        room = (nxt - t - GAP) if nxt is not None else (dur - t)
        start = min(t, max(busy + GAP, t - before)) if before else t
        end = t + max(MIN_RT, min(room, after))
        intervals.append((start, end))
        first = start if first is None else min(first, start)
        busy = t if before else end
    intervals += [(float(o["t_rel_s"]), float(o["t_rel_s"]) + 0.5)
                  for o in seg.get("overlay_texte") or []]
    return frame_end, first, intervals


def still_times(seg, dur, intervals=None):
    """[(avant, apres, debut, duree)] des temps morts de plus de MAX_STILL.

    `intervals` : les animations reellement posees par le composant et les
    overlays (mesure exacte). Sans eux, estimation depuis le script (voir
    _estimate et _motion_by_name).
    """
    rows = _data_rows(seg)
    if len(rows) < 2:
        return []
    times = [float(r["t_rel_s"]) for r in rows]
    if intervals is None:
        intervals = _estimate(seg, dur)[2]
    out = []
    for a, b in _gaps(intervals, times[0], times[-1]):
        if b - a > MAX_STILL:
            out.append((*_name_gap(rows, a, b), a, b - a))
    return out


def opening(seg, meta=None, dur=None):
    """(fin du cadre, debut de la premiere donnee, ouverture inerte, estime).

    L'ouverture inerte est le temps ou le cadre est fini et ou aucune donnee
    ne bouge encore. Mesure exacte depuis `meta` (le composant l'a posee) ;
    sinon estimation depuis le script (voir _estimate).
    """
    if meta and meta.get("first_data") is not None:
        f, d = meta["frame_end"], meta["first_data"]
        return f, d, max(0.0, d - f), False
    est = _estimate(seg, dur if dur is not None else 1e9)
    if est is None:
        return None
    f, d, _ = est
    return f, d, max(0.0, d - f), True


def warn_still(seg, intervals, dur):
    for a, b, t, length in still_times(seg, dur, intervals):
        _warn(f"{seg['id']} : ecran fige {length:.2f} s a partir de {t:.2f} s, "
              f"entre {a!r} et {b!r} (> {MAX_STILL:.0f} s)")
