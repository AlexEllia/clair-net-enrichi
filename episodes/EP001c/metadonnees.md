# EP001c — Métadonnées YouTube

## Titre

- **Retenu** : Intérêts composés : l'année où tout bascule
- Alternatives :
  - 50 € ou 500 € par mois : la même année de bascule
  - 2 400 € versés, 14 000 € d'intérêts : ce que font les années
  - L'année où vos intérêts dépassent vos versements

## Texte de miniature

L'année de bascule

## Miniatures

Variantes pour « Tester et comparer » de YouTube Studio, lues par `make miniature EP=EP001c`. Syntaxe du texte : ` / ` change de ligne, `==…==` met la ligne dans un bloc, `{…}` écrit en ambre (ce que le capital verse), `[…]` en bleu (ce que vous versez). Données : convention 9A de recherche.md.

### A — chiffre

- Chiffre : 27
- Texte : ans / ==plus tôt==
- Barres : Livret A = bascule 1,70 % ; 5 % = bascule 5 %

### B — contraste

- Texte : En quelle année / ==tout bascule ?==
- Courbes : versé et capital, 200 €/mois, 5 %, 40 ans

### C — bascule

- Texte : Quand tes {intérêts} / ==dépassent== / tes [versements]
- Courbes : intérêts et versements de l'année, 200 €/mois, 5 %, 28 ans

## Description

Deux mille quatre cents euros versés dans l'année, quatorze mille euros d'intérêts la même année. Hypothèse de calcul : 200 € par mois, 5 % par an, 40 ans. Presque six fois plus d'intérêts que de versements, et cet écart ne doit rien au montant que vous versez chaque mois.

Au programme : la capitalisation expliquée avec un Livret A, les chiffres de l'AMF sur l'effet de la durée, l'année exacte où les intérêts d'une année dépassent les versements de cette année-là, et pourquoi elle est la même à 50 € ou à 500 € par mois. Puis quatre angles morts, tous sourcés : la durée réelle des contrats, la dispersion des performances, la capacité d'épargne des ménages et le crédit à la consommation.

Niveau : débutant. Aucune notion préalable nécessaire.

Chapitres
00:00 2 400 € versés, 14 000 € d'intérêts : la même année
00:19 Pourquoi la première année déçoit
00:54 Capitalisation et intérêts composés, sans formule
03:31 La bascule, et pourquoi le montant n'y change rien
06:11 Les quatre angles morts du calcul
08:28 La réponse : ce que font les années
09:02 Quel risque pour gagner 27 ans ?

Sources principales : AMF (décembre 2021), Banque de France (2023, 2026), Euronext (31/03/2026), ACPR (30/06/2026), France Assureurs (27/01/2026), INSEE (2024), Service Public.

Ce contenu est informatif et pédagogique. Il ne constitue ni un conseil en investissement ni une recommandation personnalisée. Les performances passées ne sont pas un indicateur fiable des résultats futurs. Les simulations sont des hypothèses de calcul.

Clair net enrichi

## Chapitres (timecodes réels, respirations comprises)

00:00 2 400 € versés, 14 000 € d'intérêts : la même année
00:19 Pourquoi la première année déçoit
00:54 Capitalisation et intérêts composés, sans formule
03:31 La bascule, et pourquoi le montant n'y change rien
06:11 Les quatre angles morts du calcul
08:28 La réponse : ce que font les années
09:02 Quel risque pour gagner 27 ans ?

## Mid-rolls

| Après | Timecode |
|---|---|
| S10 (fin de l'acte 1) | 03:31 |
| S18 (fin de l'acte 2) | 06:11 |
| S25 (fin de l'acte 3) | 08:28 |

Chapitres et mid-rolls repris le 17/10/2026 de `build/chapitres.txt` et `build/timeline.json`, produits par le rendu de Claude Code après la régénération de la voix par blocs : ce sont eux qui font foi.

## Mention légale

Ce contenu est informatif et pédagogique. Il ne constitue ni un conseil en investissement ni une recommandation personnalisée. Les performances passées ne sont pas un indicateur fiable des résultats futurs. Les simulations sont des hypothèses de calcul.

## Tags

intérêts composés, capitalisation, épargne, finances personnelles, débutant, livret A, assurance-vie, fonds en euros, AMF, épargne long terme, année de bascule, Clair net enrichi

## Durée et calibrage

Audio actuel : voix régénérée le 17/10/2026 en trois blocs (B1 S01–S10, B2 S11–S18, B3 S19–S28), découpée en segments au milieu des pauses naturelles. L'audio précédent, généré segment par segment, est archivé dans `audio_segments_v1/`.

| | Valeur |
|---|---|
| Durée estimée (`outils/duree.py` sur `tts_manifest.json`, 3,940 syll/s) | 510,5 s (8 min 30 s) |
| Durée réelle de la voix, pauses naturelles comprises (somme des `duree_audio_s`) | **557,12 s (9 min 17 s)** |
| Écart | **+9,1 %** |
| Silences ajoutés aux deux jonctions de blocs (pause effective portée à 1,4 s) | 1,14 s après S10, 1,02 s après S18 |
| Durée totale de l'épisode (`build/timeline.json`) | **559,28 s (9 min 19 s)**, au-dessus du plancher de 8 min 05 s |
| Fin en quatre temps (18/10/2026) : S28 mention 7,23 s, S29 ouverture 17,31 s, S30 CTA 9,78 s, bloc B4 ; jonction S27 → S28 portée à 1,4 s (0,81 s ajoutée) | **576,93 s (9 min 37 s)** au total, mid-rolls inchangés (03:31, 06:11, 08:28) |
| Nouveau `syllabes_par_seconde` (méthode A sur EP001c, `mode_calibrage` bloc) | **3,610** (précédent 3,940, écart −8,4 %) |

Point de contrôle après le premier bloc : B1 à +9,9 % (210,56 s pour 191,56 s estimés), projection à environ 9 min 21 s. Écart supérieur à 5 % mais projection au-dessus du plancher : génération poursuivie, calibrage refait en fin d'épisode. Une partie de l'écart vient des pauses naturelles entre les phrases, absentes du calibrage précédent, mesuré segment par segment sur la voix seule ; le reste, d'une prise globalement plus lente. Volume indicatif pour 8 min 30 s au nouveau débit : environ 1 270 mots.

## Recalage des révélations

Recalage du 17/10/2026 sur l'alignement réel de la génération par blocs (`audio/alignments/`, re-basé sur le début de chaque segment). Tous les déclencheurs, révélations et overlays, ont été retrouvés. Plus grand écart entre estimation et réel : 4,54 s (S20, source en bas d'écran) ; sur une révélation : 4,27 s (S20, `band_4`). 130 entrées sur 210 dérivent de plus de 0,5 s : les estimations ont été faites à 3,976 ou 3,940 syll/s, sans les pauses de ponctuation, sur une voix plus lente (3,610 syll/s en mode bloc) ; celles de S02 et S12 sont les valeurs des briefs pilotes, calées sur l'ancien audio. Sur les temps réels, la première valeur de chaque plan tombe entre 0,77 s (S11) et 9,47 s (S02). Cinq plans la donnent après 4,5 s (S02, S19, S21, S24, S26), parce que leur première phrase ne porte pas de chiffre et que le texte validé n'a pas été modifié : la jauge monte pendant l'attente. Au calendrier, un seul intervalle entre révélations dépasse 4 s : 5,3 s dans S02, entre la mise en avant et la `suite`, comme dans le pilote validé (mesuré à 3,0 s en pixels). Overlays compris, aucun plan ne reste figé plus de 4 s.

## Crédits ElevenLabs consommés pour l'EP001c

Caractères envoyés à l'API, balises comprises, relevés dans les fichiers de chaque lot.

| Date | Lot | Requêtes | Caractères envoyés | Statut |
|---|---|---|---|---|
| 27/09/2026 | Génération segment par segment, avant le contrôle de recalcul (`audio_segments_v1/_obsolete_avant_6b/`) | 19 segments | 6 092 | Perdu : jeté après correction des chiffres |
| 17/10/2026 | Génération segment par segment de la version validée (`audio_segments_v1/`, `tts_manifest_segments_v1.json`) | 28 segments | 8 564 | Remplacé : archivé, absent de l'épisode final |
| 17/10/2026 | Test de génération par bloc, S18 à S26 (`test_voix_bloc/`) | 1 bloc | 2 670 | Test, absent de l'épisode final |
| 17/10/2026 | Génération finale par blocs (`audio/`, `tts_manifest.json`) | 3 blocs | 8 589 | **Dans l'épisode final**, sauf l'ancien S28 (296 caractères, fin de B3), remplacé le 18/10 |
| 18/10/2026 | Nouvelle fin, S28 à S30 (`audio/blocs/B4`) | 1 bloc | 581 | **Dans l'épisode final** |

| | Caractères |
|---|---|
| Envoyés pour l'audio final (B1 à B4) | 9 170, dont 296 de l'ancien S28 non utilisés au montage |
| Perdus, remplacés ou consommés par des tests (hors B1 à B4) | 17 326 |
| **Total consommé pour l'EP001c** | **26 496** |
