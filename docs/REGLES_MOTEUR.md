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
- **Familles pilotes** : une famille nouvelle passe par le verrou `PILOTES`
  (components.py), un brief dans `video/pilotes/` rendu par `video/pilote.py`
  (jamais dans script.json), la validation à l'écran par Alexandre, **puis
  seulement** la sortie du verrou, l'entrée au catalogue et
  `non_regression.py --valider`. Comparaison et Flux ont suivi ce chemin
  (`799464d`, `75f232e`, `678b086`).

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
