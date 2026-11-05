# -*- coding: utf-8 -*-
"""Identite de chaine - Clair net enrichi : declinaisons du logo retenu.

Logo retenu par Alexandre le 05/11/2026 : la piece frappee, gravure bleue,
cercle encre (piste Q2 de logo.py). Ce script produit les fichiers maitres
(SVG, texte vectorise en traces) et leurs exports PNG, les exports de
controle des zones sures, puis l'archive de livraison.

    python identite/declinaisons.py

Gabarits YouTube (aide YouTube, « Manage your channel branding », lue le
05/11/2026) : banniere 2560x1440 recommandee, 6 Mo au plus ; zone sure
1235x338 a la dimension minimale 2048x1152, soit 1546x423 a 2560x1440 ;
avatar affiche a 98x98, 15 Mo au plus ; filigrane carre, 150x150 au moins,
moins de 1 Mo.
"""

import math
import shutil
import sys
import zipfile
from pathlib import Path

import cairo
import numpy as np

import logo
from logo import rgb, style

ICI = Path(__file__).resolve().parent
LIVRAISON = ICI / "livraison"
ARCHIVE = ICI / "clair-net-enrichi-identite.zip"

SYMBOLE = logo.piste_q2
PLEIN = {"a": style.CONTRIB, "b": style.INTEREST, "fond": style.BG}   # fond non nul : piece pleine

NOM = "Clair Net Enrichi"          # majuscules demandees par Alexandre le 05/11/2026
SIGNATURE = "Faites travailler votre argent. Pas l'inverse."   # S3, retenue le 05/11/2026
GRAISSE_SIG = "sb"            # Semibold : le sous-titre agrandi doit tenir la vue mobile
# Relief complet, retenu pour l'avatar le 05/11/2026 puis etendu a toutes les
# versions couleur (banniere, filigrane, logos) pour que la piece soit partout
# la meme. Les monochromes et logo_couleur_aplat restent en aplat.
RELIEF = "R4"

BANNIERE = (2560, 1440)
ZONE_SURE = (1546, 423)       # visible sur tous les ecrans ; seule zone visible sur mobile
BANDE_ORDI = (2560, 423)
BANDE_TABLETTE = (1855, 423)
AVATAR = 800
FILIGRANE = 150
LIMITES_MO = {"banniere": 6, "avatar": 15, "filigrane": 1}

# couleurs des exports de controle seulement (hors charte)
CTRL_SURE, CTRL_ORDI, CTRL_TABLETTE, CTRL_MESURE = "#FF2D95", "#00E5FF", "#B4FF39", "#FFFFFF"


def rect_centre(w, h, tout=BANNIERE):
    W, H = tout
    return (W - w) / 2, (H - h) / 2, w, h


# --- Briques -----------------------------------------------------------------------

def symbole(ctx, cx, cy, d, pal=PLEIN, relief=True):
    """Le logo, de diametre d, centre en (cx, cy) ; en couleur, la piece en relief."""
    ctx.save()
    ctx.translate(cx - d / 2, cy - d / 2)
    ctx.scale(d, d)
    if pal is PLEIN and relief:
        piece_relief(ctx, **RELIEFS[RELIEF][1])
    else:
        SYMBOLE(ctx, pal)
    ctx.restore()


def ecrire(ctx, s, x, y, corps, graisse, couleur):
    ctx.new_path()
    logo.texte(ctx, s, x, y, corps, graisse)
    ctx.set_source_rgb(*rgb(couleur))
    ctx.fill()


def _upm():
    return logo.fonte("b")["head"].unitsPerEm


def composition(cx, cy, d, corps_nom, corps_sig, ecart_logo, ecart_lignes, sig=SIGNATURE):
    """Bloc logo + nom (+ signature sig, None pour aucune), centre en (cx, cy)."""
    signature = sig is not None
    upm = _upm()
    haut_cap = 1434 / upm                    # sCapHeight de Selawik
    l_nom = logo.chasse(NOM, "b") / upm * corps_nom
    l_sig = logo.chasse(sig, GRAISSE_SIG) / upm * corps_sig if signature else 0
    l_txt = max(l_nom, l_sig)
    largeur = d + ecart_logo + l_txt
    x0 = cx - largeur / 2
    h_txt = haut_cap * corps_nom + (ecart_lignes + haut_cap * corps_sig if signature else 0)
    haut = cy - h_txt / 2
    return {
        "logo": (x0 + d / 2, cy, d),
        "nom": (x0 + d + ecart_logo, haut + haut_cap * corps_nom, corps_nom),
        "sig": (x0 + d + ecart_logo, haut + h_txt, corps_sig, sig) if signature else None,
        "largeur": largeur,
    }


def pose_composition(ctx, comp, couleur_nom=style.INK, couleur_sig=style.INK_SOFT, pal=PLEIN):
    symbole(ctx, *comp["logo"], pal=pal)
    x, y, c = comp["nom"]
    ecrire(ctx, NOM, x, y, c, "b", couleur_nom)
    if comp["sig"]:
        x, y, c, s = comp["sig"]
        ecrire(ctx, s, x, y, c, GRAISSE_SIG, couleur_sig)


# --- Banniere ---------------------------------------------------------------------------
# Decor : grille fine et la signature de la chaine, la droite des versements
# (bleu) et l'exponentielle des interets (ambre). Leur croisement tombe a
# droite de la zone sure, dans la bande visible sur ordinateur : jamais sous
# le texte. Tout le texte et le logo restent dans la zone sure.

def _droite(t):
    return 1180 - 380 * t


def _expo(t, k=5.0):
    return 1300 - 820 * (math.exp(k * t) - 1) / (math.exp(k) - 1)


def croisement():
    lo, hi = 0.5, 1.0
    for _ in range(60):
        m = (lo + hi) / 2
        lo, hi = (m, hi) if _expo(m) > _droite(m) else (lo, m)
    return lo * BANNIERE[0], _droite(lo)


def compo_banniere(sig=SIGNATURE):
    W, H = BANNIERE
    # nom et sous-titre agrandis (retour du 05/11/2026) : le bloc occupe la
    # largeur de la zone sure, a une quarantaine de pixels des bords
    return composition(W / 2, H / 2, 262, 152, 60, 54, 34, sig)


def banniere(ctx, decor=True, contenu=True, sig=SIGNATURE):
    W, H = BANNIERE
    if decor:
        degrade = cairo.LinearGradient(0, 0, 0, H)
        degrade.add_color_stop_rgb(0, *rgb(style.BG_LIFT))
        degrade.add_color_stop_rgb(0.6, *rgb(style.BG))
        ctx.set_source(degrade)
        ctx.rectangle(0, 0, W, H)
        ctx.fill()
        ctx.set_source_rgb(*rgb(style.RULE))
        ctx.set_line_width(2)
        for x in range(0, W + 1, 128):
            ctx.move_to(x, 0)
            ctx.line_to(x, H)
        for y in range(16, H + 1, 128):
            ctx.move_to(0, y)
            ctx.line_to(W, y)
        ctx.stroke()
        logo.trait(ctx, style.CONTRIB, 8, [(0, _droite(0)), (W, _droite(1))])
        logo.trait(ctx, style.INTEREST, 8, [(W * i / 400, _expo(i / 400)) for i in range(401)])
        xc, yc = croisement()
        ctx.set_source_rgb(*rgb(style.INTEREST))
        ctx.new_path()
        ctx.arc(xc, yc, 15, 0, 2 * math.pi)
        ctx.fill()
    if contenu:
        pose_composition(ctx, compo_banniere(sig))


# --- Autres declinaisons -------------------------------------------------------------------

def avatar(ctx, fond=True):
    """800x800 : YouTube recadre en rond ; la piece en relief tient dans le cercle."""
    if fond:
        ctx.set_source_rgb(*rgb(style.BG))
        ctx.rectangle(0, 0, AVATAR, AVATAR)
        ctx.fill()
    symbole(ctx, AVATAR / 2, AVATAR / 2, AVATAR)


def filigrane(ctx):
    symbole(ctx, FILIGRANE / 2, FILIGRANE / 2, FILIGRANE)


def logo_seul(pal, cote=1000, relief=True):
    return lambda ctx: symbole(ctx, cote / 2, cote / 2, cote, pal, relief)


COMPO_LOGO_NOM = (2200, 600)


def logo_nom(ctx, blanc=False):
    w, h = COMPO_LOGO_NOM
    comp = composition(w / 2, h / 2, 460, 200, 0, 90, 0, sig=None)
    if blanc:
        pose_composition(ctx, comp, "#FFFFFF", pal=logo.BLANC)
    else:
        pose_composition(ctx, comp)


# --- Export ---------------------------------------------------------------------------------

def svg(chemin, w, h, dessin):
    s = cairo.SVGSurface(str(chemin), w, h)
    s.set_document_unit(cairo.SVGUnit.PX)
    dessin(cairo.Context(s))
    s.finish()
    texte = chemin.read_text(encoding="utf-8")
    assert "<image" not in texte, f"{chemin.name} contient une image matricielle"
    return chemin


def rendu(w, h, dessin, k=1.0):
    img = cairo.ImageSurface(cairo.FORMAT_ARGB32, round(w * k), round(h * k))
    c = cairo.Context(img)
    c.scale(k, k)
    dessin(c)
    img.flush()
    return img


def alpha(img):
    a = np.ndarray((img.get_height(), img.get_stride() // 4, 4), np.uint8, img.get_data())
    return a[:, :img.get_width(), 3]


def boite(img):
    """Boite (x0, y0, x1, y1) des pixels non transparents, bords exclus."""
    ys, xs = np.nonzero(alpha(img))
    return int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1


def png(img, chemin):
    img.write_to_png(str(chemin))
    return chemin


# --- Controles ------------------------------------------------------------------------------

def _rect_pointille(ctx, couleur, x, y, w, h, ep=4):
    ctx.set_source_rgb(*rgb(couleur))
    ctx.set_line_width(ep)
    ctx.set_dash([24, 14])
    ctx.rectangle(x, y, w, h)
    ctx.stroke()
    ctx.set_dash([])


def _etiquette(ctx, s, x, y, couleur, corps=30):
    ctx.select_font_face("Segoe UI", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(corps)
    e = ctx.text_extents(s)
    ctx.set_source_rgba(0, 0, 0, 0.7)
    ctx.rectangle(x - 8, y - corps - 4, e.x_advance + 16, corps + 16)
    ctx.fill()
    ctx.set_source_rgb(*rgb(couleur))
    ctx.move_to(x, y)
    ctx.show_text(s)


def controle_banniere(dossier):
    W, H = BANNIERE
    contenu = rendu(W, H, lambda c: banniere(c, decor=False))
    bx0, by0, bx1, by1 = boite(contenu)
    zx, zy, zw, zh = rect_centre(*ZONE_SURE)
    dans = bx0 >= zx and by0 >= zy and bx1 <= zx + zw and by1 <= zy + zh
    marges = (bx0 - zx, by0 - zy, zx + zw - bx1, zy + zh - by1)
    xc, yc = croisement()
    ox, oy, ow, oh = rect_centre(*BANDE_ORDI)
    croix_visible_ordi = ox <= xc <= ox + ow and oy <= yc <= oy + oh
    croix_hors_zone = not (zx <= xc <= zx + zw)

    img = rendu(W, H, banniere)
    ctx = cairo.Context(img)
    tx, ty, tw, th = rect_centre(*BANDE_TABLETTE)
    _rect_pointille(ctx, CTRL_ORDI, ox + 3, oy, ow - 6, oh)
    _rect_pointille(ctx, CTRL_TABLETTE, tx, ty + 10, tw, th - 20)
    ctx.set_source_rgb(*rgb(CTRL_SURE))
    ctx.set_line_width(6)
    ctx.rectangle(zx, zy, zw, zh)
    ctx.stroke()
    ctx.set_source_rgb(*rgb(CTRL_MESURE))
    ctx.set_line_width(2)
    ctx.rectangle(bx0, by0, bx1 - bx0, by1 - by0)
    ctx.stroke()
    _etiquette(ctx, "Télévision : 2560 × 1440 (image entière)", 40, 70, "#FFFFFF")
    _etiquette(ctx, "Ordinateur : 2560 × 423", 40, oy - 24, CTRL_ORDI)
    _etiquette(ctx, "Tablette : 1855 × 423", tx + tw - 340, ty - 24, CTRL_TABLETTE)
    _etiquette(ctx, "Zone sûre, tous écrans et mobile : 1546 × 423", zx + 8, zy + zh + 56, CTRL_SURE)
    _etiquette(ctx, f"Contenu mesuré (trait blanc) : {bx1 - bx0} × {by1 - by0} px, marges "
                    f"gauche {marges[0]:.0f}, haut {marges[1]:.0f}, droite {marges[2]:.0f}, "
                    f"bas {marges[3]:.0f} px", zx + 8, zy + zh + 110, CTRL_MESURE, 26)
    chemin = png(img, dossier / "controle_banniere.png")
    return {
        "controle": chemin,
        "contenu_dans_zone_sure": dans,
        "boite_contenu": (bx0, by0, bx1, by1),
        "zone_sure": (zx, zy, zx + zw, zy + zh),
        "marges_g_h_d_b": marges,
        "croisement": (round(xc), round(yc)),
        "croisement_visible_sur_ordinateur": croix_visible_ordi,
        "croisement_hors_zone_sure": croix_hors_zone,
    }


def controle_avatar(dossier):
    sym = rendu(AVATAR, AVATAR, lambda c: avatar(c, fond=False))
    a = alpha(sym)
    ys, xs = np.nonzero(a)
    r_max = float(np.max(np.hypot(xs + 0.5 - AVATAR / 2, ys + 0.5 - AVATAR / 2)))
    dans = r_max <= AVATAR / 2

    W, H = 1460, 880
    img = cairo.ImageSurface(cairo.FORMAT_RGB24, W, H)
    ctx = cairo.Context(img)
    ctx.set_source_rgb(*rgb("#1E242D"))
    ctx.paint()
    av = rendu(AVATAR, AVATAR, avatar)
    ctx.set_source_surface(av, 40, 40)
    ctx.paint()
    # hors du cercle de recadrage : assombri
    ctx.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
    ctx.rectangle(40, 40, AVATAR, AVATAR)
    ctx.arc(40 + AVATAR / 2, 40 + AVATAR / 2, AVATAR / 2, 0, 2 * math.pi)
    ctx.set_source_rgba(1, 0.18, 0.58, 0.35)
    ctx.fill()
    ctx.set_fill_rule(cairo.FILL_RULE_WINDING)
    ctx.set_source_rgb(*rgb(CTRL_SURE))
    ctx.set_line_width(4)
    ctx.arc(40 + AVATAR / 2, 40 + AVATAR / 2, AVATAR / 2, 0, 2 * math.pi)
    ctx.stroke()
    ctx.set_source_rgb(*rgb(CTRL_MESURE))
    ctx.set_line_width(2)
    ctx.set_dash([10, 8])
    ctx.arc(40 + AVATAR / 2, 40 + AVATAR / 2, r_max, 0, 2 * math.pi)
    ctx.stroke()
    ctx.set_dash([])
    _etiquette(ctx, "Recadrage YouTube", 880, 90, CTRL_SURE, 26)
    _etiquette(ctx, f"Rayon du symbole : {r_max:.0f} px sur 400", 880, 140, CTRL_MESURE, 26)
    x = 880
    for d, fond in ((98, "#0F0F0F"), (98, "#FFFFFF"), (48, "#0F0F0F"), (48, "#FFFFFF")):
        ctx.set_source_rgb(*rgb(fond))
        ctx.rectangle(x, 200, d + 24, d + 24)
        ctx.fill()
        petit = rendu(AVATAR, AVATAR, avatar, d / AVATAR)
        ctx.save()
        ctx.arc(x + 12 + d / 2, 212 + d / 2, d / 2, 0, 2 * math.pi)
        ctx.clip()
        ctx.set_source_surface(petit, x + 12, 212)
        ctx.paint()
        ctx.restore()
        x += d + 36
    _etiquette(ctx, "Affichage réel : 98 px et 48 px", 880, 380, "#FFFFFF", 22)
    chemin = dossier / "controle_avatar.png"
    img.write_to_png(str(chemin))
    return {"controle": chemin, "symbole_dans_le_cercle": dans, "rayon_max_px": round(r_max, 1)}


# --- Pistes : relief de l'avatar (retour d'Alexandre, 05/11/2026) ------------------------------
# Tout reste vectoriel : degrades et decalages, pas de flou (un flou ferait
# entrer une image matricielle dans le SVG maitre). Les teintes claires et
# foncees sont tirees de l'ambre et du bleu de la charte.

def melange(h1, h2, t):
    a, b = rgb(h1), rgb(h2)
    return "#" + "".join(f"{round((x + (y - x) * t) * 255):02X}" for x, y in zip(a, b))


AMBRE_CLAIR = melange(style.INTEREST, "#FFFFFF", 0.40)
AMBRE_FONCE = melange(style.INTEREST, "#000000", 0.30)
AMBRE_TRANCHE = melange(style.INTEREST, "#000000", 0.50)


def _gravure(ctx, cercle, sablier, dx=0.0, dy=0.0):
    """Cercle et sablier ouvert de la piece Q2, decales de (dx, dy)."""
    ctx.save()
    ctx.translate(dx, dy)
    ctx.set_source_rgb(*rgb(cercle))
    ctx.set_line_width(0.028)
    ctx.new_path()
    ctx.arc(0.5, 0.5, 0.41, 0, 2 * math.pi)
    ctx.stroke()
    ctx.translate(0.5, 0.5)
    ctx.scale(0.66, 0.66)
    ctx.translate(-0.5, -0.5)
    logo.piste_l(ctx, {"a": sablier, "b": sablier, "fond": None})
    ctx.restore()


def _degrade(cx, cy, r, stops):
    g = cairo.LinearGradient(cx - r * 0.7, cy - r * 0.7, cx + r * 0.7, cy + r * 0.7)
    for t, h in stops:
        g.add_color_stop_rgb(t, *rgb(h))
    return g


def piece_relief(ctx, degrade=False, biseau=False, relief=False, tranche=False):
    """La piece Q2 dans un carre unite, avec les effets de relief demandes."""
    cx, cy, r = 0.5, 0.5, 0.48
    if tranche:                       # piece vue un peu de dessus : la tranche depasse en bas
        cx, cy, r = 0.5, 0.483, 0.455
        ctx.set_source_rgb(*rgb(AMBRE_TRANCHE))
        ctx.new_path()
        ctx.arc(cx, cy + 0.034, r, 0, 2 * math.pi)
        ctx.fill()
    if degrade:                       # lumiere en haut a gauche
        ctx.set_source(_degrade(cx, cy, r, [(0, AMBRE_CLAIR), (0.45, style.INTEREST), (1, AMBRE_FONCE)]))
    else:
        ctx.set_source_rgb(*rgb(style.INTEREST))
    ctx.new_path()
    ctx.arc(cx, cy, r, 0, 2 * math.pi)
    ctx.fill()
    if biseau:                        # le champ, dans le cercle, est en creux : degrade inverse
        r_in = 0.395 * r / 0.48
        ctx.set_source(_degrade(cx, cy, r_in, [(0, melange(style.INTEREST, "#000000", 0.12)),
                                               (1, melange(style.INTEREST, "#FFFFFF", 0.22))]))
        ctx.new_path()
        ctx.arc(cx, cy, r_in, 0, 2 * math.pi)
        ctx.fill()
    ctx.save()
    ctx.translate(cx, cy)
    ctx.scale(r / 0.48, r / 0.48)
    ctx.translate(-0.5, -0.5)
    if relief:                        # gravure en bosse : ombre en bas a droite, reflet en haut a gauche
        e = 0.011
        _gravure(ctx, AMBRE_FONCE, AMBRE_FONCE, e, e)
        _gravure(ctx, AMBRE_CLAIR, AMBRE_CLAIR, -e * 0.7, -e * 0.7)
    _gravure(ctx, style.BG, style.CONTRIB)
    ctx.restore()


RELIEFS = {
    "aplat": ("Actuel (aplat)", {}),
    "R1": ("Gravure en relief", {"relief": True}),
    "R2": ("Pièce dorée", {"degrade": True, "biseau": True}),
    "R3": ("Sur la tranche", {"tranche": True, "degrade": True}),
    "R4": ("Relief complet", {"degrade": True, "biseau": True, "relief": True, "tranche": True}),
}


def avatar_relief(options):
    def dessin(ctx):
        ctx.set_source_rgb(*rgb(style.BG))
        ctx.rectangle(0, 0, AVATAR, AVATAR)
        ctx.fill()
        ctx.save()
        ctx.scale(AVATAR, AVATAR)
        piece_relief(ctx, **options)
        ctx.restore()
    return dessin


def _rond(ctx, img, x, y, d):
    ctx.save()
    ctx.new_path()
    ctx.arc(x + d / 2, y + d / 2, d / 2, 0, 2 * math.pi)
    ctx.clip()
    ctx.set_source_surface(img, x, y)
    ctx.paint()
    ctx.restore()


def _titre(ctx, s, x, y, corps, couleur=style.INK, gras=True):
    ctx.select_font_face("Segoe UI", cairo.FONT_SLANT_NORMAL,
                         cairo.FONT_WEIGHT_BOLD if gras else cairo.FONT_WEIGHT_NORMAL)
    ctx.set_font_size(corps)
    ctx.set_source_rgb(*rgb(couleur))
    ctx.move_to(x, y)
    ctx.show_text(s)


def exploration_avatars():
    dossier = ICI / "exploration" / "avatar_relief"
    dossier.mkdir(parents=True, exist_ok=True)
    col, marge = 290, 40
    W, H = marge * 2 + col * len(RELIEFS), 650
    img = cairo.ImageSurface(cairo.FORMAT_RGB24, W, H)
    ctx = cairo.Context(img)
    ctx.set_source_rgb(*rgb("#1E242D"))
    ctx.paint()
    _titre(ctx, "Avatar : pistes de relief", marge, 46, 26)
    _titre(ctx, "Recadré en rond comme sur YouTube. Pixels réels pour 98 et 48 px.", marge, 76, 15,
           style.MUTED, False)
    for i, (cle, (nom, options)) in enumerate(RELIEFS.items()):
        x = marge + i * col
        dessin = avatar_relief(options)
        svg(dossier / f"avatar_{cle}.svg", AVATAR, AVATAR, dessin)
        png(rendu(AVATAR, AVATAR, dessin), dossier / f"avatar_{cle}_800.png")
        _titre(ctx, nom if cle == "aplat" else f"{cle}. {nom}", x, 130, 19)
        ctx.set_source_rgb(*rgb(YT_SOMBRE))
        ctx.rectangle(x, 150, 260, 260)
        ctx.fill()
        _rond(ctx, rendu(AVATAR, AVATAR, dessin, 240 / AVATAR), x + 10, 160, 240)
        bx = x
        for d, fond in ((98, YT_SOMBRE), (98, YT_CLAIR)):
            ctx.set_source_rgb(*rgb(fond))
            ctx.rectangle(bx, 430, 122, 122)
            ctx.fill()
            _rond(ctx, rendu(AVATAR, AVATAR, dessin, d / AVATAR), bx + 12, 442, d)
            bx += 130
        bx = x
        for fond in (YT_SOMBRE, YT_CLAIR):
            ctx.set_source_rgb(*rgb(fond))
            ctx.rectangle(bx, 560, 60, 60)
            ctx.fill()
            _rond(ctx, rendu(AVATAR, AVATAR, dessin, 48 / AVATAR), bx + 6, 566, 48)
            bx += 66
    chemin = dossier / "planche_avatars.png"
    img.write_to_png(str(chemin))
    return chemin


# --- Pistes : sous-titre de la banniere (retour d'Alexandre, 05/11/2026) -----------------------

SIGNATURES = [
    "Moins de jargon, plus d'intérêts.",
    "La liberté financière, preuves à l'appui.",
    "Faites travailler votre argent. Pas l'inverse.",
    "Ce que votre banque ne vous explique pas.",
]

YT_SOMBRE, YT_CLAIR = "#0F0F0F", "#FFFFFF"


def exploration_signatures():
    """Chaque sous-titre dans la zone sure (ce qu'on voit sur mobile), a mi-echelle."""
    dossier = ICI / "exploration" / "signatures"
    dossier.mkdir(parents=True, exist_ok=True)
    W, H = BANNIERE
    zx, zy, zw, zh = rect_centre(*ZONE_SURE)
    k = 0.5
    pw, ph = round(zw * k), round(zh * k)
    marge, pas = 40, ph + 70
    img = cairo.ImageSurface(cairo.FORMAT_RGB24, pw + 2 * marge, 100 + pas * len(SIGNATURES))
    ctx = cairo.Context(img)
    ctx.set_source_rgb(*rgb("#1E242D"))
    ctx.paint()
    _titre(ctx, "Bannière : pistes de sous-titre (zone sûre, vue mobile)", marge, 46, 24)
    controles = []
    for i, s in enumerate(SIGNATURES):
        y = 100 + i * pas
        _titre(ctx, f"S{i + 1}. « {s} »", marge, y + 22, 17, style.INK_SOFT, False)
        ban = rendu(W, H, lambda c, s=s: banniere(c, sig=s), k)
        ctx.save()
        ctx.rectangle(marge, y + 36, pw, ph)
        ctx.clip()
        ctx.set_source_surface(ban, marge - zx * k, y + 36 - zy * k)
        ctx.paint()
        ctx.restore()
        bx0, by0, bx1, by1 = boite(rendu(W, H, lambda c, s=s: banniere(c, decor=False, sig=s)))
        controles.append((s, bx0 >= zx and by0 >= zy and bx1 <= zx + zw and by1 <= zy + zh,
                          round(bx0 - zx), round(zx + zw - bx1)))
    chemin = dossier / "planche_signatures.png"
    img.write_to_png(str(chemin))
    for s, ok, mg, md in controles:
        print(f"{'OK ' if ok else 'HORS'} marges {mg}/{md} px : {s}")
    return chemin


# --- Livraison ------------------------------------------------------------------------------

def produit():
    if LIVRAISON.exists():
        shutil.rmtree(LIVRAISON)
    d_logo, d_yt, d_ctrl, d_pol = (LIVRAISON / n for n in ("logo", "youtube", "controles", "polices"))
    for d in (d_logo, d_yt, d_ctrl, d_pol):
        d.mkdir(parents=True)

    # logo maitre (relief), version couleur en aplat, monochromes
    for nom, pal, relief in (("couleur", PLEIN, True), ("couleur_aplat", PLEIN, False),
                             ("blanc", logo.BLANC, False), ("noir", logo.NOIR, False)):
        dessin = logo_seul(pal, relief=relief)
        svg(d_logo / f"logo_{nom}.svg", 1000, 1000, dessin)
        for k in (1.024, 0.512):
            png(rendu(1000, 1000, dessin, k), d_logo / f"logo_{nom}_{round(1000 * k)}.png")
    w, h = COMPO_LOGO_NOM
    svg(d_logo / "logo_nom_fond_sombre.svg", w, h, logo_nom)
    png(rendu(w, h, logo_nom), d_logo / "logo_nom_fond_sombre.png")
    svg(d_logo / "logo_nom_blanc.svg", w, h, lambda c: logo_nom(c, blanc=True))
    png(rendu(w, h, lambda c: logo_nom(c, blanc=True)), d_logo / "logo_nom_blanc.png")

    # YouTube
    W, H = BANNIERE
    svg(d_yt / "banniere_2560x1440.svg", W, H, banniere)
    ban = png(rendu(W, H, banniere), d_yt / "banniere_2560x1440.png")
    svg(d_yt / "avatar_800x800.svg", AVATAR, AVATAR, avatar)
    av = png(rendu(AVATAR, AVATAR, avatar), d_yt / "avatar_800x800.png")
    svg(d_yt / "filigrane_150x150.svg", FILIGRANE, FILIGRANE, filigrane)
    fil_img = rendu(FILIGRANE, FILIGRANE, filigrane)
    fil = png(fil_img, d_yt / "filigrane_150x150.png")

    # controles
    r_ban = controle_banniere(d_ctrl)
    r_av = controle_avatar(d_ctrl)
    a = alpha(fil_img)
    r_fil = {
        "taille": (fil_img.get_width(), fil_img.get_height()),
        "coins_transparents": bool(a[0, 0] == a[0, -1] == a[-1, 0] == a[-1, -1] == 0),
    }
    poids = {n: p.stat().st_size / 1e6 for n, p in (("banniere", ban), ("avatar", av), ("filigrane", fil))}

    # polices et fiche
    for f in sorted(logo.POLICES.glob("*")):
        shutil.copy(f, d_pol / f.name)
    shutil.copy(ICI / "LISEZ-MOI.md", LIVRAISON / "LISEZ-MOI.md")

    rapport = [
        f"Controles de livraison - identite {NOM}",
        "",
        f"Banniere : contenu (texte + logo) dans la zone sure : {r_ban['contenu_dans_zone_sure']}",
        f"  boite du contenu {r_ban['boite_contenu']}, zone sure {r_ban['zone_sure']}",
        "  marges gauche/haut/droite/bas : " + " / ".join(f"{m:.1f}" for m in r_ban["marges_g_h_d_b"]) + " px",
        f"  croisement des courbes en {r_ban['croisement']} : visible sur ordinateur "
        f"{r_ban['croisement_visible_sur_ordinateur']}, hors zone sure {r_ban['croisement_hors_zone_sure']}",
        f"Avatar : symbole dans le cercle de recadrage : {r_av['symbole_dans_le_cercle']} "
        f"(rayon max {r_av['rayon_max_px']} px sur 400)",
        f"Filigrane : {r_fil['taille'][0]}x{r_fil['taille'][1]}, coins transparents : {r_fil['coins_transparents']}",
        "Poids (limite YouTube) : " + ", ".join(
            f"{n} {poids[n]:.2f} Mo ({LIMITES_MO[n]} Mo)" for n in poids),
        "SVG : aucun ne contient d'image matricielle (texte vectorise en traces).",
    ]
    (d_ctrl / "rapport.txt").write_text("\n".join(rapport) + "\n", encoding="utf-8")

    ok = (r_ban["contenu_dans_zone_sure"] and r_ban["croisement_visible_sur_ordinateur"]
          and r_ban["croisement_hors_zone_sure"] and r_av["symbole_dans_le_cercle"]
          and r_fil["taille"] == (150, 150) and r_fil["coins_transparents"]
          and all(poids[n] < LIMITES_MO[n] for n in poids))

    if ARCHIVE.exists():
        ARCHIVE.unlink()
    with zipfile.ZipFile(ARCHIVE, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(LIVRAISON.rglob("*")):
            if f.is_file():
                z.write(f, Path("clair-net-enrichi-identite") / f.relative_to(LIVRAISON))
    print("\n".join(rapport))
    print(f"Archive : {ARCHIVE}")
    return ok


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "livraison"
    if action == "avatars":
        print(exploration_avatars())
    elif action == "signatures":
        print(exploration_signatures())
    else:
        sys.exit(0 if produit() else 1)
