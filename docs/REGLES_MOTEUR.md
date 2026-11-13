# Règles du moteur et règles git

Copie versionnée des règles décidées avec Alexandre, pour qu'elles survivent à la
mémoire de session de Claude et à la machine. Le détail fait foi dans
`video/CATALOGUE.md` et dans le code ; ici, l'essentiel et le pourquoi.

- Rédigé le 19/10/2026, état du dépôt : `683acf4`.
- Règles du moteur décidées du 17 au 19/10/2026.

## Règles du moteur

- **Bars, règle v3-phrase** (`BARS_RULE`, components.py) : la barre 1 monte dès le
  cadre posé ; chaque barre suivante ne monte qu'au début de la phrase qui contient
  son propre déclencheur (alignement réel, `briefs.with_voice`) et atteint sa hauteur
  sur ce mot ; 6 s au plus, sous 0,6 s elle surgit.
  *Pourquoi* : l'anticipation (« v2-anticipation », archivée) faisait monter la
  barre 3 pendant que la voix parlait de la 2 (EP001c, 5:32). La variante « v3 »
  (fin de la phrase précédente) a été essayée et rejetée : avec le plafond de 6 s
  elle ne changeait rien.
  Commits : `e78d1b0`, `bbab096` (catalogue).
- **Mise en avant au milieu de l'intervalle figé** : si l'écran resterait figé plus
  de 4 s entre l'arrivée de la barre g (étiquette + fondu de sa source) et la
  croissance de g+1, la barre g est encadrée au milieu de l'attente, calée sur le
  début du mot le plus proche, et revient à la normale quand g+1 monte. Jamais une
  barre pas encore montée, jamais avant la barre 1 ; en empilées, toute la colonne.
  Alexandre a **refusé la dérogation R6** : corriger la règle plutôt que déroger.
  Commits : `e78d1b0`, `a8c490b` (le cadre n'apparaît plus avant son heure).
- **Source par barre** : overlay ancre `source_g`, sous la catégorie, fondu 0,4 s à
  la fin de la croissance, une fois par source ; remplace la source globale `bas`.
  Commit : `e78d1b0`.
- **Plans de chaîne** `mention` et `ecran_fin` (plans_chaine.py) : sans
  manim_brief ni overlay_texte (refusés au check et au build) ; écran de fin
  prolongé en silence jusqu'à 20 s et animé jusqu'au bout ; zones réservées vidéo
  830×467 centre (1340, 540), abonnement Ø 300 centre (480, 600) ; gabarit
  `build/ecran_fin_zones.png`. Le bouton est un seul objet continu ; son
  enfoncement 0,9 s après « abonnez-vous » est voulu.
  Commits : `300c412`, `98299d2` (catalogue), `3e40004` (bouton continu).
- **Chapitres** (timeline.py) : mention, ouverture et cta forment un seul chapitre ;
  titres lus dans `metadonnees.md` ; le build bloque si le nombre de titres diffère
  ou si un chapitre dure moins de 10 s.
  Commits : `c8ca8dd`, `7ccd316` (catalogue).
- **R6 au moment de figer** (`non_regression.py --valider / --nouvelle-version`) :
  refus au-delà de 4 s figées au calendrier, sauf `--derogation-r6 "motif"` écrite
  dans la version. Chaque version de référence enregistre ses règles
  (`regle_cadre`, `regle_comparaison`, `regle_barres`).
  Commits : `a23c1d9` (R6 mesurée en pixels), `e78d1b0` (`--derogation-r6`).
- **Contrôle bloquant de `make check`** (11/11/2026, `check_nouveaute` dans
  build.py) : refus de tout plan, quel que soit son `type_visuel`, où plus de 4 s
  passent sans rien de nouveau à l'écran, de la première image à la fin de la voix.
  Jugé au calendrier du moteur, sans rendu ; ce qui s'anime hors de l'image ne
  compte pas (quatrième encart `centre`) ; l'argent qui circule compte ; l'écran
  de fin n'est jugé qu'en pixels. Le build, lui, ne refuse pas : il mesure en
  pixels et avertit. *Pourquoi* : l'EP004 rendu le 11/11 comptait 15 plages figées
  (135 s sur 503 s), dont 24 s sur un plan de typographie à 13 encarts.
- **Encarts « centre », règle `v2-zone`** (12/11/2026, `ENCART_RULE` dans
  components.py, placement dans scenes.add_overlays) : un encart ne recouvre jamais
  le graphique. Dès qu'un plan en porte un, la colonne de droite lui est réservée
  (centre x = 4,75, largeur 4,2) et le graphique s'arrête à x = 2,35 : aire de tracé
  de LineChart, Bars et Areas, colonnes de Comparaison, légende, nœuds de Flux
  (resserrés seulement si l'un déborde). Trois emplacements ; le quatrième encart
  prend la place du plus ancien, qui sort en fondu (0,35 s). Un plan sans encart ne
  change pas : les quatre plans validés à l'écran sont identiques au pixel près.
  `v1` (encarts à x = 4,15 par-dessus le graphique, empilés sans limite) est
  archivée. *Pourquoi* : sur l'EP004, les encarts cachaient la dernière jauge ou la
  dernière barre et sa valeur sur 11 plans, et le quatrième sortait de l'image.
- **Libellés de Flux** (12/11/2026) : chaque nom de nœud ou de lien est posé là où
  il ne touche rien (place habituelle, puis autres côtés, puis deux lignes), sans
  changer la taille des lettres. *Pourquoi* : EP004 S13, deux noms superposés.
- **Contrôle bloquant de placement** (12/11/2026, `check_placement` dans build.py) :
  `make check` refuse tout encart ou libellé qui recouvre un élément, un autre
  encart ou libellé, ou sort de l'image ; jugé sans rendu, sur les boîtes
  englobantes. Sous la règle `v1`, il refuse 23 plans de l'EP004.
- **Ancrage des étiquettes de valeur, règle `v2-ancre`** (12/11/2026, `LABEL_RULE`
  dans components.py) : une étiquette reste collée à son point, de la couleur de sa
  série ; elle n'a de places que tout autour de lui, et le point le plus proche
  d'elle est toujours le sien (ni un autre point, ni la courbe d'une autre série, à
  0,05 près). Sans place libre : trait de rappel court, jamais au-delà de
  `ANCRE_MAX` = 0,60 unité. `make check` le refuse sinon (toutes familles).
  *Pourquoi* : EP004 S04, « 91,7 % » (courbe bleue) se lisait sur la courbe jaune
  et « 100 % » sous l'avant-dernier point — une étiquette lue près d'un autre point
  est un chiffre faux, même si chaque point était tracé à la bonne hauteur
  (vérifié : 0,00 d'écart). `v1` (trois crans d'éloignement sans trait) archivée.
- **LineChart : étiquettes des seuls points nommés** (12/11/2026) : dès qu'un
  `series_k_point_j` est nommé, les autres points ne servent qu'à tracer. Un plan
  sans point nommé (EP001b S09, validé) les marque tous, inchangé, dans la limite
  de 6 étiquettes (`ETIQUETTES_MAX`) : au-delà, `make check` refuse. *Pourquoi* :
  EP004 S10, 40 valeurs superposées.
- **Accolade d'écart** (12/11/2026) : hauteur réelle toujours ; sous 0,35 unité,
  pattes allongées, trait affirmé et avertissement au build.
- **Mention exclue de R6** (12/11/2026, décision d'Alexandre) : ni `make check` ni
  la carte de densité ne comptent le plan `mention` (`densite.EXCLUS_R6`) ; le
  build écrit sa mesure à part, « hors R6 ». La dérive reste à 2 %.
- **Typographie : rotation à trois, emplacements desserrés, marge minimale**
  (12 et 13/11/2026, scenes.add_overlays) : en `typo_cinetique`, trois textes
  `centre` au plus à l'écran, le quatrième remplace le plus ancien, qui sort en
  fondu (0,35 s). Emplacements `TYPO_Y` = 1,66 / −0,39 / −2,44, espacés de 2,05
  et centrés entre le titre et la source (avant : 0,95 / −0,95 / −2,85) ; deux
  textes : ±1,025 ; hauteur d'un texte plafonnée à 1,90. Le contrôle de
  placement s'applique à la typographie, avec une marge minimale de 0,15 unité
  (`MARGE_ENCART`, 20 px en 1080p) entre un texte et un autre texte, un
  libellé ou le bord. Depuis le 13/11/2026 (décision d'Alexandre), la marge
  vaut pour **tous les plans** : encart latéral contre élément du graphique,
  libellé, autre encart ou bord. Refus pour un script écrit contre le
  catalogue actuel (`meta.catalogue_md5`), simple remarque pour un script
  antérieur : EP004 S09 et S20 (encart à moins de 0,15 d'un nom de nœud) sont
  signalés, à corriger quand l'épisode sera refait. `fond_anime` et `broll` : empilement d'avant. *Pourquoi* :
  sur le plan d'essai à six encarts, deux grands textes voisins se touchaient
  presque et le troisième arrivait à 0,04 unité de la source, sans que le
  contrôle le voie. Outils : `video/outils/planche.py` (plan d'essai `.json`),
  `video/outils/identique.py` (comparaison image par image d'un épisode),
  `video/outils/essais/`.
- **Code couleur de sens, R10** (12/11/2026, décision d'Alexandre) : `CONTRIB`
  (bleu) = ce que l'on verse, `INTEREST` (ambre) = ce que l'on gagne, `NEG`
  (#E2725B) = ce que l'on perd ; une perte n'apparaît jamais en ambre ni en
  bleu. Liens de `Flux` : paramètre `nature` (`neutre` par défaut, `gain`,
  `perte`). `perte` : le lien part de celui qui perd, tracé en `NEG`, montant
  précédé du signe moins (U+2212), et le nœud qui perd rétrécit à 88 % quand
  le montant est écrit (plancher 70 %) ; `gain` : ambre, signe plus. La nature
  l'emporte sur `couleur`. **Contrôle bloquant** (`check_sens` dans build.py) :
  refus d'une perte déclarée ou dessinée hors `NEG` ou sans signe moins, d'un
  gain hors ambre ou sans signe plus ; jugé sur le brief et sur les objets
  posés, contre la charte (`style.py`). Un lien `NEG` sans `nature` est
  refusé si `meta.catalogue_md5` du script est celui du catalogue actuel,
  signalé sinon. Mise en avant : un lien estompé estompe aussi son montant
  (0,25, comme sa pointe et ses particules). Les plans d'essai hors épisode passent les mêmes
  contrôles par `video/outils/controle.py`. *Pourquoi* : EP004 S17, « 1,2 %
  perdus » illustrés par un flux entrant.
- **Erosion** (13/11/2026 ; validée à l'écran le jour même sur le plan d'essai
  `video/outils/essais/erosion.json`, sortie du verrou `PILOTES`, au
  catalogue) : un capital qui fond, famille par défaut d'une perte.
  Colonne aux couleurs du capital (jamais `NEG`) ; à chaque perte, une tranche
  proportionnelle se détache du haut, vire au `NEG`, glisse sur le côté avec
  son montant signé, s'estompe à 50 % et reste en fantôme ; la valeur
  restante défile en compteur. `annees` > 1 : une tranche par année, en
  accéléré. R3 : `reste` (ce qu'il reste après chaque perte) et `cumul` sont
  donnés par le brief, le moteur ne calcule rien ; entre deux valeurs
  sourcées, le compteur et les tranches annuelles suivent un taux constant
  (silhouette, comme le modèle d'épargne). Éléments : `capital`, `perte_k`
  (tracés, 6 s au plus), `reste` (étiquette), `cumul` (surgissement). Ancres
  d'overlay posées telles quelles (`cues.anchor_align`) : `capital`,
  `perte_k`, `cumul`. Chaque perte et le cumul passent le contrôle de sens.
  Essais : `video/outils/essais/erosion.json`, `erosion_trois_pertes.json`.
- **Mention** (11/11/2026) : dérive de 2 % sur toute la durée du plan, portée par
  une seule animation (`Mention`) avec les deux fondus. *Pourquoi* : la dérive ne
  partait qu'après la seconde ligne, et seulement s'il restait plus de 4 s ; sur
  l'EP004, 4,1 s figées entre la première ligne et « ni ».
- **Règle de méthode** : tout changement de règle d'une famille → aperçu de
  **tous** ses plans dans l'épisode à publier, audio réel compris
  (`video/apercu.py`).
  *Pourquoi* : le cadre de mise en avant visible dès la première image de S17 et
  S22 n'apparaissait pas sur la référence.
  Commit : `683acf4`.
- **Piège Manim** : toute animation qui touche un objet pas encore à l'écran doit
  être introductrice (`introducer=True`, `Restyle`), sinon Manim le pose dès la
  première image. Vu deux fois sur l'EP001c (cadre des barres, bouton).
  Commits : `a8c490b`, `3e40004`.
- **Musique de fin et mastering** (règles de chaîne, 20/10/2026 ;
  `video/musique_fin.py`, `video/mastering.py`, paramètres dans
  `config/charte.json`) : la musique de la charte entre 3 s avant la fin de la
  voix du CTA, en fondu de 1,5 s, au moins 20 dB sous la voix ; à la fin de la
  voix elle remonte en 1 s jusqu'à −20 LUFS, se tient pendant la prolongation
  silencieuse, et sort en fondu de 2 s qui finit sur la dernière image. Jamais
  de boucle : un morceau trop court est signalé. Puis un gain global sur tout
  le mix amène l'épisode à −14 LUFS, avec un limiteur true-peak à −1 dBTP ;
  l'écart de 20 dB et le niveau de fin se mesurent dans la vidéo livrée. Le
  mixage se fait sur la piste finale, sans nouveau rendu de l'image
  (`-c:v copy`) ; `build.py` l'applique à chaque build.
  *Pourquoi* : la voix seule était à −16,6 LUFS et −0,4 dBTP, hors des cibles
  de diffusion.
  Contrôles : voix inchangée avant la musique (à l'échantillon près, au gain
  global près hors action du limiteur), crête, sonie, durée, chapitres et
  mid-rolls inchangés.
- **Miniatures** (règle de chaîne, 27/10/2026 ; `make miniature EP=…`,
  `video/miniature.py`) : le moteur dessine une miniature par variante de la
  section `## Miniatures` de `metadonnees.md` (familles `chiffre`,
  `contraste`, `bascule`), aux couleurs et dans la police de la charte,
  en 1280×720 et en 168×94, avec une planche. Phrase qui accroche, **6 mots au
  plus** (décision d'Alexandre), un seul chiffre géant, mot-clé dans un bloc
  incliné ; aucun terme du lexique interdit, aucune promesse de gain. Coin
  inférieur droit laissé libre pour la durée. Données recalculées
  (convention 9A), chiffre géant égal à l'écart des barres, tout nombre
  affiché présent dans `recherche.md`.
  *Pourquoi* : la v1, fidèle à la charte mais sage, n'accrochait pas ; la v3
  (textes en capitales, blocs, halos, phrases de 5 à 6 mots) a été validée
  sur l'EP001c.
- **Familles pilotes** : une famille nouvelle passe par le verrou `PILOTES`
  (components.py), un brief dans `video/pilotes/` rendu par `video/pilote.py`
  (jamais dans script.json), la validation à l'écran par Alexandre, **puis
  seulement** la sortie du verrou, l'entrée au catalogue et
  `non_regression.py --valider`. Comparaison et Flux ont suivi ce chemin
  (`799464d`, `75f232e`, `678b086`). Depuis le 13/11/2026, une famille peut
  aussi être validée sur un plan d'essai hors épisode (`video/outils/essais/`,
  `"_pilote": true` tant qu'elle est sous verrou), contrôlé par
  `video/outils/controle.py` et rendu par `video/outils/planche.py` : Erosion.

**Application** : relire le catalogue avant de toucher une famille ; ne jamais
réintroduire l'anticipation des barres ni une dérogation R6 sans accord ; ne
jamais sortir une famille de `PILOTES` sans validation à l'écran.

## Règles git

- Un commit par changement logique, directement sur `main`.
- Titre court en français sans accents (« R6 et controle final mesures en
  pixels »), corps qui dit quoi et pourquoi, chiffres vérifiés à l'appui, ligne
  `Co-Authored-By`.
- `git add` sur chemins explicites seulement, jamais `-A`.
- On n'indexe que ses propres fichiers, jamais les modifications d'Alexandre en
  cours ni les fichiers de `episodes/` produits par Cowork, sauf autorisation
  explicite et nominative.
- Aucune commande git qui touche aux fichiers de travail (`reset --hard`,
  `checkout`/`restore` sur un chemin, `clean`, `stash`) : si l'une semble
  nécessaire, s'arrêter et demander (règle écrite par Alexandre le 18/10/2026).
- Pour séparer deux chantiers dans un même fichier : `git apply --cached` d'un
  patch filtré (n'écrit que l'index). Pour vérifier l'état committé :
  `git archive HEAD | tar -x` dans un dossier temporaire.
- Lancer `python video/non_regression.py` avant tout commit qui touche le moteur,
  et le citer dans le message.
- Les médias (wav, mp3, mp4), `build/` et `video/` des épisodes, et
  `config/secrets.env` sont ignorés par git.
- Ne jamais demander de coller un mot de passe ou un jeton dans la conversation.
- **Fin de session** (règle du 19/10/2026) : à la fin de chaque session où il y a
  eu un commit, `git push`, puis confirmer à Alexandre que `origin/main` pointe
  sur le même commit que `main`. Dépôt distant :
  `https://github.com/AlexEllia/clair-net-enrichi`. Les médias, builds et
  secrets ne sont pas sur GitHub : ils se sauvegardent autrement.
- Après chaque épisode publié : lancer outils/sauvegarde_medias.bat.
  (Copie additive de `episodes\` vers
  `%OneDrive%\Sauvegardes\clair-net-enrichi\episodes\`, journal horodaté dans
  `...\clair-net-enrichi\journaux\`. `config/secrets.env` n'y est pas : il se
  garde dans un gestionnaire de mots de passe.)
- Les outils de contrôle réutilisables vivent dans `video/outils/` (épisode en
  argument, aucun chemin en dur), jamais dans un `build/` ignoré par git.
