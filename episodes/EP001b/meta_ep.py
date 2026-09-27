# -*- coding: utf-8 -*-
"""Phase 6 — EP001b : metadonnees.md, timecodes calculés sur audio/durations.json (respirations comprises)."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
sc = json.load(open(os.path.join(HERE, "script.json"), encoding="utf-8")); m = sc["meta"]; segs = sc["segments"]
d = json.load(open(os.path.join(HERE, "audio", "durations.json"), encoding="utf-8"))
TIT = {"hook": "2 400 € versés, 14 000 € d'intérêts : la même année", "tension": "Pourquoi la première année déçoit",
       "acte1": "Comment la capitalisation fabrique la puissance", "acte2": "La bascule, et pourquoi le montant n'y change rien",
       "acte3": "Les quatre limites, sans les cacher", "payoff": "La réponse : la quinzième année",
       "cta": "Mention légale et rendez-vous"}
fmt = lambda t: "%02d:%02d" % (int(t) // 60, int(t) % 60)
t = 0; chap = []; seen = set(); mids = []
for s in segs:
    if s["role"] not in seen: seen.add(s["role"]); chap.append(f"{fmt(t)} {TIT[s['role']]}")
    t += d[s["id"]]["duree_totale_s"]
    if s["midroll_apres"]: mids.append((s["id"], fmt(t)))
voix = sum(d[s["id"]]["duree_audio_s"] for s in segs)
legal = ("Ce contenu est informatif et pédagogique. Il ne constitue ni un conseil en investissement "
         "ni une recommandation personnalisée. Les performances passées ne sont pas un indicateur fiable des résultats futurs.")
desc = ("Deux mille quatre cents euros versés dans l'année. Quatorze mille euros d'intérêts la même année. "
        "Hypothèse de calcul : 200 € par mois, 5 % par an, 40 ans. Mais le vrai moment clé arrive bien avant : "
        "l'année où vos intérêts dépassent vos versements, pour la première fois. Elle a un numéro, et il est le même "
        "que vous versiez cinquante euros par mois ou cinq cents.\n\n"
        "Au programme : le mécanisme officiel de la capitalisation, les chiffres de l'AMF sur l'effet de la durée, "
        "l'année exacte de la bascule, et pourquoi le montant versé ne la déplace pas. Puis quatre limites, toutes sourcées : "
        "la durée réelle des contrats, la dispersion des performances, la capacité d'épargne des ménages, et le crédit à la consommation.\n\n"
        "Niveau : débutant. Aucune notion préalable nécessaire.\n\n"
        "Chapitres\n" + "\n".join(chap) + "\n\n"
        "Sources principales : AMF (décembre 2021), Euronext (CAC 40, 31/03/2026), ACPR (30/06/2026), INSEE, "
        "Banque de France (taux d'usure 2026-T3), France Assureurs (27/01/2026), Service Public (Livret A).\n\n"
        + legal + "\n\nClair net enrichi")
md = (f"# EP001b — Métadonnées YouTube\n\n"
      f"Épisode : EP001b · Niveau : débutant · Voix : Victoria - Content Creator (eleven_v3)\n"
      f"Script : {m['mots_total']} mots · Durée voix seule : {voix:.1f} s ({fmt(voix)}) · avec respirations : {t:.1f} s ({fmt(t)})\n\n"
      f"## Titre retenu\n{m['titre_principal']}\n\n## Titres alternatifs\n" + "\n".join(f"- {x}" for x in m["titres_alternatifs"]) +
      f"\n\n## Texte de miniature\n{m['texte_miniature']}\n\n## Description YouTube\n```\n{desc}\n```\n\n"
      "## Chapitres (timecodes réels, respirations comprises)\n" + "\n".join(f"- {c}" for c in chap) +
      "\n\n## Mid-rolls (timecodes réels)\n" + "\n".join(f"- {tc} — après {sid}" for sid, tc in mids) +
      f"\n\n## Mention légale\n{legal}\n\n## Tags\n{', '.join(m['tags'])}\n")
open(os.path.join(HERE, "metadonnees.md"), "w", encoding="utf-8").write(md)
print(md)
