# -*- coding: utf-8 -*-
"""Miniatures YouTube aux couleurs et dans la typographie de la charte
(style.py), une par variante de la section « ## Miniatures » de
metadonnees.md (fonction « Tester et comparer » de YouTube Studio).

    make miniature EP=EP001c        (python video/miniature.py EP001c)

Ecrit dans episodes/<EP>/build/miniatures/ : miniature_<X>.png (1280x720),
miniature_<X>_168x94.png (mobile), planche.png (variantes cote a cote,
badge de duree simule) et brief.json (ce qui a ete lu et calcule).

Familles :
  chiffre   un chiffre geant, ecart entre deux barres (annees de bascule)
  contraste deux courbes qui divergent (cumul verse, capital)
  bascule   les interets de l'annee croisent ses versements, croisement marque

Contraintes verifiees (code de sortie 1 sinon) : 1280x720, PNG sous 2 Mo,
coin inferieur droit (ZONE_DUREE) laisse au fond, 6 mots au plus, un seul
chiffre geant, lexique interdit de la skill absent, hauteur de capitale d'au
moins 7 px en 168x94, contraste WCAG d'au moins 4,5:1, chiffre geant egal a
l'ecart des barres, tout nombre affiche present dans recherche.md.
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
import style  # noqa: E402  (palette et police de la charte)

W, H = 1280, 720
SS = 2                                   # sur-echantillonnage du dessin
MOBILE = (168, 94)
MARGE = 64
ZONE_DUREE = (1280 - 200, 720 - 76, 1280, 720)   # 180x60 et une marge
POIDS_MAX = 2 * 1024 * 1024

POLICES = {  # style.FONT = "Segoe UI" : fichiers Windows de la famille
    "black": "seguibl.ttf", "bold": "segoeuib.ttf", "semi": "seguisb.ttf",
}


def police(graisse, taille):
    return ImageFont.truetype(str(Path("C:/Windows/Fonts") / POLICES[graisse]), taille * SS)


def rgb(h, a=255):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) + (a,)


def fond(projecteurs=()):
    """Fond encre de la charte : vignette haute (BG_LIFT), projecteurs doux
    (x, y, rayon, couleur, opacite) derriere le point focal, bords assombris."""
    img = Image.new("RGBA", (W * SS, H * SS), rgb(style.BG))
    haut = Image.new("RGBA", img.size, rgb(style.BG_LIFT))
    masque = Image.linear_gradient("L").resize(img.size).transpose(Image.FLIP_TOP_BOTTOM)
    img.paste(haut, (0, 0), masque.point(lambda v: int(v * 0.9)))
    for x, y, r, c, a in projecteurs:
        calque = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(calque).ellipse([(x - r) * SS, (y - r) * SS, (x + r) * SS, (y + r) * SS],
                                       fill=rgb(c, a))
        img.alpha_composite(calque.filter(ImageFilter.GaussianBlur(r * 0.45 * SS)))
    # Bords assombris : le regard va au centre de l'image.
    bord = Image.radial_gradient("L").resize(img.size)
    noir = Image.new("RGBA", img.size, (5, 7, 10, 255))
    img.paste(noir, (0, 0), bord.point(lambda v: max(0, int((v - 150) * 0.9))))
    return img


TEXTES = []      # (texte, graisse, taille, couleur, couleur du fond) poses, pour les controles


def texte(d, xy, s, graisse, taille, couleur, ancre="ls"):
    TEXTES.append((s, graisse, taille, couleur, style.BG))
    d.text((xy[0] * SS, xy[1] * SS), s, font=police(graisse, taille), fill=rgb(couleur),
           anchor=ancre)
    return d.textbbox((xy[0] * SS, xy[1] * SS), s, font=police(graisse, taille), anchor=ancre)


def couleur(c):
    """Nom de la palette (style.py) ou code hexadecimal."""
    return getattr(style, c, c)


def bloc(img, xy, s, taille, coul=None, boite=None, angle=0.0, pad=None):
    """Une ligne en capitales grasses : `s` est un texte (couleur `coul`) ou
    une liste de segments [texte, couleur] ; boite pleine optionnelle,
    inclinee de `angle` degres. xy = coin haut gauche ; renvoie le coin bas
    droit."""
    segs = [[s, coul]] if isinstance(s, str) else s
    boite = couleur(boite) if boite else None
    pad = pad or ((30, 12) if boite else (0, 0))
    f = police("black", taille)
    tout = "".join(t for t, _ in segs)
    for t, c in segs:
        TEXTES.append((t, "black", taille, couleur(c), boite or style.BG))
    x0, y0, x1, y1 = f.getbbox(tout, anchor="ls")
    asc = -min(y0, f.getbbox("H", anchor="ls")[1])     # accents des capitales compris
    w = x1 - x0 + 2 * pad[0] * SS
    h = asc + 2 * pad[1] * SS + int(0.06 * taille * SS)
    calque = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(calque)
    if boite:
        d.rounded_rectangle([0, 0, w - 1, h - 1], radius=int(0.12 * taille * SS),
                            fill=rgb(boite))
    x = pad[0] * SS - x0
    for t, c in segs:
        d.text((x, pad[1] * SS + asc), t, font=f, fill=rgb(couleur(c)), anchor="ls")
        x += f.getlength(t)
    if angle:
        calque = calque.rotate(angle, resample=Image.BICUBIC, expand=True)
    if boite:
        ombre = Image.new("RGBA", calque.size, (0, 0, 0, 0))
        ombre.paste((0, 0, 0, 170), (0, 0), calque.split()[3])
        ombre = ombre.filter(ImageFilter.GaussianBlur(14 * SS))
        img.alpha_composite(ombre, (int(xy[0] * SS + 10 * SS), int(xy[1] * SS + 14 * SS)))
    img.alpha_composite(calque, (int(xy[0] * SS), int(xy[1] * SS)))
    return (xy[0] + calque.size[0] / SS, xy[1] + calque.size[1] / SS)


def poser(img, lignes, x, y, ecart=16):
    """Empile les lignes du brief : {"segments" | "texte", "couleur",
    "taille", "boite", "angle"}. Renvoie le bas de la pile."""
    for l in lignes:
        s_ = l.get("segments") or l["texte"]
        if isinstance(s_, str):
            s_ = s_.upper()
        else:
            s_ = [[t.upper(), c] for t, c in s_]
        _, y = bloc(img, (x + (10 if l.get("boite") else 0), y), s_, l["taille"],
                    l.get("couleur", "INK"), l.get("boite"), l.get("angle", 0))
        y += ecart
    return y


def lueur(img, forme, couleur, rayon=26, opacite=150):
    """Halo doux sous un element (point de croisement, barre)."""
    calque = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(calque).ellipse(forme, fill=rgb(couleur, opacite))
    img.alpha_composite(calque.filter(ImageFilter.GaussianBlur(rayon * SS)))


def trait_lumineux(img, pts, couleur, largeur):
    """Trace epais avec un halo de sa couleur."""
    calque = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(calque).line(pts, fill=rgb(couleur, 200), width=int(largeur * 2.6 * SS),
                                joint="curve")
    img.alpha_composite(calque.filter(ImageFilter.GaussianBlur(largeur * 1.1 * SS)))
    ImageDraw.Draw(img).line(pts, fill=rgb(couleur), width=int(largeur * SS), joint="curve")


def pointe(img, pts, couleur, taille):
    """Pointe de fleche au bout d'un trace, dans sa direction."""
    (xa, ya), (xb, yb) = pts[-2], pts[-1]
    n = ((xb - xa) ** 2 + (yb - ya) ** 2) ** 0.5
    ux, uy = (xb - xa) / n, (yb - ya) / n
    t = taille * SS
    ImageDraw.Draw(img).polygon([
        (xb + ux * t * 0.6, yb + uy * t * 0.6),
        (xb - ux * t * 0.6 - uy * t * 0.7, yb - uy * t * 0.6 + ux * t * 0.7),
        (xb - ux * t * 0.6 + uy * t * 0.7, yb - uy * t * 0.6 - ux * t * 0.7)],
        fill=rgb(couleur))


def courbe_xy(valeurs, x0, x1, y0, y1, vmax):
    n = len(valeurs) - 1
    return [((x0 + (x1 - x0) * k / n) * SS, (y0 - (y0 - y1) * v / vmax) * SS)
            for k, v in enumerate(valeurs)]


# --- Familles -------------------------------------------------------------------
# Chaque famille renvoie (image, fond nu) : le controle du coin de duree
# compare l'image a son propre fond.

def chiffre(b):
    projecteurs = [(360, 300, 380, style.INTEREST, 46)]
    img = fond(projecteurs)
    d = ImageDraw.Draw(img)
    # Chiffre geant (ambre, halo) et son unite (creme).
    calque = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(calque).text((24 * SS, 468 * SS), b["chiffre"], font=police("black", 500),
                                fill=rgb(style.INTEREST, 210), anchor="ls")
    img.alpha_composite(calque.filter(ImageFilter.GaussianBlur(22 * SS)))
    bb = texte(d, (24, 468), b["chiffre"], "black", 500, style.INTEREST)
    poser(img, b["lignes"], bb[2] / SS + 26, b.get("y_lignes", 150), ecart=10)
    # Deux barres : longueur proportionnelle a la valeur ; l'ecart, en ambre
    # lumineux, est ce que dit le chiffre.
    (l1, v1), (l2, v2) = b["barres"]
    x0, x1 = 410, 1060
    k = (x1 - x0) / max(v1, v2)
    ys, ep = (556, 652), 64
    xa, xb = x0 + k * min(v1, v2), x0 + k * max(v1, v2)
    lueur(img, [xa * SS, (ys[0] - 40) * SS, xb * SS, (ys[1] + 30) * SS], style.INTEREST, 30, 90)
    for (lab, v), y, col in (((l1, v1), ys[0], style.WHITE_DIM),
                             ((l2, v2), ys[1], style.INTEREST)):
        texte(d, (x0 - 24, y + 30), lab.upper(), "black", 82,
              style.INTEREST if col == style.INTEREST else style.INK, "rs")
        d.rounded_rectangle([x0 * SS, (y - ep / 2) * SS, (x0 + k * v) * SS, (y + ep / 2) * SS],
                            radius=ep / 2 * SS, fill=rgb(col))
    ym = (ys[0] + ys[1]) / 2
    d.line([xb * SS, (ys[0] + ep / 2 - 4) * SS, xb * SS, ym * SS, (xa + 20) * SS, ym * SS],
           fill=rgb(style.INTEREST), width=12 * SS, joint="curve")
    # La fleche va de la fin longue a la fin courte : l'ecart est gagne sur le temps.
    pointe(img, [(xb * SS, ym * SS), (xa * SS, ym * SS)], style.INTEREST, 34)
    return img, fond(projecteurs)


def contraste(b):
    projecteurs = [(1060, 160, 330, style.INTEREST, 60)]
    img = fond(projecteurs)
    # La courbe haute sort presque du cadre : on ne voit pas ou elle s'arrete.
    x0, x1, yb, yh = 70, 1150, 640, 60
    vmax = max(b["haut"])
    bas, haut = (courbe_xy(b[k], x0, x1, yb, yh, vmax) for k in ("bas", "haut"))
    calque = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(calque).polygon(haut + bas[::-1], fill=rgb(style.INTEREST, 95))
    img.alpha_composite(calque)
    trait_lumineux(img, bas, style.CONTRIB, 16)
    trait_lumineux(img, haut, style.INTEREST, 24)
    pointe(img, haut, style.INTEREST, 70)
    poser(img, b["lignes"], MARGE - 20, 40)
    return img, fond(projecteurs)


def bascule(b):
    import math
    v = b["courbe"]
    x0, x1, yb, yh = 40, 1250, 690, 400
    vmax = max(v)
    n = len(v) - 1
    yf = yb - (yb - yh) * b["fixe"] / vmax
    # Croisement : la ou le trace passe la ligne (entre l'annee k et k+1, la
    # premiere ou la courbe la depasse doit etre l'annee de bascule du brief).
    k = next(i for i, x in enumerate(v) if x > b["fixe"])
    if k + 1 != b["croisement"]:                          # courbe[0] = annee 1
        sys.exit(f"bascule : la courbe depasse {b['fixe']} l'annee {k + 1}, "
                 f"le brief annonce {b['croisement']}")
    xc = x0 + (x1 - x0) * (k - 1 + (b["fixe"] - v[k - 1]) / (v[k] - v[k - 1])) / n
    projecteurs = [(xc, yf, 300, style.INTEREST, 70)]
    img = fond(projecteurs)
    d = ImageDraw.Draw(img)
    courbe = courbe_xy(v, x0, x1, yb, yh, vmax)
    apres = [p for p in courbe if p[0] >= xc * SS]
    calque = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(calque).polygon([(xc * SS, yf * SS)] + apres + [(apres[-1][0], yf * SS)],
                                   fill=rgb(style.INTEREST, 110))
    img.alpha_composite(calque)
    trait_lumineux(img, [(x0 * SS, yf * SS), (x1 * SS, yf * SS)], style.CONTRIB, 16)
    trait_lumineux(img, courbe, style.INTEREST, 24)
    # Impact au croisement : halo, rayons, point.
    lueur(img, [(xc - 90) * SS, (yf - 90) * SS, (xc + 90) * SS, (yf + 90) * SS],
          style.INK, 30, 170)
    for a in range(0, 360, 45):
        ca, sa = math.cos(math.radians(a + 22.5)), math.sin(math.radians(a + 22.5))
        d.line([(xc + 46 * ca) * SS, (yf + 46 * sa) * SS, (xc + 86 * ca) * SS,
                (yf + 86 * sa) * SS], fill=rgb(style.INK), width=8 * SS)
    d.ellipse([(xc - 26) * SS, (yf - 26) * SS, (xc + 26) * SS, (yf + 26) * SS],
              fill=rgb(style.INK), outline=rgb(style.INTEREST), width=9 * SS)
    poser(img, b["lignes"], MARGE - 20, 30, ecart=8)
    return img, fond(projecteurs)


FAMILLES = {"chiffre": chiffre, "contraste": contraste, "bascule": bascule}


def rendre(brief, dest):
    dest.mkdir(parents=True, exist_ok=True)
    sorties = {}
    for nom, b in brief["variantes"].items():
        TEXTES.clear()
        img, nu = FAMILLES[b["famille"]](b)
        img = img.resize((W, H), Image.LANCZOS).convert("RGB")
        nu = nu.resize((W, H), Image.LANCZOS).convert("RGB")
        p = dest / f"miniature_{nom}.png"
        img.save(p, optimize=True)
        m = dest / f"miniature_{nom}_168x94.png"
        img.resize(MOBILE, Image.LANCZOS).save(m, optimize=True)
        sorties[nom] = (p, m, list(TEXTES), nu)
    return sorties


# --- Controles --------------------------------------------------------------------

LEXIQUE_INTERDIT = ("krach", "effondrement", "ruine", "arnaque", "escroquerie", "faillite",
                    "catastrophe", "desastre", "désastre", "tout perdre", "foutu",
                    "on vous ment", "personne n'en parle", "ce qu'on ne vous dit pas",
                    "la verite sur", "la vérité sur", "les banques detestent",
                    "les banques détestent", "garanti", "sans risque", "achetez")
MOTS_MAX = 6                     # decision d'Alexandre, 27/10/2026
CAPITALE_MIN_MOBILE = 7.0        # px de hauteur de capitale en 168x94
CONTRASTE_MIN = 4.5              # WCAG, texte contre le fond


def _lum(h):
    c = [v / 255 for v in rgb(h)[:3]]
    c = [v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4 for v in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def contraste_wcag(a, b):
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def controler(sorties):
    """Une ligne par variante ; renvoie (lignes, tout_ok)."""
    lignes, ok_tout = [], True
    for nom, (p, m, textes, nu) in sorties.items():
        vide = nu.crop(ZONE_DUREE)
        img = Image.open(p)
        poids = p.stat().st_size
        coin = Image.open(p).convert("RGB").crop(ZONE_DUREE)
        ecart_coin = int(np.abs(np.asarray(coin, np.int16) - np.asarray(vide, np.int16)).max())
        tout = " ".join(t[0] for t in textes)
        jetons = tout.replace("’", " ").replace("'", " ").split()
        mots = [j for j in jetons if any(c.isalpha() for c in j)]
        geants = [t[0] for t in textes if t[2] >= 200 and any(c.isdigit() for c in t[0])]
        interdits = [w for w in LEXIQUE_INTERDIT if w in tout.lower()]
        caps = [(police(t[1], t[2]).getbbox("H")[3] - police(t[1], t[2]).getbbox("H")[1])
                / SS * MOBILE[0] / W for t in textes]
        contr = min(contraste_wcag(t[3], t[4]) for t in textes)
        ok = (img.size == (W, H) and poids < POIDS_MAX and ecart_coin <= 3 and len(mots) <= MOTS_MAX
              and len(geants) <= 1 and not interdits and min(caps) >= CAPITALE_MIN_MOBILE
              and contr >= CONTRASTE_MIN)
        ok_tout &= ok
        lignes.append(
            f"{nom} : {img.size[0]}x{img.size[1]}, {poids / 1024:.0f} Ko ; coin duree libre "
            f"(ecart au fond {ecart_coin}) ; texte « {tout} » : {len(mots)} mot(s) "
            f"{mots}, chiffre geant {geants or 'aucun'} ; lexique interdit "
            f"{interdits or 'aucun'} ; capitale en 168x94 : {min(caps):.1f} a "
            f"{max(caps):.1f} px ; contraste min {contr:.1f}:1 -> {'OK' if ok else 'NON'}")
    return lignes, ok_tout


def planche(sorties, dest, duree="9:47"):
    """Les variantes cote a cote : en grand (badge de duree simule dans le
    coin reserve), puis en 168x94 a l'echelle 1, puis agrandies x2."""
    pw, ph, g = 600, 338, 40
    n = len(sorties)
    img = Image.new("RGB", (n * pw + (n + 1) * g, 120 + ph + 60 + 94 * 2 + 140), (24, 24, 24))
    d = ImageDraw.Draw(img)
    f_t = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 30)
    f_p = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 20)
    f_b = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 15)
    for k, (nom, (p, m, *_)) in enumerate(sorties.items()):
        x = g + k * (pw + g)
        d.text((x, 40), f"Variante {nom}", font=f_t, fill=(240, 240, 240))
        grand = Image.open(p).resize((pw, ph), Image.LANCZOS)
        gd = ImageDraw.Draw(grand)
        bw, bh = 52, 24                                   # badge de duree simule
        gd.rounded_rectangle([pw - bw - 8, ph - bh - 8, pw - 8, ph - 8], 4, fill=(0, 0, 0))
        gd.text((pw - 8 - bw / 2, ph - 8 - bh / 2), duree, font=f_b, fill=(255, 255, 255),
                anchor="mm")
        img.paste(grand, (x, 100))
        y = 100 + ph + 30
        d.text((x, y), "168x94 (mobile, echelle 1) et agrandi x2 :", font=f_p,
               fill=(190, 190, 190))
        petit = Image.open(m)
        img.paste(petit, (x, y + 34))
        img.paste(petit.resize((336, 188), Image.NEAREST), (x + 168 + 24, y + 34))
    d.text((g, img.height - 46), "Badge de duree simule (planche seulement) : le coin "
           "inferieur droit des miniatures est laisse au fond.", font=f_p, fill=(150, 150, 150))
    out = dest / "planche.png"
    img.save(out, optimize=True)
    return out


# --- Lecture de metadonnees.md ------------------------------------------------------
# Section « ## Miniatures » : une sous-section « ### A — famille » par variante,
# des lignes « - Cle : valeur ». Les donnees sont calculees ici avec la
# convention 9A de recherche.md (versement en fin de mois, taux mensuel
# equivalent), jamais recopiees a la main.

TAILLES = {  # (ligne simple, ligne en bloc) par famille, en px
    "chiffre": (190, 96), "contraste": (100, 116), "bascule": (100, 124)}
POSE = {"chiffre": {"y_lignes": 150}}


def annees(mensuel, taux, n):
    """[(annee, verse cumule, capital, interets de l'annee)] - convention 9A."""
    i = (1 + taux) ** (1 / 12) - 1
    c = verse = 0.0
    out = []
    for a in range(1, n + 1):
        it_an = 0.0
        for _ in range(12):
            it = c * i
            c += it
            it_an += it
            c += mensuel
            verse += mensuel
        out.append((a, verse, c, it_an))
    return out


def annee_bascule(mensuel, taux):
    """Premiere annee ou les interets de l'annee depassent ses versements."""
    for a, _, _, it_an in annees(mensuel, taux, 100):
        if it_an > 12 * mensuel:
            return a
    sys.exit(f"pas de bascule en 100 ans a {100 * taux:g} %")


def _taux(s):
    return float(s.replace(",", ".")) / 100


def _parametres(s):
    m = re.search(r"([\d ]+)\s*€\s*/\s*mois", s)
    t = re.search(r"(\d+(?:,\d+)?)\s*%", s)
    n = re.search(r"(\d+)\s*ans", s)
    if not (m and t and n):
        sys.exit(f"miniatures : « {s} » doit donner €/mois, taux en % et duree en ans")
    return int(m.group(1).replace(" ", "")), _taux(t.group(1)), int(n.group(1))


def typo(s):
    """Typographie francaise : apostrophe courbe, espace fine avant ? ! : ;"""
    s = s.replace("'", "’")
    return re.sub(r"\s*([?!:;])", " \\1", s)


def lignes_texte(texte, famille):
    """« a / ==b== / c {x} [y] » -> lignes de poser()."""
    simple, en_bloc = TAILLES[famille]
    boite = "INK" if "{" in texte else "INTEREST"   # l'ambre est deja pris par un mot
    out = []
    for brut in (x.strip() for x in texte.split(" / ")):
        if brut.startswith("==") and brut.endswith("=="):
            out.append({"texte": typo(brut[2:-2].strip()), "taille": en_bloc, "couleur": "BG",
                        "boite": boite, "angle": 4})
            continue
        segs = [[typo(t), {"{": "INTEREST", "[": "CONTRIB"}.get(t[:1], "INK")]
                for t in re.split(r"(\{[^}]*\}|\[[^\]]*\])", brut) if t]
        segs = [[t.strip("{}[]") if c != "INK" else t, c] for t, c in segs]
        out.append({"segments": segs, "taille": simple})
    return out


def lire_metadonnees(ep_dir):
    md = (ep_dir / "metadonnees.md").read_text(encoding="utf-8")
    m = re.search(r"^## Miniatures\s*$(.*?)(?=^## |\Z)", md, re.M | re.S)
    if not m:
        sys.exit(f"{ep_dir / 'metadonnees.md'} : pas de section « ## Miniatures »")
    titre = re.search(r"\*\*Retenu\*\*\s*:\s*(.+)", md)
    variantes = {}
    for nom, famille, corps in re.findall(r"^### (\w+)\s*[—-]\s*(\w+)\s*$(.*?)(?=^### |\Z)",
                                          m.group(1), re.M | re.S):
        if famille not in FAMILLES:
            sys.exit(f"miniature {nom} : famille inconnue « {famille} »")
        cles = dict(re.findall(r"^- ([^:\n]+?)\s*:\s*(.+?)\s*$", corps, re.M))
        b = {"famille": famille, "lignes": lignes_texte(cles["Texte"], famille),
             "texte_source": cles["Texte"], **POSE.get(famille, {})}
        if famille == "chiffre":
            b["chiffre"] = cles["Chiffre"]
            b["barres"] = []
            for part in cles["Barres"].split(";"):
                lab, regle = (x.strip() for x in part.split("="))
                t = re.search(r"bascule\s+(\d+(?:,\d+)?)\s*%", regle)
                b["barres"].append([lab, annee_bascule(200, _taux(t.group(1)))])
                b.setdefault("taux_cites", []).append(t.group(1) + " %")
            ecart = abs(b["barres"][0][1] - b["barres"][1][1])
            if str(ecart) != b["chiffre"]:
                sys.exit(f"miniature {nom} : le chiffre {b['chiffre']} n'est pas l'ecart des "
                         f"barres ({b['barres'][0][1]} - {b['barres'][1][1]} = {ecart})")
        elif famille == "contraste":
            mensuel, taux, n = _parametres(cles["Courbes"])
            t = annees(mensuel, taux, n)
            b["bas"] = [0] + [round(x[1]) for x in t]
            b["haut"] = [0] + [round(x[2]) for x in t]
            b["taux_cites"] = [f"{100 * taux:g} %".replace(".", ",")]
        elif famille == "bascule":
            mensuel, taux, n = _parametres(cles["Courbes"])
            t = annees(mensuel, taux, n)
            b["fixe"] = 12 * mensuel
            b["courbe"] = [round(x[3]) for x in t]
            b["croisement"] = annee_bascule(mensuel, taux)
            b["taux_cites"] = [f"{100 * taux:g} %".replace(".", ",")]
        variantes[nom] = b
    if not variantes:
        sys.exit("metadonnees.md : section Miniatures sans variante « ### A — famille »")
    return {"episode": ep_dir.name, "titre": titre.group(1).strip() if titre else None,
            "variantes": variantes}


def chiffres_sources(brief, ep_dir):
    """Chaque nombre affiche ou utilise doit figurer dans recherche.md."""
    rech = (ep_dir / "recherche.md").read_text(encoding="utf-8").replace(" ", " ")
    absents = []
    for nom, b in brief["variantes"].items():
        vus = [b.get("chiffre", "")] + b.get("taux_cites", [])
        vus += re.findall(r"\d+(?:,\d+)?\s*%?", b["texte_source"])
        vus += [lab for lab, _ in b.get("barres", [])]
        for v in filter(None, (x.strip() for x in vus)):
            for num in re.findall(r"\d+(?:,\d+)?", v):
                if not re.search(rf"(?<![\d,]){re.escape(num)}(?![\d,])", rech):
                    absents.append(f"{nom} : {num}")
    return absents


def duree_episode(ep_dir):
    tl = ep_dir / "build" / "timeline.json"
    if not tl.exists():
        return None
    s = int(json.loads(tl.read_text(encoding="utf-8"))["duree_totale_s"])
    return f"{s // 60}:{s % 60:02d}"


def main():
    racine = Path(__file__).resolve().parent.parent
    if len(sys.argv) != 2:
        sys.exit("usage : python video/miniature.py EP001c")
    ep_dir = racine / "episodes" / sys.argv[1]
    brief = lire_metadonnees(ep_dir)
    absents = chiffres_sources(brief, ep_dir)
    dest = ep_dir / "build" / "miniatures"
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "brief.json").write_text(json.dumps(brief, ensure_ascii=False, indent=1),
                                     encoding="utf-8")
    sorties = rendre(brief, dest)
    lignes, ok = controler(sorties)
    print(f"titre retenu : {brief['titre']}")
    print("\n".join(lignes))
    print("chiffres absents de recherche.md :", ", ".join(absents) or "aucun")
    print("planche :", planche(sorties, dest, duree_episode(ep_dir) or "0:00"))
    sys.exit(0 if ok and not absents else 1)


if __name__ == "__main__":
    main()
