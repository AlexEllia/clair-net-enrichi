# -*- coding: utf-8 -*-
"""Musique de fin : un fond sonore sous la fin du cta et pendant la
prolongation silencieuse de l'ecran de fin. Regle de chaine, pas d'episode :
les parametres sont dans config/charte.json (cle "musique_fin").

Enveloppe, en temps de l'episode (fv : fin de la voix, fe : fin de la video,
c'est-a-dire de sa derniere image) :
- a fv - avance_sur_fin_voix_s, la musique entre en fondu (fondu_entree_s)
  jusqu'au niveau bas : sous_voix_db sous la sonie de la voix du plan
  ecran_fin, pour ne jamais couvrir « Clair net enrichi » ni « abonnez-vous » ;
- de fv a fv + montee_s, elle remonte (rampe en dB) jusqu'a niveau_fin_lufs
  et s'y maintient pendant la prolongation silencieuse ;
- elle sort en fondu (fondu_sortie_s), nulle sur la derniere image.
Chaque gain est calcule sur la sonie EBU R128 du passage du morceau qui
tombe dans sa phase (une intro douce et un refrain n'ont pas le meme
niveau). Le silence qui ouvre le morceau est saute. Le morceau ne boucle
jamais : s'il est plus court que la plage, il s'arrete et on le signale.

Puis le mastering de chaine (mastering.py, cle "mastering") : gain global
vers la sonie cible et limiteur true-peak. Le niveau de fin s'entend dans la
video livree : il est corrige du gain global. L'ecart sous la voix est
mesure apres mastering, voix et musique chacune seule sous la meme courbe
de gain ; sous sous_voix_db, rien n'est produit.

Avant fv - avance_sur_fin_voix_s, la piste rendue est la voix multipliee par
le gain global (et par le limiteur, la ou il agit) : la musique s'ajoute,
rien d'autre ne change.

    python video/musique_fin.py EP001c --extrait 557   (extrait de controle)
    python video/musique_fin.py EP001c --sortie video/EP001c_musique.mp4

L'outil autonome reprend video/voix.wav et le flux image de
video/<ep>.mp4 (copie, sans nouveau rendu) ; build.py appelle piste().
"""
import argparse
import json
import re
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
CHARTE = ROOT / "config" / "charte.json"


def charte(path=CHARTE):
    return json.loads(Path(path).read_text(encoding="utf-8")).get("musique_fin")


def lire_wav(path):
    with wave.open(str(path)) as w:
        if w.getnchannels() != 1 or w.getsampwidth() != 2:
            sys.exit(f"{path} : mono 16 bits attendu")
        return np.frombuffer(w.readframes(w.getnframes()), np.int16), w.getframerate()


def ecrire_wav(path, x, sr):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(x.astype("<i2").tobytes())


def decoder(path, sr):
    """Le morceau entier, mono, en flottants, a la frequence de la voix."""
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(sr),
                        "-f", "f32le", "-"], capture_output=True, check=True)
    return np.frombuffer(r.stdout, np.float32).astype(np.float64)


def sonie(x, sr):
    """(sonie integree LUFS, crete vraie dBTP) d'un signal flottant mono."""
    r = subprocess.run(["ffmpeg", "-nostats", "-hide_banner", "-f", "f32le", "-ar", str(sr),
                        "-ac", "1", "-i", "-", "-af", "ebur128=peak=true", "-f", "null", "-"],
                       input=np.asarray(x, np.float32).tobytes(), capture_output=True)
    resume = r.stderr.decode("utf-8", "replace")
    resume = resume[resume.rfind("Summary:"):]
    i = re.search(r"I:\s+(-?[\d.]+|-inf) LUFS", resume).group(1)
    p = re.search(r"Peak:\s+(-?[\d.]+|-inf) dBFS", resume).group(1)
    return float(i), float(p)


def piste(voix, sr, fin_voix_s, fin_video_s, ref_voix_s, c=None, racine=ROOT,
          decalage_fin_db=0.0, decalage_bas_db=0.0):
    """Mixe la musique de fin sous `voix` (int16 mono).

    fin_voix_s  : fin de la voix (fin_voix_s du plan ecran_fin, timeline) ;
    fin_video_s : fin de la derniere image ;
    ref_voix_s  : (debut, fin) de la voix dont la musique doit rester sous
                  sous_voix_db (le plan ecran_fin) ;
    decalage_fin_db : correction du niveau de fin, pour qu'il soit atteint
                  apres le gain global du mastering ;
    decalage_bas_db : correction du niveau bas, pour que l'ecart sous la voix
                  tienne apres le limiteur (qui rabote les cretes de la voix).
    Renvoie (mix flottant, musique seule sur la plage, debut de la plage en
    echantillons, rapport)."""
    c = c or charte()
    m = decoder(racine / c["fichier"], sr)
    d0 = int(round(c.get("debut_morceau_s", 0.0) * sr))
    if c.get("sauter_silence_initial", True):
        seuil = 10 ** (c.get("seuil_silence_dbfs", -50.0) / 20)
        fort = np.flatnonzero(np.abs(m[d0:]) > seuil)
        d0 += int(fort[0]) if len(fort) else 0
    m = m[d0:]

    def i(t):
        return int(round(t * sr))

    t0 = fin_voix_s - c["avance_sur_fin_voix_s"]
    a, fv, fe = i(t0), i(fin_voix_s), i(fin_video_s)
    fi, mo, fo = i(c["fondu_entree_s"]), i(c["montee_s"]), i(c["fondu_sortie_s"])
    if not (a + fi <= fv and fv + mo <= fe - fo):
        sys.exit("musique_fin : la plage est trop courte pour les fondus de la charte")
    plage = fe - a
    rapport = {"debut_s": round(t0, 3), "fin_voix_s": round(fin_voix_s, 3),
               "fin_video_s": round(fin_video_s, 3),
               "morceau_saute_s": round(d0 / sr, 3), "plage_s": round(plage / sr, 3),
               "morceau_restant_s": round(len(m) / sr, 3)}
    if len(m) < plage:
        rapport["ATTENTION"] = (f"morceau trop court : {len(m) / sr:.2f} s pour une plage de "
                                f"{plage / sr:.2f} s ; il s'arrete, sans boucle")
        print("ATTENTION musique_fin :", rapport["ATTENTION"])
    m = np.concatenate([m[:plage], np.zeros(max(0, plage - len(m)))])

    # Gains, sur la sonie du passage de chaque phase (avant enveloppe).
    v = voix.astype(np.float64) / 32768
    l_voix, _ = sonie(v[i(ref_voix_s[0]):i(ref_voix_s[1])], sr)
    # Niveau bas : calcule sur le plateau (apres le fondu d'entree), la ou
    # le gain bas s'applique en entier ; l'intro qui monte le rend plus fort
    # que la moyenne des secondes d'entree.
    l_bas_brut, _ = sonie(m[fi:fv - a], sr)
    l_haut_brut, _ = sonie(m[fv + mo - a:fe - fo - a], sr)
    cible_bas = l_voix - c["sous_voix_db"]
    g_bas = cible_bas + decalage_bas_db - l_bas_brut
    g_haut = c["niveau_fin_lufs"] + decalage_fin_db - l_haut_brut

    # Enveloppe en dB sur la plage, puis fondus en amplitude.
    db = np.empty(plage)
    db[:fv - a] = g_bas
    db[fv - a:fv + mo - a] = np.linspace(g_bas, g_haut, mo, endpoint=False)
    db[fv + mo - a:] = g_haut
    env = 10 ** (db / 20)
    env[:fi] *= np.linspace(0.0, 1.0, fi, endpoint=False)
    env[fe - fo - a:] *= np.linspace(1.0, 0.0, fo)          # nulle sur la derniere
    musique = m * env

    sortie = v.copy()
    if len(sortie) < fe:
        sortie = np.concatenate([sortie, np.zeros(fe - len(sortie))])
    sortie[a:fe] += musique
    rapport.update({"gain_bas_db": round(g_bas, 2), "gain_haut_db": round(g_haut, 2),
                    "_phases": {"voix": (i(ref_voix_s[0]), i(ref_voix_s[1])),
                                "sous_voix": (a + fi, fv), "fin": (fv + mo, fe - fo)}})
    return sortie, musique, a, rapport


def mesurer_fin(voix_f, musique, a, gain, sr, phases):
    """Sonie de la voix et de la musique, chacune seule, apres la courbe de
    gain `gain` (scalaire ou par echantillon) : l'ecart est celui du mix."""
    g = np.broadcast_to(gain, voix_f.shape) if np.ndim(gain) == 0 else gain
    m = np.zeros(len(g))
    m[a:a + len(musique)] = musique
    v0, v1 = phases["voix"]
    b0, b1 = phases["sous_voix"]
    h0, h1 = phases["fin"]
    l_voix, _ = sonie(voix_f[v0:v1] * g[v0:v1], sr)
    l_bas, _ = sonie(m[b0:b1] * g[b0:b1], sr)
    l_haut, _ = sonie(m[h0:h1] * g[h0:h1], sr)
    return {"voix_reference_lufs": l_voix, "musique_sous_voix_lufs": l_bas,
            "ecart_sous_voix_db": round(l_voix - l_bas, 1), "musique_fin_lufs": l_haut}


def bande_finale(voix, sr, fin_voix_s, fin_video_s, ref_voix_s, racine=ROOT):
    """Musique de fin puis mastering, selon config/charte.json. Sans plan
    ecran_fin (fin_voix_s None), le mastering seul.
    Renvoie (piste int16, rapport, courbe de gain)."""
    import mastering
    ch = json.loads(CHARTE.read_text(encoding="utf-8"))
    cm = ch.get("musique_fin") if fin_voix_s is not None else None
    cmast = ch.get("mastering")
    v = voix.astype(np.float64) / 32768
    rapport = {}
    if cm:
        decalage, bas = 0.0, 0.0
        for _ in range(6):
            mix, musique, a, rm = piste(voix, sr, fin_voix_s, fin_video_s, ref_voix_s, cm,
                                        racine, decalage, bas)
            phases = rm["_phases"]
            if not cmast:
                break
            z, gain, rmast = mastering.masteriser(mix, sr, cmast)
            # Le niveau de fin s'entend apres le gain global : on le corrige
            # d'autant, ce qui ne change presque pas la sonie de l'episode.
            # L'ecart sous la voix se juge dans le mix livre : si le limiteur
            # a baisse la voix, la musique descend d'autant (+0,1 dB de marge).
            ecart = mesurer_fin(v, musique, a, gain, sr, phases)["ecart_sous_voix_db"]
            manque = cm["sous_voix_db"] - ecart
            stable = abs(decalage + rmast["gain_db"]) <= 0.05
            if stable and manque <= 0:
                break
            decalage = -rmast["gain_db"]
            if manque > 0:
                bas -= manque + 0.1
        rm.pop("_phases")
        rm["correction_bas_db"] = round(bas, 2)
        rm["correction_fin_db"] = round(decalage, 2)
        rapport["musique_fin"] = rm
        rapport["musique_fin"]["avant_mastering"] = mesurer_fin(v, musique, a, 1.0, sr, phases)
    else:
        mix = v
    if cmast:
        if not cm:
            z, gain, rmast = mastering.masteriser(mix, sr, cmast)
        rapport["mastering"] = rmast
        if cm:
            rapport["musique_fin"]["apres_mastering"] = mesurer_fin(v, musique, a, gain, sr,
                                                                     phases)
    else:
        z, gain = mix, 1.0
    if cm:
        fin = rapport["musique_fin"].get("apres_mastering",
                                         rapport["musique_fin"]["avant_mastering"])
        if fin["ecart_sous_voix_db"] < cm["sous_voix_db"] - 0.05:
            sys.exit(f"musique_fin : musique a {fin['ecart_sous_voix_db']} dB sous la voix, "
                     f"la charte en demande {cm['sous_voix_db']}")
    rapport["echantillons_ecretes"] = int((np.abs(z) * 32768 > 32767).sum())
    out = np.clip(np.round(z * 32768), -32768, 32767).astype(np.int16)
    return out, rapport, gain


def _timeline(ep_dir):
    tl = json.loads((ep_dir / "build" / "timeline.json").read_text(encoding="utf-8"))
    types = {s["id"]: s.get("type_visuel") for s in
             json.loads((ep_dir / "script.json").read_text(encoding="utf-8"))["segments"]}
    fin = [r for r in tl["segments"] if types.get(r["id"]) == "ecran_fin"]
    if len(fin) != 1:
        sys.exit("script.json : il faut exactement un plan ecran_fin")
    return tl, fin[0]


def duree_image(video):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "stream=duration", "-of", "csv=p=0", str(video)],
                       capture_output=True, text=True, check=True)
    return float(r.stdout.strip())


def main():
    ap = argparse.ArgumentParser(description="Musique de fin (charte de chaine)")
    ap.add_argument("ep", help="episode, par exemple EP001c")
    ap.add_argument("--extrait", type=float, metavar="DEBUT_S",
                    help="ne rend que l'extrait de DEBUT_S a la fin (controle d'ecoute)")
    ap.add_argument("--sortie", type=Path, help="video produite (defaut : video/<ep>_musique.mp4)")
    a = ap.parse_args()
    ep_dir = ROOT / "episodes" / a.ep
    vdir = ep_dir / "video"
    source = vdir / f"{a.ep}.mp4"
    voix, sr = lire_wav(vdir / "voix.wav")
    tl, fin = _timeline(ep_dir)
    fe = duree_image(source)
    out, rapport, _ = bande_finale(voix, sr, fin["fin_voix_s"], fe,
                                   (fin["debut_s"], fin["fin_voix_s"]))
    bande = vdir / "_bande_musique.wav"
    ecrire_wav(bande, out, sr)

    if a.extrait is not None:
        dest = a.sortie or vdir / f"{a.ep}_extrait_musique.mp4"
        # Extrait d'ecoute : image reencodee pour couper hors image cle.
        cmd = ["ffmpeg", "-y", "-v", "error", "-ss", f"{a.extrait:.3f}", "-i", str(source),
               "-ss", f"{a.extrait:.3f}", "-i", str(bande), "-map", "0:v", "-map", "1:a",
               "-c:v", "libx264", "-crf", "18", "-preset", "medium",
               "-c:a", "aac", "-b:a", "192k", "-ar", str(sr), "-shortest", str(dest)]
    else:
        dest = a.sortie or vdir / f"{a.ep}_musique.mp4"
        cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(source), "-i", str(bande),
               "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
               "-ar", str(sr), "-map_chapters", "0", "-movflags", "+faststart", "-shortest",
               str(dest)]
    subprocess.run(cmd, check=True)
    rapport["video"] = str(dest)
    rapport["bande"] = str(bande)
    print(json.dumps(rapport, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
