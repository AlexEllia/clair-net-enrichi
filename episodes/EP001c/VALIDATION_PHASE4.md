# EP001c — Validation de la phase 4

## Validation en vigueur : fin en quatre temps (18/10/2026)

- **Date et heure** : 18 octobre 2026, 13 h 29 (heure de Paris)
- **Mots exacts de l'utilisatrice** : « Je valide la version 1 de S29, avec une correction de la question finale, et S27, S28, S30 tels quels. »
- **Texte de S29 imposé par l'utilisatrice** : « Au Livret A, votre bascule n'arrive que la quarante-deuxième année. À cinq pour cent, la quinzième. Seul le rendement l'avance. Mais un rendement plus haut a toujours un prix. Alors la vraie question devient la vôtre : quel risque êtes-vous prêt à prendre pour gagner vingt-sept ans ? »
- **Condition posée** : poursuivre sans nouvelle validation si seuls ces points changent ; s'arrêter si un contrôle échoue ou si le calcul 42 − 15 ne donne pas 27. Calcul ajouté à `recherche.md` (§9A, T3 bis) : 27, à 50, 200 et 500 €/mois.
- **Objet validé** : S01 à S27 inchangés (texte validé le 17/10/2026 à 17 h 28, voir plus bas) ; S28 mention, S29 ouverture et S30 CTA nouveaux.
- **Empreinte des `vo_fr`, S01 à S30** : `cb607ccadab5ce466ff52654231dce47` (md5 de `json.dumps([(id, vo_fr), …], ensure_ascii=False)`, dans l'ordre des segments).
- **Empreinte des `texte_tts`, S01 à S30** : `d26d4e085e7ccf33d46f02293421f977` (même méthode). Balises : aucune pour S28 et S30, `[curious]` en ouverture de S29.

Les scripts de génération vérifient, avant chaque appel à l'API, que ce fichier existe, que `STOP` est absent et que les textes prononcés ont exactement ces deux empreintes. Toute modification d'un `vo_fr` ou d'un `texte_tts` annule cette validation.

## Historique — validation du 17/10/2026

- **Date et heure** : 17 octobre 2026, 17 h 28 (heure de Paris)
- **Mots exacts de l'utilisatrice** : « Je valide cette version corrigée. »
- **Version validée** : `script.json` md5 `4015ede3115242d799accc71b1bb5303` ; textes prononcés S01–S28 : `vo_fr` `0ee694e1ddac0a6b6ead92e449d12d7b`, `texte_tts` `0363d77d8d50648a8c418aca7bb7bdc9`. S01 à S27 de cette version sont repris à l'identique.
