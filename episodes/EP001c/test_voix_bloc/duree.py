#!/usr/bin/env python3
"""
Estimation de la duree de lecture d'un script francais par ElevenLabs.

Unite de mesure : la SYLLABE, pas le mot.
D'un segment a l'autre, le debit en mots/minute varie d'environ 45 % parce que
la longueur des mots varie enormement ("or" contre "quatre-vingt-dix-neuf").
Le debit en syllabes/seconde, lui, varie d'environ 7 %. C'est donc la seule
unite sur laquelle un budget de script peut reposer.

Le compteur de syllabes ci-dessous est une heuristique, pas une analyse
phonetique. Ce n'est pas un defaut : le MEME compteur sert a la calibration et
a la prediction, donc son biais systematique s'annule dans le rapport. Ne le
remplacez jamais par un autre sans recalibrer la voix dans la foulee.

Usage :
    python3 outils/duree.py --calibrer  <tts_manifest.json | texte.txt> <duree_voix_seule_s>
    python3 outils/duree.py --estimer   <script.json> <syllabes_par_seconde>
    python3 outils/duree.py --volume    <syllabes_par_seconde> [secondes_cible]
"""

import json
import re
import sys

VOYELLES = "aeiouyàâäéèêëîïôöûùüÿ"

# Penalite de debit des balises d'intention v3, mesuree sur EP001b.
# Seul [excited] sort du bruit : environ 13 % plus lent. Les autres balises
# se tiennent dans +/- 3 % du debit sans balise et sont donc ignorees.
PENALITE_BALISE = {"excited": 0.873}


def syllabes_mot(mot: str) -> int:
    """Compte les groupes de voyelles d'un mot, e muet final retire."""
    mot = re.sub(r"[^a-zàâäéèêëîïôöûùüÿç'-]", "", mot.lower())
    if not mot:
        return 0
    groupes = re.findall(f"[{VOYELLES}]+", mot)
    n = len(groupes)
    if n > 1 and mot.endswith("e") and not mot.endswith(("ee", "ie", "ue", "oe", "ae")):
        n -= 1
    return max(n, 1)


def syllabes(texte: str) -> int:
    """Compte les syllabes d'un texte, balises d'intention exclues."""
    texte = re.sub(r"\[[^\]]*\]", " ", texte)
    return sum(syllabes_mot(m) for m in texte.split())


def mots(texte: str) -> int:
    texte = re.sub(r"\[[^\]]*\]", " ", texte)
    return len([m for m in texte.split() if re.search(f"[{VOYELLES}]", m.lower())])


def morceaux(texte: str):
    """Decoupe un segment en morceaux (coefficient, texte).

    Une balise d'intention ne ralentit que le texte qui la SUIT, jusqu'a la
    balise suivante. Le texte place avant la premiere balise est lu au debit
    de reference (coefficient 1,0). Une balise inconnue ou neutre remet le
    coefficient a 1,0.
    """
    res = []
    coef = 1.0
    pos = 0
    for m in re.finditer(r"\[([^\]]*)\]", texte):
        if m.start() > pos:
            res.append((coef, texte[pos:m.start()]))
        coef = PENALITE_BALISE.get(m.group(1).strip().lower(), 1.0)
        pos = m.end()
    if pos < len(texte):
        res.append((coef, texte[pos:]))
    return res


def syllabes_ponderees(texte: str) -> float:
    """Syllabes d'un segment, chacune ponderee par le ralentissement qui la touche.

    duree = syllabes_ponderees / syllabes_par_seconde. La grandeur est additive :
    la somme sur plusieurs segments est exacte, sans jamais multiplier entre
    elles les penalites de segments differents.
    """
    return sum(syllabes(t) / c for c, t in morceaux(texte) if c > 0)


def coefficient(texte: str) -> float:
    """Coefficient moyen equivalent du segment (affichage uniquement)."""
    sp = syllabes_ponderees(texte)
    return syllabes(texte) / sp if sp else 1.0


def duree_s(texte: str, syll_par_s: float) -> float:
    """Duree de lecture predite, en secondes."""
    return syllabes_ponderees(texte) / syll_par_s


def _segments(chemin: str):
    """Liste des textes de segments a partir d'un manifeste ou d'un fichier texte.

    - tts_manifest.json ou script.json : un texte par segment (texte_tts, sinon vo_fr) ;
    - fichier texte : une ligne non vide = un segment.
    Chaque segment repart du debit de reference : une balise ne deborde jamais
    sur le segment suivant.
    """
    if chemin.lower().endswith(".json"):
        data = json.load(open(chemin, encoding="utf-8"))
        return [seg.get("texte_tts") or seg.get("vo_fr", "") for seg in data["segments"]]
    return [l for l in open(chemin, encoding="utf-8").read().splitlines() if l.strip()]


def _calibrer(chemin: str, duree_mesuree: float) -> None:
    segs = _segments(chemin)
    s = sum(syllabes(t) for t in segs)
    m = sum(mots(t) for t in segs)
    sp = sum(syllabes_ponderees(t) for t in segs)
    sps = sp / duree_mesuree
    print(f"segments                 : {len(segs)}")
    print(f"mots                     : {m}")
    print(f"syllabes                 : {s}  ({s/m:.2f} par mot)")
    print(f"syllabes ponderees       : {sp:.1f}  (ralentissement moyen des balises : {s/sp:.3f})")
    print(f"duree mesuree            : {duree_mesuree:.1f} s  (voix seule, silences exclus)")
    print()
    print(f"syllabes_par_seconde     : {sps:.3f}   <-- a ecrire dans config/voice.json")
    print(f"debit_mots_min (indicatif): {m/duree_mesuree*60:.1f}")
    print(f"volume 8 min 30 s        : ~{int(round(sps*510*(s/sp)/(s/m)/10))*10} mots")
    if not 3.0 <= sps <= 6.0:
        print("\n!! VALEUR HORS PLAGE PLAUSIBLE (3 a 6 syllabes/s) : verifier la duree")
        print("   fournie (voix seule ?) et le fichier d'entree avant de l'enregistrer.")


def _estimer(chemin: str, sps: float) -> None:
    data = json.load(open(chemin, encoding="utf-8"))
    total_s = total_syl = total_mots = 0.0
    print(f"{'id':6s} {'mots':>6s} {'syll':>6s} {'coef':>6s} {'duree':>8s}")
    for seg in data["segments"]:
        t = seg.get("texte_tts") or seg.get("vo_fr", "")
        d = duree_s(t, sps)
        total_s += d
        total_syl += syllabes(t)
        total_mots += mots(t)
        print(f"{seg['id']:6s} {mots(t):6d} {syllabes(t):6d} {coefficient(t):6.3f} {d:7.1f}s")
    mn, sec = divmod(int(round(total_s)), 60)
    print()
    print(f"TOTAL : {total_mots:.0f} mots, {total_syl:.0f} syllabes, {total_s:.1f} s = {mn} min {sec:02d} s")
    if total_s < 485:
        print("!! SOUS LE PLANCHER de 8 min 05 s — allonger le script avant de generer l'audio")
    elif total_s > 545:
        print("!! AU-DESSUS de la cible 8 min 20 - 8 min 45 — raccourcir")
    else:
        print("OK : dans la fenetre 8 min 20 - 8 min 45")


def _volume(sps: float, cible: float = 510.0) -> None:
    print(f"budget syllabes pour {cible:.0f} s : {sps*cible:.0f}")
    for spm in (1.55, 1.63, 1.71, 1.80):
        print(f"  a {spm:.2f} syllabes/mot -> ~{sps*cible/spm:.0f} mots")
    print("\nLe budget en SYLLABES est la contrainte. La conversion en mots n'est")
    print("qu'un ordre de grandeur pour demarrer la redaction.")


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a:
        print(__doc__)
    elif a[0] == "--calibrer":
        _calibrer(a[1], float(a[2]))
    elif a[0] == "--estimer":
        _estimer(a[1], float(a[2]))
    elif a[0] == "--volume":
        _volume(float(a[1]), float(a[2]) if len(a) > 2 else 510.0)
    else:
        print(__doc__)
