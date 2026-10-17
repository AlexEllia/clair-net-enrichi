# EP001c — Validation de la phase 4

- **Date et heure** : 17 octobre 2026, 17 h 28 (heure de Paris)
- **Mots exacts de l'utilisatrice** : « Je valide cette version corrigée. »
- **Objet validé** : la version corrigée après le point de contrôle des trois segments (coupe d'environ 9 s dans S15, S24, S25, S26 et S28, présentée le 17/10/2026 à 17 h 26), le reste du script étant inchangé par rapport à la version validée à 17 h 22.
- **Version validée** : `episodes/EP001c/script.json`, md5 `4015ede3115242d799accc71b1bb5303`, relu sur le disque le 17/10/2026 avant écriture de ce fichier.
- **Recherche associée** : `episodes/EP001c/recherche.md`, md5 `6adefc568ceb018756450c5b34f976ad`.
- **Catalogue** : `video/CATALOGUE.md`, md5 `0a2aef70fcd31aaf2f245a0cc49a5a00` (égal à `meta.catalogue_md5`).
- **Calibrage** : 3,976 syllabes/s (EP001b), voix Victoria - Content Creator.
- **Audio conservé** : S01, S02 et S03, générés juste après la validation de 17 h 22, sous celle-ci ; leur texte est identique dans la version validée ici.

Toute modification de `script.json` après cette validation l'annule : ce fichier doit alors être supprimé et le point d'arrêt de la phase 4 repris. Les scripts de génération vérifient, avant chaque appel à l'API, que ce fichier existe, que `STOP` est absent et que l'empreinte de `script.json` est toujours celle ci-dessus.
