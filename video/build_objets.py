# -*- coding: utf-8 -*-
"""Ce qu'un plan a deja pose a un instant donne (pour l'accent commun)."""


def _deplier(a):
    sous = getattr(a, "animations", None)
    if sous:
        return [x for y in sous for x in _deplier(y)]
    return [a]


def objets_avant(cues, t):
    """Les objets du graphique poses avant `t`, sans doublon : le decor, et la
    cible de chaque animation deja partie. L'argent qui circule (Courant)
    n'en est pas : ses particules suivent leur chemin."""
    from components import Courant
    out, vus = [], set()
    for m in cues.static:
        if id(m) not in vus:
            vus.add(id(m))
            out.append(m)
    for t0, anims, _ in sorted(cues.items, key=lambda c: c[0]):
        if t0 >= t:
            continue
        for a in [x for y in anims for x in _deplier(y)]:
            m = getattr(a, "mobject", None)
            if m is None or isinstance(a, Courant) or id(m) in vus:
                continue
            vus.add(id(m))
            out.append(m)
    return out
