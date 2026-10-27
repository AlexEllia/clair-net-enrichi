# Catalogue des composants visuels — Clair net enrichi

Ce document dit ce que tu peux écrire dans `manim_brief` pour un segment
`"type_visuel": "manim"`. Tout ce qui n'y figure pas n'existe pas : le moteur
de rendu refusera le segment. N'invente ni nom de composant, ni nom
d'élément, ni paramètre.

---

## 1. Les règles, avant tout

**R1 — Un composant du catalogue, et rien d'autre.** `manim_brief.composant`
prend l'un des noms de famille listés en section 4 comme *disponibles*.
Jamais un nom décrivant l'usage (`two_growth_curves`, `tipping_year_bars`…) :
l'usage se règle par les paramètres de la famille.

**R2 — Des éléments du catalogue, et rien d'autre.** Chaque
`revelations[].element` est un nom listé pour la famille choisie, écrit
exactement (`series_1_point_2`, `bar_3`), jamais un nom descriptif
(`curve_high_rate_y30`, `bar_lowest_rate`).

**R3 — Aucun chiffre calculé ni déduit par le moteur.** Chaque nombre écrit
à l'écran vient tel quel de `donnees` ou d'un paramètre du brief. Le moteur
ne fait aucune soustraction, aucun rapport, aucun arrondi. Si tu veux qu'un
écart, un multiplicateur ou un total s'affiche, écris sa valeur, et elle
doit figurer dans les sources du segment. Vérifie ce que la valeur mesure :
« multiplié par 4,3 » décrit un capital, pas l'écart entre deux courbes.

**R4 — Une révélation nommée par valeur énoncée.** Tout chiffre que la voix
énonce et que le visuel illustre doit être lisible à l'écran au moment où
la voix le dit. Pour chaque valeur de `donnees` que la voix énonce, écris
une révélation qui nomme cette valeur (`series_k_point_j` pour une courbe,
`bar_g` pour une barre, `band_g` pour une bande, `value_g` pour une jauge,
`link_k` pour un montant de flux), calée sur le mot qui l'énonce (section 2).
Sinon le visuel n'illustre rien.

**R5 — Première donnée tôt.** La première révélation de donnée tombe dans
la première phrase du segment, avant 4,5 s, idéalement vers 3 s. Le cadre
du graphe est du décor : il se construit en 1 à 4 s et s'efface devant le
premier tracé, qui commence à bouger dès que le cadre est posé. Si la phrase
d'ouverture n'a pas de chiffre, réécris-la pour qu'elle en porte un (voir
les exemples exemplaires, section 4). Évite aussi l'excès inverse : une
valeur énoncée dans la première seconde ne laisse le temps ni au cadre ni
au tracé.

**R6 — Pas de temps mort.** Entre deux révélations consécutives, l'écran
ne doit pas rester figé plus de 4 s. Tout dépend de l'élément qui vient :

- s'il **se trace** (courbe, barre qui monte, bande qui s'étend), il commence à bouger jusqu'à
  6 s avant son mot et comble l'attente : jusqu'à ~10 s entre deux valeurs
  énoncées restent vivantes. Une courbe comble moins : seulement la part de
  sa longueur qui précède le point énoncé ;
- s'il **surgit** (repère, accolade, annotation, ligne de référence), il ne
  bouge qu'à partir de son mot : il doit arriver moins de 4 s après la fin
  de l'animation précédente, soit ~4,3 s après une valeur et ~5,5 s après un
  autre surgissement.

R6 se juge sur ce que voit le spectateur : une fois le plan rendu, `make
check` mesure ses temps morts en pixels. Un fondu ne s'y voit qu'à ~20 %
d'opacité, soit ~0,5 s après son mot : vise 3,5 s au plus entre la fin d'une
animation et le mot suivant.

**R7 — Pas de mots dans la scène.** Le graphe n'écrit que des chiffres et
les symboles € et %, et ne dessine que les pictogrammes du catalogue. Tout mot
passe par `overlay_texte` : titre, titres d'axes, légendes, source, noms des
options et des nœuds (section 3).

**R8 — Le cadre n'est pas une révélation.** N'écris pas de révélation pour
le cadre, la grille ou les axes : ils se construisent seuls avant la
première donnée.

**R9 — Pas de catégorie muette.** Sur une famille à catégories distinctes
— `Bars`, `Areas` en bandes, `Comparaison` —, chaque ligne de `donnees` est une catégorie
que la voix mentionne, et elle a sa révélation. Une catégorie que la voix ne
mentionne pas ne figure pas dans `donnees` : elle s'afficherait pendant que
la voix parle d'autre chose. Les courbes, elles, gardent leurs points
intermédiaires : ils sont sur le chemin du tracé. Le build signale toute
barre, bande ou jauge sans révélation.

---

## 2. Comment le temps est compté

### La règle de rythme de la chaîne

> **Le mouvement anticipe, l'information attend.**

Un élément qui se trace — une courbe qui progresse, une barre qui monte,
une bande qui s'étend — peut commencer à se construire pendant que la voix parle encore de
l'élément précédent. Sa valeur, elle, n'apparaît qu'à l'arrivée, sur son
mot déclencheur. Une courbe qui progresse vers une valeur ne la révèle pas
tant qu'elle n'y est pas ; une barre qui monte non plus. Ce qui ne doit
jamais précéder le mot, c'est l'information — le point et sa valeur — pas
le mouvement qui y mène.

Conséquence pour toi : tu n'as pas à « faire de la place » avant une valeur
pour qu'elle ait le temps de se construire. Cale chaque révélation sur le
mot qui énonce la valeur ; le moteur planifie le mouvement à rebours depuis
ce mot.

### Ce que tu écris, ce que le recalage réécrit

Tu écris le script **avant** que l'audio existe. Tes `t_rel_s` sont donc des
**estimations** : compte les syllabes (ou les mots) depuis le début du
segment, au débit de la chaîne.

Après la génération audio, une phase de recalage reprend chaque révélation
et chaque overlay : elle cherche son `declencheur` dans l'alignement réel de
la voix, réécrit `t_rel_s` avec l'instant mesuré, et conserve ton estimation
dans `t_rel_s_estime`. Le moteur de rendu ne consomme que des valeurs
recalées.

Le `declencheur` est donc la clé de recherche, et deux conditions sont
impératives :

- **il recopie le texte de `vo_fr` mot pour mot** — mêmes mots, même
  orthographe, mêmes traits d'union (`cent soixante-cinq`, pas `165` ni
  `cent soixante cinq`) ;
- **il est unique dans le segment** — la chaîne n'apparaît qu'une fois dans
  `vo_fr`. `trente` ne convient pas si la phrase dit aussi « trente-quatre » :
  écris `trois cent trente-deux`.

Choisis comme déclencheur le mot qui énonce la valeur elle-même, pas le mot
qui l'annonce.

### Les chapitres

Un chapitre commence à chaque changement de `role` dans le script. Les rôles de
fin - `mention`, `ouverture`, `cta` - ne forment qu'un chapitre, qui commence au
premier d'entre eux. Les titres viennent du bloc « Chapitres » de
`metadonnees.md`, dans l'ordre (leurs timecodes sont recalculés par le build,
qui signale tout écart). Le build **bloque** si le nombre de titres diffère du
nombre de chapitres calculés, ou si un chapitre dure moins de 10 s (règle
YouTube). Écris donc autant de titres que de groupes de rôles, et donne au
moins 10 s à chacun.

### Les règles de durée

- Le segment dure `duree_audio_s`. Aucune révélation après la fin de la
  voix : pendant le silence qui suit, l'image est figée.
- Deux révélations au même `t_rel_s` forment une seule apparition.
- Deux animations ne se chevauchent jamais : chacune se termine 0,2 s avant
  la suivante.
- Durée d'une apparition qui surgit :
  `clamp(intervalle jusqu'à la révélation suivante − 0,2 s ; 0,3 s ; 1,5 s)`.
  Sous 0,3 s, le build signale que le script enchaîne trop vite.

Trois types d'éléments :

| Type | Durée max | Ce que signifie son `t_rel_s` |
|---|---|---|
| **tracé** (courbe, barre qui monte, bande qui s'étend) | 6 s | l'instant où le tracé *atteint* son point, ou la barre *atteint* sa hauteur. Le mouvement commence avant (jusqu'à 6 s avant) ; la valeur apparaît à l'arrivée. |
| **étiquette** | 0,3 s | l'instant où la valeur apparaît, sur un point déjà atteint. |
| **surgissement** (repère, accolade, annotation, ligne de référence) | 1,5 s | l'instant où l'élément commence à apparaître. Rien ne bouge avant son mot. |

---

## 3. Le texte : `overlay_texte`

Chaque entrée : `{"ancre": …, "t_rel_s": …, "texte_fr": …}`. Les overlays
sont recalés comme les révélations : donne-leur aussi un `declencheur`
unique quand leur instant dépend de la voix.

| Ancre | Où | Usage |
|---|---|---|
| `titre_haut` | en haut, centré | le titre du graphe |
| `axe_x` | centré sous l'axe horizontal | titre de l'axe horizontal |
| `axe_y` | à gauche de l'axe vertical, pivoté de 90° | titre de l'axe vertical |
| `legende` | bandeau sous le titre | une entrée par série, **dans l'ordre des séries** : la 1re légende prend la couleur de la série 1, etc. |
| `bas` | pied d'image | source, mention |
| `centre` | encart à droite du graphe | propos court |
| `option_1`, `option_2` | au-dessus de chaque colonne de `Comparaison` | nom de l'option, dans sa couleur |
| `noeud_k` | sous le k-ième nœud de `Flux` | nom du nœud |
| `lien_k` | le long du k-ième lien de `Flux` | nom du flux, dans sa couleur |
| `source_g` | sous la catégorie g de `Bars` | source de la barre g, en gris ; remplace `bas` |

- `axe_x`, `axe_y` et `titre_haut` : poser à ~0,6 s.
- Une légende : poser juste après la première révélation de sa série.
- Les titres d'axes commencent par une majuscule.
- `option_k`, `noeud_k`, `lien_k` : poser sur le mot qui nomme l'option, le
  nœud ou le flux, avec un `declencheur`. Ces ancres n'existent que sur leur
  famille.
- `source_g` : son instant est celui de la fin de croissance de la barre g,
  quel que soit le `t_rel_s` écrit. Une source identique à celle d'une barre
  précédente ne se répète pas.

---

## 4. Les familles

**Règle de méthode — un changement de règle se voit sur tout l'épisode.** Tout
changement de règle d'une famille donne lieu à un aperçu de **tous** les plans
de cette famille dans l'épisode à publier, avec leur audio réel - pas seulement
du plan de référence. La non-régression garantit les calendriers ; seul
l'aperçu de chaque plan montre ce que la règle fait aux autres données (un
cadre de mise en avant visible avant son heure sur S17 et S22 de l'EP001c, que
la référence S17 de l'EP001b ne montrait pas). Pour `Bars` :
`python video/apercu.py EPxxx Sxx`, plan par plan.

### Disponibles

#### `LineChart` — courbes

Une ou plusieurs séries tracées sur un axe horizontal continu (années, en
général). Pour montrer une croissance, un écart qui se creuse, un
croisement.

**`donnees`** — des tableaux de nombres, sous l'une de deux formes :

- large : `[x, y1, y2, …]`, une ligne par abscisse, une colonne par série ;
- longue : `[x, y]` répété ; à abscisse égale, la 1re ligne va à la série 1,
  la 2e à la série 2, etc.

Les nombres sont écrits en JSON (point décimal : `34.8`). Leur typographie à
l'écran (`34,8 %` ou `34.8%`) dépend de la langue du rendu, pas du script.

**Paramètres** (au même niveau que `composant` dans `manim_brief`) :

| Paramètre | Obligatoire | Valeurs admises | Effet |
|---|---|---|---|
| `interpolation` | **oui** | `"exponentielle"`, `"lineaire"`, `"escalier"` | La forme de la courbe **entre** deux points sourcés. C'est une hypothèse, pas un fait : déclare celle qui correspond à la source. `exponentielle` = taux constant entre deux points (pour un gain en %, c'est le capital 1 + y/100 qui croît à taux constant). `lineaire` = segments droits. `escalier` = la valeur tient jusqu'au point suivant. |
| `axes.unite_y` | **oui** | `"percent_growth"`, `"percent"`, `"EUR"`, `"EUR_per_year"`, ou autre | Format des chiffres de l'axe vertical et des étiquettes : `%` pour `percent*`, `€` pour `EUR*`, nombre nu sinon. `percent_growth` signale un gain en %. |
| `axes.unite_x` | non | libre (`"years"`…) | Documentaire ; l'axe horizontal porte des nombres nus. |
| `origine` | non | `[x, y]` | Point commun ajouté en tête de chaque série (ex. `[0, 0]` : gain nul au départ). Il ne porte pas d'étiquette. |
| `couleurs` | non | liste parmi `"INTEREST"` (ambre), `"CONTRIB"` (bleu), `"TEAL"`, `"NEG"`, `"WHITE_DIM"` | Une par série. Convention de la chaîne : bleu = ce que vous versez, ambre = ce que le capital verse. |
| `croisement` | non | `true` | Repère au premier croisement des séries 1 et 2. |
| `ecart` | non | `{"x": 30, "valeur": 9.5, "format": "facteur"}` | Accolade verticale entre les séries à l'abscisse `x`. `valeur` est facultative ; si elle est écrite, elle vient des sources (R3). `format` : `"nombre"`, `"pct"`, `"euro"`, `"facteur"` (×). |
| `facteur` | non | `{"serie": 1, "x": 30, "valeur": 4.3}` | Multiplicateur « ×4,3 » écrit à côté du point de la série à l'abscisse `x`. `valeur` vient des sources (R3). |

**Éléments adressables dans `revelations`** :

| Élément | Type | Remarque |
|---|---|---|
| `series_k_point_j` | tracé (≤ 6 s) + étiquette | Le j-ième point sourcé de la série k (`origine` exclue, dans l'ordre de `donnees`). À écrire pour **chaque valeur énoncée** (R4). La courbe est planifiée pour atteindre ce point à cet instant ; sa valeur apparaît alors. |
| `series_k` | tracé (≤ 6 s) | À n'écrire que si aucun point de la série n'est énoncé ; son `t_rel_s` vaut alors rendez-vous de son premier point. |
| `crossing` | surgissement (1,5 s) | Exige `croisement: true`. |
| `gap` | surgissement (1,5 s) | Exige `ecart`. |
| `factor` | surgissement (1,5 s) | Exige `facteur`. |
| ~~`frame`~~ | décor | Ne pas écrire (R8). |

**Comment les séries se partagent le temps** :

- Tu peux alterner librement entre séries, dans l'ordre naturel d'une
  comparaison : série 1 à 20 ans, série 2 à 20 ans, puis série 1 à 30 ans,
  série 2 à 30 ans. Chaque courbe avance par morceaux vers son prochain
  point, s'arrête, et reprend quand vient son tour.
- Une seule courbe bouge à la fois. Entre deux points énoncés de séries
  différentes, laisse au moins 0,7 s (0,2 s d'écart + 0,5 s de tracé
  minimal). Deux valeurs de séries différentes ne peuvent pas tomber sur le
  même mot : donne-leur chacune le sien.
- Un point dont la voix ne dit pas la valeur peut rester dans `donnees` sans
  révélation : il est sur le chemin du tracé (R9). Quand sa série n'a plus de
  rendez-vous, le tracé continue à vitesse constante et sa valeur apparaît à
  l'arrivée.

**Exemple réel** — le plan S09 de l'EP001b, validé à l'écran, réécrit dans
ce format. Ne reprends pas ses données : « 330 » y est un arrondi, la valeur
exacte à 5 % sur trente ans est 332,2 (1,05³⁰ = 4,3219). C'est un plan réel, mais
**pas exemplaire** : la première valeur tombe à
6,94 s, contre R5, parce que la phrase d'ouverture (« Ce n'est pas une
opinion : l'AMF publie son propre calcul. ») ne porte aucun chiffre. Le
tracé occupe l'attente, mais rien de chiffré ne se montre avant 7 s.

```json
{
  "type_visuel": "manim",
  "manim_brief": {
    "composant": "LineChart",
    "donnees": [[20, 165], [20, 22], [30, 330], [30, 34.8]],
    "axes": {"unite_x": "years", "unite_y": "percent_growth"},
    "interpolation": "exponentielle",
    "origine": [0, 0],
    "couleurs": ["INTEREST", "WHITE_DIM"],
    "facteur": {"serie": 1, "x": 30, "valeur": 4.3},
    "revelations": [
      {"element": "series_1_point_1", "t_rel_s": 6.94, "declencheur": "cent soixante-cinq"},
      {"element": "series_2_point_1", "t_rel_s": 11.72, "declencheur": "vingt-deux"},
      {"element": "factor", "t_rel_s": 15.97, "declencheur": "quatre virgule trois"}
    ]
  },
  "overlay_texte": [
    {"ancre": "titre_haut", "t_rel_s": 0.6, "texte_fr": "Deux rendements, même durée"},
    {"ancre": "axe_x", "t_rel_s": 0.6, "texte_fr": "Années"},
    {"ancre": "axe_y", "t_rel_s": 0.6, "texte_fr": "Gain en pourcentage"},
    {"ancre": "legende", "t_rel_s": 7.34, "texte_fr": "Cinq pour cent par an"},
    {"ancre": "legende", "t_rel_s": 12.12, "texte_fr": "Un pour cent par an"},
    {"ancre": "bas", "t_rel_s": 15.17, "texte_fr": "Source : AMF, décembre 2021"}
  ]
}
```

**Exemple exemplaire** — le même propos, écrit pour respecter toutes les
règles. **C'est celui-ci qu'il faut imiter.** La phrase d'ouverture porte
le premier chiffre ; chaque valeur énoncée a sa révélation, y compris les
deux valeurs à 30 ans, en alternant les séries ; chaque déclencheur est
unique dans `vo_fr`. Les `t_rel_s` sont des estimations (165 mots/min) que
le recalage remplacera.

```json
{
  "vo_fr": "À cinq pour cent par an, un capital gagne cent soixante-cinq pour cent en vingt ans. À un pour cent, il gagne vingt-deux pour cent. Sur trente ans, l'écart se creuse : trois cent trente-deux pour cent contre trente-quatre virgule huit. Le premier capital est multiplié par quatre virgule trois. C'est le calcul de l'AMF.",
  "type_visuel": "manim",
  "manim_brief": {
    "composant": "LineChart",
    "donnees": [[20, 165], [20, 22], [30, 332.2], [30, 34.8]],
    "axes": {"unite_x": "years", "unite_y": "percent_growth"},
    "interpolation": "exponentielle",
    "origine": [0, 0],
    "couleurs": ["INTEREST", "WHITE_DIM"],
    "facteur": {"serie": 1, "x": 30, "valeur": 4.3},
    "revelations": [
      {"element": "series_1_point_1", "t_rel_s": 3.27, "declencheur": "cent soixante-cinq"},
      {"element": "series_2_point_1", "t_rel_s": 8.0, "declencheur": "vingt-deux"},
      {"element": "series_1_point_2", "t_rel_s": 11.64, "declencheur": "trois cent trente-deux"},
      {"element": "series_2_point_2", "t_rel_s": 13.82, "declencheur": "trente-quatre virgule huit"},
      {"element": "factor", "t_rel_s": 17.09, "declencheur": "quatre virgule trois"}
    ]
  },
  "overlay_texte": [
    {"ancre": "titre_haut", "t_rel_s": 0.6, "texte_fr": "Deux rendements, même durée"},
    {"ancre": "axe_x", "t_rel_s": 0.6, "texte_fr": "Années"},
    {"ancre": "axe_y", "t_rel_s": 0.6, "texte_fr": "Gain en pourcentage"},
    {"ancre": "legende", "t_rel_s": 3.67, "texte_fr": "Cinq pour cent par an"},
    {"ancre": "legende", "t_rel_s": 8.4, "texte_fr": "Un pour cent par an"},
    {"ancre": "bas", "t_rel_s": 18.18, "texte_fr": "Source : AMF, décembre 2021", "declencheur": "C'est le calcul"}
  ]
}
```

#### `Bars` — barres

Des barres verticales, une catégorie par ligne de `donnees`. Pour comparer
des valeurs entre elles : un résultat par taux, par horizon, par scénario.

**`donnees`** — `[x, v1, v2, …]` : `x` est la catégorie (écrite sous le
groupe de barres), `v1…vn` les valeurs des séries. Une seule valeur par
ligne = barres simples. Les valeurs négatives descendent sous zéro.

**Paramètres** :

| Paramètre | Obligatoire | Valeurs admises | Effet |
|---|---|---|---|
| `mode` | **oui** | `"simple"`, `"groupees"`, `"empilees"` | `simple` : une valeur par ligne. `groupees` : les séries côte à côte dans chaque catégorie. `empilees` : les séries empilées ; n'empile que des parts qui s'additionnent réellement, et donne chaque part dans `donnees` (le moteur ne calcule jamais « le reste »). |
| `axes.unite_y` | **oui** | comme `LineChart` | Format des valeurs (axe vertical et étiquettes). |
| `axes.unite_x` | non | `"percent…"`, `"EUR…"`, ou autre | Format des catégories : `1,7 %` pour `percent…`, nombre nu sinon. |
| `couleurs` | non | comme `LineChart` | Une par série. |
| `mise_en_avant` | non | `{"barre": g}` ou `{"barre": g, "serie": s}` | Encadre une barre et estompe les autres. |
| `repere` | non | `{"valeur": 50}` | Ligne horizontale pointillée à cette hauteur, avec sa valeur. La valeur vient des sources (R3). |
| `annotation` | non | `{"barre": g, "valeur": 3, "format": "facteur"}` | Un chiffre écrit au-dessus d'une catégorie (« ×3 »). La valeur vient des sources (R3). |

**Éléments adressables dans `revelations`** :

| Élément | Type | Remarque |
|---|---|---|
| `bar_g` | tracé (≤ 6 s) + étiquette | La barre de la catégorie g (1re ligne de `donnees` = `bar_1`), en mode `simple`. À écrire pour **chaque** barre, sur le mot qui énonce sa valeur (R4, R9) : la barre atteint sa hauteur à cet instant, et sa valeur apparaît. |
| `bar_g_s` | tracé (≤ 6 s) + étiquette | La barre de la série s dans la catégorie g, en modes `groupees` et `empilees`. |
| `highlight` | surgissement (1,5 s) | Exige `mise_en_avant`. |
| `reference` | surgissement (1,5 s) | Exige `repere`. |
| `annotation` | surgissement (1,5 s) | Exige `annotation`. |
| ~~`frame`~~ | décor | Ne pas écrire (R8). |

**Source par barre** — pas un élément de `revelations`, un overlay : une
entrée `{"ancre": "source_g", "texte_fr": "…"}` par barre qui a sa source.
Elle s'écrit en gris sous la catégorie g, en fondu de 0,4 s, à la fin de la
croissance de sa barre, et reste jusqu'à la fin du plan. Une même source
partagée par plusieurs barres ne s'écrit qu'une fois, sous la première. Dès
qu'une source par barre existe, elle remplace la source globale `bas`.

**Quand une barre monte (règle v3-phrase)** — la barre 1 monte dès que le
cadre est posé, 6 s au plus, et atteint sa hauteur sur son mot. Chaque barre
suivante ne commence à monter qu'**au début de la phrase qui contient son
propre déclencheur** (dans l'alignement réel de la voix : la première lettre
après le « . », « ? » ou « ! » qui précède ce déclencheur), et atteint sa
hauteur sur ce déclencheur : elle monte pendant que la voix l'annonce, jamais
pendant que la voix parle encore de la précédente. Sa croissance dure 6 s au
plus ; sous 0,6 s, la barre surgit avec sa valeur, comme une étiquette.

**Mise en avant pendant l'attente** — si, entre l'arrivée de la barre g (son
étiquette, et le fondu de sa source quand elle en a une) et le début de
croissance de la barre g+1, l'écran resterait figé plus de 4 s, la barre g
passe en mise en avant (encadrée, les barres déjà montées estompées) au milieu
de cette attente, calée sur le début du mot le plus proche ; elle revient à
l'état normal quand g+1 commence à monter. C'est le moteur qui le décide :
rien à écrire. La voix parle encore de la barre g, l'image la désigne.

Une seule barre monte à la fois. Entre deux valeurs énoncées, laisse au
moins 0,7 s. Mise en avant, repère et annotation écrits par le brief, eux,
surgissent en 1,5 s sur leur mot. Une catégorie que la voix ne mentionne pas
n'a pas sa place dans `donnees` (R9).

**Exemple réel** — le plan S17 de l'EP001b, validé à l'écran (version 3, du
18/10/2026), réécrit dans ce format. Il est vrai mais **pas exemplaire** : la
première valeur n'est lisible qu'à 9,82 s, contre R5, parce que la phrase
d'ouverture (« Une seule chose déplace la bascule : le rendement. ») ne porte
aucun chiffre.

```json
{
  "type_visuel": "manim",
  "manim_brief": {
    "composant": "Bars",
    "mode": "simple",
    "donnees": [[1.7, 42], [2.6, 28], [5.0, 15], [8.81, 9]],
    "axes": {"unite_x": "percent_per_year", "unite_y": "years"},
    "couleurs": ["INTEREST"],
    "revelations": [
      {"element": "bar_1", "t_rel_s": 9.82, "declencheur": "quarante-deuxième"},
      {"element": "bar_2", "t_rel_s": 13.16, "declencheur": "vingt-huitième"},
      {"element": "bar_3", "t_rel_s": 21.73, "declencheur": "quinzième"},
      {"element": "bar_4", "t_rel_s": 24.6, "declencheur": "neuvième"}
    ]
  }
}
```

Ce que ça donne : la barre 1 monte de 3,82 s à 9,82 s et « 42 » apparaît sur
« quarante-deuxième » ; la barre 2 monte de 11,28 s, au début de sa phrase
(« À deux virgule six »), à 13,16 s, sur « vingt-huitième ». La voix commente
alors les fonds en euros jusqu'à 20,08 s : l'attente dépasserait 4 s, la
barre 2 passe donc en mise en avant à 16,76 s, et revient à l'état normal
quand la barre 3 commence à monter, à 20,08 s, sur « À cinq pour cent ». Elle
atteint 15 sur « quinzième » à 21,73 s ; la barre 4 monte de 22,96 s à
24,60 s. Plus longue immobilité mesurée en pixels : 3,3 s.

**Exemple exemplaire** — le même propos, écrit pour respecter toutes les
règles. **C'est celui-ci qu'il faut imiter.** La première phrase porte la
première valeur ; chaque année de bascule a sa révélation sur le mot qui
l'énonce ; la définition des fonds en euros précède leur valeur, dans la
même phrase, si bien que la barre 2 monte pendant qu'on l'explique. Les
`t_rel_s` sont des estimations (3,94 syllabes/s) que le recalage remplacera.

```json
{
  "vo_fr": "Au Livret A, la bascule n'arrive que la quarante-deuxième année, à un virgule sept pour cent. Aux fonds en euros, la partie garantie de l'assurance-vie, c'est la vingt-huitième, à deux virgule six pour cent en deux mille vingt-cinq. À cinq pour cent, la quinzième. À huit virgule huit, la neuvième. Une seule chose déplace la bascule : le rendement.",
  "type_visuel": "manim",
  "manim_brief": {
    "composant": "Bars",
    "mode": "simple",
    "donnees": [[1.7, 42], [2.6, 28], [5.0, 15], [8.81, 9]],
    "axes": {"unite_x": "percent_per_year", "unite_y": "years"},
    "couleurs": ["INTEREST"],
    "revelations": [
      {"element": "bar_1", "t_rel_s": 2.79, "declencheur": "quarante-deuxième"},
      {"element": "bar_2", "t_rel_s": 10.91, "declencheur": "vingt-huitième"},
      {"element": "bar_3", "t_rel_s": 15.99, "declencheur": "quinzième"},
      {"element": "bar_4", "t_rel_s": 18.02, "declencheur": "neuvième"}
    ]
  },
  "overlay_texte": [
    {"ancre": "titre_haut", "t_rel_s": 0.6, "texte_fr": "Année de bascule selon le rendement"},
    {"ancre": "axe_x", "t_rel_s": 0.6, "texte_fr": "Rendement net annuel"},
    {"ancre": "axe_y", "t_rel_s": 0.6, "texte_fr": "Année de bascule"}
  ]
}
```

Ce que ça donne (estimations) : le cadre se pose en 1 s ; la barre 1 monte
de 1,2 s à 2,79 s et « 42 » apparaît sur « quarante-deuxième » ; la barre 2
monte du début de sa phrase, 6,09 s, à « vingt-huitième », 10,91 s, pendant
« Aux fonds en euros, la partie garantie de l'assurance-vie » ; la barre 3
monte de 14,72 s à 15,99 s, la barre 4 de 16,50 s à 18,02 s, chacune pendant
sa propre phrase. Aucune attente ne dépasse 4 s (3,5 s au plus, entre « 28 »
et la phrase des 5 %) : pas de mise en avant.

#### `Areas` — bandes de dispersion

Une bande verticale par catégorie — une durée de détention, un horizon —
qui montre où tombent les résultats possibles. Pour faire *voir* qu'une
dispersion se resserre, ou qu'un pire cas s'améliore avec le temps.

**`donnees`** — sous l'une de deux formes :

- `[x, bas, haut]` : la bande va d'une borne sourcée à l'autre ;
- `[x, borne]` : une seule borne est sourcée (par exemple le 1er centile) ;
  le paramètre `borne` dit alors laquelle.

**Paramètres** :

| Paramètre | Obligatoire | Valeurs admises | Effet |
|---|---|---|---|
| `mode` | **oui** | `"bandes"` | Le mode `"aires"` n'est pas encore disponible : le moteur le refuse. |
| `borne` | **oui** si une seule valeur par ligne | `"plancher"`, `"plafond"` | `plancher` : la valeur est un minimum — « un cas sur cent tombe sous… », « 99 cas sur 100 dépassent… ». La bande part de ce plancher, s'ouvre vers le haut et s'efface en dégradé : le moteur ne dessine jamais une borne que la source ne donne pas. `plafond` : l'inverse, ouverte vers le bas. |
| `axes.unite_y` | **oui** | comme `LineChart` | Format des valeurs (axe vertical et étiquettes). |
| `axes.unite_x` | non | comme `Bars` | Format des catégories. |
| `couleurs` | non | une couleur | Couleur du corps des bandes (bleu par défaut). |

**Éléments adressables dans `revelations`** :

| Élément | Type | Remarque |
|---|---|---|
| `band_g` | tracé (≤ 6 s) + étiquette | La bande de la catégorie g (1re ligne de `donnees` = `band_1`). À écrire pour **chaque** bande (R9). Sur le mot qui énonce sa borne, la bande atteint sa borne et la valeur apparaît — en rouge si elle est négative, en vert si elle est positive. Elle s'est étendue avant, depuis son côté ouvert (ou depuis son milieu pour une bande à deux bornes). |
| ~~`frame`~~ | décor | Ne pas écrire (R8). La ligne du zéro fait partie du cadre. |

Chaque bande de `donnees` a sa révélation, sur le mot qui énonce sa borne
(R4). Une catégorie que la voix ne mentionne pas ne figure pas dans
`donnees` (R9) : l'exemple réel ci-dessous montre ce qui se passe sinon.

**Exemple réel** — le plan S20 de l'EP001b, réécrit dans ce format. Il est
vrai mais **pas exemplaire** : la première valeur n'est lisible qu'à
11,92 s (R5), et deux catégories (10 et 20 ans) figurent dans `donnees` sans
que la voix les mentionne (R9).

```json
{
  "type_visuel": "manim",
  "manim_brief": {
    "composant": "Areas",
    "mode": "bandes",
    "borne": "plancher",
    "donnees": [[5, -13.0], [10, -4.8], [20, -3.0], [30, 2.4]],
    "axes": {"unite_x": "years", "unite_y": "percent_per_year"},
    "revelations": [
      {"element": "band_1", "t_rel_s": 11.92, "declencheur": "treize"},
      {"element": "band_4", "t_rel_s": 17.41, "declencheur": "deux virgule quatre"}
    ]
  }
}
```

Ce que ça donne : le cadre se construit en 4 s ; la bande des 5 ans descend
de 5,92 s à 11,92 s et « −13 % » apparaît sur « treize » ; les bandes des 10
et 20 ans suivent (−4,8 % à 13,75 s, −3 % à 15,58 s) pendant que la voix
parle déjà des trente ans ; la bande des 30 ans atteint 2,4 % sur « deux
virgule quatre ».

**Exemple exemplaire** — le même propos, écrit pour respecter toutes les
règles. **C'est celui-ci qu'il faut imiter.** La première phrase porte la
première valeur ; chaque borne est énoncée et a sa révélation sur le mot
qui l'énonce ; la source vient à la fin. Les `t_rel_s` sont des estimations
(165 mots/min) que le recalage remplacera.

```json
{
  "vo_fr": "Sur cinq ans de Bourse, un cas sur cent tombe sous moins treize pour cent par an. Sur dix ans, moins quatre virgule huit. Sur vingt ans, moins trois. Et sur trente ans, quatre-vingt-dix-neuf cas sur cent dépassent deux virgule quatre pour cent par an. C'est la mesure de l'AMF sur soixante-dix ans de Bourse de Paris.",
  "type_visuel": "manim",
  "manim_brief": {
    "composant": "Areas",
    "mode": "bandes",
    "borne": "plancher",
    "donnees": [[5, -13.0], [10, -4.8], [20, -3.0], [30, 2.4]],
    "axes": {"unite_x": "years", "unite_y": "percent_per_year"},
    "revelations": [
      {"element": "band_1", "t_rel_s": 4.0, "declencheur": "moins treize"},
      {"element": "band_2", "t_rel_s": 7.27, "declencheur": "moins quatre virgule huit"},
      {"element": "band_3", "t_rel_s": 9.82, "declencheur": "moins trois"},
      {"element": "band_4", "t_rel_s": 13.82, "declencheur": "deux virgule quatre"}
    ]
  },
  "overlay_texte": [
    {"ancre": "titre_haut", "t_rel_s": 0.6, "texte_fr": "Dispersion des performances selon la durée"},
    {"ancre": "axe_x", "t_rel_s": 0.6, "texte_fr": "Durée de détention"},
    {"ancre": "axe_y", "t_rel_s": 0.6, "texte_fr": "Performance réelle annualisée"},
    {"ancre": "bas", "t_rel_s": 16.36, "texte_fr": "Source : AMF, décembre 2021", "declencheur": "C'est la mesure"}
  ]
}
```

Ce que ça donne : le cadre se pose en 1 s ; chaque bande descend pendant que
la voix introduit son horizon et atteint son plancher sur la valeur ; le
plancher des 30 ans passe au-dessus du zéro, en vert. L'écran n'est jamais
figé entre la première et la dernière valeur.

#### `Comparaison` — deux options face à face

Deux colonnes, une par option, qui se remplissent en alternance au rythme de
la voix. Pour opposer deux montants, deux pourcentages, deux durées : ce que
vous versez et ce que le capital vous verse, deux taux, deux scénarios. Les
éléments sont des jauges (une valeur écrite à leur sommet), des
pictogrammes qui se comptent, un écart, une mise en avant. Le nom de chaque
option passe en overlay, sur `option_1` et `option_2` (R7).

**`donnees`** — `[option, valeur]`, une ligne par jauge, dans l'ordre
d'entrée. `option` vaut 1 (colonne de gauche) ou 2 (colonne de droite) ; une
option peut porter plusieurs jauges. Toutes les jauges partagent la même
échelle : une jauge de 55 face à une jauge de 2 400 reste un trait, et c'est
voulu. Les valeurs sont positives ou nulles.

**Paramètres** :

| Paramètre | Obligatoire | Valeurs admises | Effet |
|---|---|---|---|
| `unite` | **oui** | `"EUR"`, `"percent"`, ou autre | Format des valeurs écrites : `€`, `%`, nombre nu. |
| `couleurs` | non | deux couleurs, comme `LineChart` | Une par option. Convention de la chaîne : bleu = ce que vous versez, ambre = ce que le capital verse. |
| `pictogrammes` | non | `[{"option": k, "icone": nom, "nombre": n}]` | `n` pictogrammes (1 à 40) qui apparaissent un à un dans la colonne k, à côté de ses jauges. `n` est un nombre que la voix énonce et que les sources portent (R3) : « douze mois » donne 12. `icone` : un nom de la liste ci-dessous. |
| `ecart` | non | `{"entre": [g1, g2], "valeur": v, "format": f}` | Pointillé à la hauteur de la plus petite des jauges `g1` et `g2` (rangs dans `donnees`) et accolade le long de la plus grande. `valeur` est facultative ; si elle est écrite, elle vient des sources (R3). `format` : comme `LineChart`. |
| `mise_en_avant` | non | `{"option": k}` | Encadre l'option k et estompe l'autre. |
| `suite` | non | `{"option": k}` | Une bande ouverte au-dessus de la dernière jauge de k, en dégradé, sans borne ni valeur : ce qui viendra et qu'on ne chiffre pas encore. Des particules y montent jusqu'à la fin du plan. |

**Éléments adressables dans `revelations`** :

| Élément | Type | Remarque |
|---|---|---|
| `value_g` | tracé (≤ 6 s) + étiquette | La jauge de la g-ième ligne de `donnees` monte et atteint sa hauteur sur le mot qui énonce sa valeur ; la valeur s'écrit alors. À écrire pour **chaque** ligne (R4, R9). |
| `pictos_k` | tracé (≤ 6 s) | Les pictogrammes de la k-ième entrée de `pictogrammes` apparaissent un à un ; le dernier arrive sur le mot qui énonce leur nombre. |
| `suite` | tracé (≤ 6 s) | Exige `suite`. La bande atteint son sommet sur son mot ; les particules continuent ensuite jusqu'à la fin du plan. |
| `gap` | surgissement (1,5 s) | Exige `ecart`. |
| `highlight` | surgissement (1,5 s) | Exige `mise_en_avant`. |
| ~~`frame`~~ | décor | Ne pas écrire (R8). Les deux lignes de base et le séparateur se construisent seuls ; si la première donnée tarde, toute la structure (voir ci-dessous). |

**Comment les deux options se partagent le temps** : comme les barres, un
seul tracé bouge à la fois, et il commence à monter pendant que la voix parle
encore de l'élément précédent. Alterne les options dans l'ordre où la voix les
oppose. Laisse au moins 0,7 s entre deux valeurs énoncées. Un tracé qui suit un
écart ou une mise en avant attend sa fin pour partir : pour qu'une `suite`
monte sur toute sa durée, place son mot au moins 7,7 s après le surgissement
qui la précède (1,5 s + 0,2 s + 6 s), sinon elle monte plus vite.

Une jauge trop basse pour qu'on la voie monter (moins de 0,3 unité de haut,
comme 55 € face à 2 400 €) n'anticipe pas : six secondes d'un trait immobile
à l'œil ne sont pas du mouvement. Elle monte en 0,5 s, juste avant son mot.

**Quand la première donnée tarde** — si le premier mouvement de donnée
arrive plus de 4 s après le début du plan, la structure de la comparaison se
construit pendant toute l'attente, sans aucune valeur : colonne par colonne,
sa ligne de base et un socle clair sous chaque jauge, puis le contour vide de
la jauge, à la hauteur maximale du plan (le même pour toutes : il ne dit rien
des valeurs) ; le séparateur vient avec la seconde colonne. Ni chiffre, ni
jauge remplie, ni pictogramme : le nombre de pictogrammes est une
information, il attend son mot. Les étapes s'étalent à pas régulier sur
toute l'attente ; au-delà de 3 s entre deux étapes, le build avertit que la
première donnée arrive trop tard pour que la structure seule tienne l'écran.
Un nom d'option sans `declencheur` apparaît avec sa colonne ; avec un
`declencheur`, sur son mot. Rien à écrire pour cela : c'est le moteur qui
décide. Cela ne dispense pas de R5 : une première valeur tôt reste la règle.

**Pictogrammes disponibles** (Lucide, licence ISC, `video/pictos/lucide/`) :
`banknote`, `building-2`, `calendar`, `coins`, `flag`, `hand-coins`, `hotel`,
`hourglass`, `house`, `landmark`, `percent`, `piggy-bank`, `sprout`,
`trending-up`, `user`, `wallet`. Aucun autre : un nom absent de cette liste
est refusé.

**Exemple réel** — le plan pilote S02 de l'EP001c, validé à l'écran le
17/10/2026, puis dans sa version 2 le 18/10/2026 (structure construite
pendant l'attente). Il est vrai mais **pas exemplaire** : la première valeur
n'est lisible qu'à 8,14 s, contre R5, parce que les deux phrases d'ouverture
(« Sauf que tout commence mal. Les intérêts, c'est ce que votre épargne vous
rapporte. ») ne portent aucun chiffre. La structure et les overlays d'option
et de titre occupent l'attente.

```json
{
  "type_visuel": "manim",
  "manim_brief": {
    "composant": "Comparaison",
    "unite": "EUR",
    "donnees": [[1, 55], [2, 2400]],
    "couleurs": ["INTEREST", "CONTRIB"],
    "pictogrammes": [{"option": 2, "icone": "calendar", "nombre": 12}],
    "ecart": {"entre": [1, 2]},
    "mise_en_avant": {"option": 1},
    "suite": {"option": 1},
    "revelations": [
      {"element": "value_1", "t_rel_s": 8.14, "declencheur": "cinquante-cinq euros, pour deux"},
      {"element": "value_2", "t_rel_s": 9.62, "declencheur": "deux mille quatre cents"},
      {"element": "pictos_1", "t_rel_s": 13.48, "declencheur": "douze mois"},
      {"element": "gap", "t_rel_s": 16.27, "declencheur": "ça ne vaut pas la peine"},
      {"element": "highlight", "t_rel_s": 18.96, "declencheur": "l'effet paraît nul"},
      {"element": "suite", "t_rel_s": 31.4, "declencheur": "cache la suite"}
    ]
  },
  "overlay_texte": [
    {"ancre": "option_1", "t_rel_s": 2.22, "texte_fr": "Intérêts", "declencheur": "intérêts, c'est"},
    {"ancre": "titre_haut", "t_rel_s": 5.56, "texte_fr": "Année 1", "declencheur": "première année"},
    {"ancre": "option_2", "t_rel_s": 10.53, "texte_fr": "Versements", "declencheur": "versés"},
    {"ancre": "bas", "t_rel_s": 23.0, "texte_fr": "Source : AMF, décembre 2021", "declencheur": "l'a écrit"}
  ]
}
```

Ce que ça donne : la première donnée tarde, la structure se construit de 0 à
7,44 s en quatre étapes à 1,86 s d'intervalle (base et socle des intérêts,
contour vide, base et socle des versements avec le séparateur, contour vide),
entre lesquelles « Intérêts » et « Année 1 » arrivent sur leur mot ; la jauge
de 55 €, un trait, monte en 0,5 s et « 55 € » s'écrit sur « cinquante-cinq » ;
la jauge de
2 400 € monte en 1,3 s ; les douze calendriers apparaissent un à un de 9,82 s
à « douze mois » ; l'écart surgit sur « ça ne vaut pas la peine », la mise en
avant sur « l'effet paraît nul » ; la bande monte de 25,4 s à « cache la
suite », et l'argent y monte jusqu'à la fin du plan. Sur la voix par blocs de
l'EP001c, aucune immobilité de plus de 2 s avant la première donnée, 2,9 s au
plus sur le plan (27,9 s figées au diagnostic, en fond animé).

**Exemple exemplaire** — le même propos, écrit pour respecter toutes les
règles. **C'est celui-ci qu'il faut imiter.** La première phrase porte la
première valeur ; chaque valeur et le nombre de pictogrammes ont leur
révélation sur le mot qui les énonce ; la `suite` vient assez tard après la
mise en avant pour monter sur toute sa durée. Les `t_rel_s` sont des
estimations (3,94 syllabes/s) que le recalage remplacera.

```json
{
  "vo_fr": "À cinq pour cent, vos intérêts de la première année : cinquante-cinq euros. Vos versements, eux : deux mille quatre cents euros. Cinquante-cinq euros, pour douze mois d'efforts. Vu comme ça, l'écart semble sans appel, et l'effet paraît nul. Ce que le temps fabrique ne se voit pas encore : il travaille en silence.",
  "type_visuel": "manim",
  "manim_brief": {
    "composant": "Comparaison",
    "unite": "EUR",
    "donnees": [[1, 55], [2, 2400]],
    "couleurs": ["INTEREST", "CONTRIB"],
    "pictogrammes": [{"option": 2, "icone": "calendar", "nombre": 12}],
    "ecart": {"entre": [1, 2]},
    "mise_en_avant": {"option": 1},
    "suite": {"option": 1},
    "revelations": [
      {"element": "value_1", "t_rel_s": 3.3, "declencheur": "cinquante-cinq euros. Vos"},
      {"element": "value_2", "t_rel_s": 6.09, "declencheur": "deux mille quatre cents"},
      {"element": "pictos_1", "t_rel_s": 9.39, "declencheur": "douze mois"},
      {"element": "gap", "t_rel_s": 11.17, "declencheur": "l'écart semble"},
      {"element": "highlight", "t_rel_s": 12.94, "declencheur": "l'effet paraît nul"},
      {"element": "suite", "t_rel_s": 18.27, "declencheur": "en silence"}
    ]
  },
  "overlay_texte": [
    {"ancre": "option_1", "t_rel_s": 1.02, "texte_fr": "Intérêts", "declencheur": "vos intérêts"},
    {"ancre": "titre_haut", "t_rel_s": 2.54, "texte_fr": "Année 1", "declencheur": "première année"},
    {"ancre": "option_2", "t_rel_s": 4.82, "texte_fr": "Versements", "declencheur": "Vos versements"},
    {"ancre": "bas", "t_rel_s": 14.21, "texte_fr": "Hypothèse de calcul : 200 € par mois, 5 % par an", "declencheur": "Ce que le temps"}
  ]
}
```

Ce que ça donne : le cadre se pose en 1 s ; la jauge des intérêts monte et
« 55 € » s'écrit sur « cinquante-cinq » ; celle des versements monte pendant
« Vos versements, eux » et atteint 2 400 € sur son mot ; les calendriers
comblent l'attente jusqu'à « douze mois » ; écart puis mise en avant ; la
bande part à 14,64 s, à la fin de la mise en avant, et l'argent y monte
jusqu'au dernier mot. Aucune immobilité de plus de 2 s.

#### `Flux` — nœuds, liens, argent qui circule

Des nœuds reliés par des flèches, où l'argent circule en particules : du
versement vers l'enveloppe, de l'enveloppe vers les intérêts, des intérêts
vers l'enveloppe. Pour montrer un mécanisme : d'où vient l'argent, où il
s'accumule, ce qu'il produit. Un nœud est un pictogramme dans un cercle ; son
nom passe en overlay sur `noeud_k`, celui d'un flux sur `lien_k` (R7). Les
montants, eux, sont écrits dans la scène, sur leur lien.

**Pas de `donnees`** : la structure est dans `noeuds` et `liens`.

**Paramètres** :

| Paramètre | Obligatoire | Valeurs admises | Effet |
|---|---|---|---|
| `noeuds` | **oui** | `[{"icone": nom, "position": [x, y], "couleur": c}]` | Un nœud par entrée ; `node_1` est le premier. `icone` : la liste des pictogrammes de `Comparaison`. `position` en unités de scène, centre (0, 0) : x de −5,5 à 5,5, y de −2,4 à 1,8 ; sans position, les nœuds s'alignent de gauche à droite. `couleur` : celle du cercle (gris clair par défaut). |
| `liens` | **oui** | `[{"de": i, "vers": j, "couleur": c, "intensite": n, "courbure": a, "montant": v, "format": f}]` | Une flèche du nœud i vers le nœud j ; `link_1` est le premier. `intensite` (1 à 3) règle le débit visible des particules : un flux plus fort se voit plus dense. `courbure` (en radians, 1,0 conseillé) courbe le lien : deux liens opposés entre les mêmes nœuds, de même courbure, forment une boucle. `montant` est facultatif ; s'il est écrit, il vient des sources (R3), au `format` `"euro"` par défaut. |
| `mise_en_avant` | non | `{"liens": [k, …]}` | Ces liens s'affirment ; les autres et leurs particules s'estompent. |

**Éléments adressables dans `revelations`** :

| Élément | Type | Remarque |
|---|---|---|
| `node_k` | surgissement (1,5 s) | Le nœud apparaît sur son mot. |
| `link_k` | surgissement (1,5 s) | La flèche se trace de sa source à sa cible sur son mot ; son montant s'écrit au même instant. Puis l'argent y circule jusqu'à la fin du plan. Ses deux nœuds doivent déjà être là, ou arriver sur le même mot : le build signale un lien qui part avant eux. |
| `highlight` | surgissement (1,5 s) | Exige `mise_en_avant`. |

`Flux` n'a pas de cadre : le premier nœud est la première donnée (R5). Un nœud
et le lien qui y mène peuvent partager un mot : ils forment une seule
apparition. Tant qu'aucun lien n'est posé, l'écran ne vit que des
surgissements : moins de 4 s entre deux nœuds (R6). Dès qu'un lien est posé,
l'argent qui circule tient l'écran jusqu'à la fin.

**Exemple réel** — le plan pilote S12 de l'EP001c, validé à l'écran le
17/10/2026, qui remplace un b-roll sans overlay. L'analogie du jeu de société
en est le propos : la case départ est le versement fixe (bleu), les loyers
sont les intérêts (ambre). Aucun visuel de marque : pictogrammes génériques,
et le nom du jeu n'est écrit nulle part. Pas de montant : le script n'en
avance aucun.

```json
{
  "type_visuel": "manim",
  "manim_brief": {
    "composant": "Flux",
    "noeuds": [
      {"icone": "flag", "position": [-4.8, 0.2]},
      {"icone": "wallet", "position": [0.0, 0.2]},
      {"icone": "house", "position": [4.6, 1.35]},
      {"icone": "hotel", "position": [4.6, -1.45]}
    ],
    "liens": [
      {"de": 1, "vers": 2, "couleur": "CONTRIB", "intensite": 1},
      {"de": 3, "vers": 2, "couleur": "INTEREST", "intensite": 2},
      {"de": 4, "vers": 2, "couleur": "INTEREST", "intensite": 2}
    ],
    "mise_en_avant": {"liens": [2, 3]},
    "revelations": [
      {"element": "node_2", "t_rel_s": 1.95, "declencheur": "vous vivez"},
      {"element": "node_1", "t_rel_s": 3.97, "declencheur": "case départ. Puis"},
      {"element": "link_1", "t_rel_s": 3.97, "declencheur": "case départ. Puis"},
      {"element": "node_3", "t_rel_s": 6.11, "declencheur": "maisons"},
      {"element": "node_4", "t_rel_s": 7.08, "declencheur": "hôtels"},
      {"element": "link_2", "t_rel_s": 10.0, "declencheur": "loyers"},
      {"element": "link_3", "t_rel_s": 10.0, "declencheur": "loyers"},
      {"element": "highlight", "t_rel_s": 11.04, "declencheur": "plus que la case"}
    ]
  },
  "overlay_texte": [
    {"ancre": "noeud_2", "t_rel_s": 1.95, "texte_fr": "Vous", "declencheur": "vous vivez"},
    {"ancre": "noeud_1", "t_rel_s": 3.97, "texte_fr": "Case départ", "declencheur": "case départ. Puis"},
    {"ancre": "noeud_3", "t_rel_s": 6.11, "texte_fr": "Maisons", "declencheur": "maisons"},
    {"ancre": "noeud_4", "t_rel_s": 7.08, "texte_fr": "Hôtels", "declencheur": "hôtels"},
    {"ancre": "lien_2", "t_rel_s": 10.0, "texte_fr": "Loyers", "declencheur": "loyers"}
  ]
}
```

Ce que ça donne : « Vous » apparaît sur « vous vivez », la case départ et sa
flèche sur « case départ », et l'argent circule dès 5,47 s ; maisons et hôtels
surgissent sur leur mot ; les deux flux de loyers, plus denses, partent sur
« loyers » ; sur « plus que la case », ils s'affirment et la case départ
s'estompe. Plus longue immobilité : les 2 premières secondes (14,7 s figées
avant, en b-roll).

**Exemple exemplaire** — un mécanisme avec ses montants : versement,
enveloppe, intérêts qui y restent. **C'est celui-ci qu'il faut imiter.** Le
premier montant est dans la première phrase, sur le lien qui le porte ; chaque
nœud et chaque lien arrivent sur le mot qui les nomme ; la boucle
enveloppe ↔ intérêts est faite de deux liens opposés de même courbure. Les
`t_rel_s` sont des estimations (3,94 syllabes/s) que le recalage remplacera.

```json
{
  "vo_fr": "Chaque mois, vous versez deux cents euros sur votre livret. Ce livret, c'est l'enveloppe : il garde votre capital. Au bout d'un an, il produit cinquante-cinq euros d'intérêts. Et ces intérêts restent dans l'enveloppe : l'année suivante, ils rapportent à leur tour. C'est la capitalisation.",
  "type_visuel": "manim",
  "manim_brief": {
    "composant": "Flux",
    "noeuds": [
      {"icone": "hand-coins", "position": [-4.8, -0.2]},
      {"icone": "piggy-bank", "position": [0.0, -0.2]},
      {"icone": "sprout", "position": [4.6, -0.2]}
    ],
    "liens": [
      {"de": 1, "vers": 2, "couleur": "CONTRIB", "intensite": 1, "montant": 200},
      {"de": 2, "vers": 3, "couleur": "INTEREST", "intensite": 1, "courbure": 1.0, "montant": 55},
      {"de": 3, "vers": 2, "couleur": "INTEREST", "intensite": 2, "courbure": 1.0}
    ],
    "mise_en_avant": {"liens": [3]},
    "revelations": [
      {"element": "node_1", "t_rel_s": 0.76, "declencheur": "vous versez"},
      {"element": "node_2", "t_rel_s": 1.52, "declencheur": "deux cents euros"},
      {"element": "link_1", "t_rel_s": 1.52, "declencheur": "deux cents euros"},
      {"element": "node_3", "t_rel_s": 8.63, "declencheur": "cinquante-cinq euros"},
      {"element": "link_2", "t_rel_s": 8.63, "declencheur": "cinquante-cinq euros"},
      {"element": "link_3", "t_rel_s": 12.18, "declencheur": "restent dans l'enveloppe"},
      {"element": "highlight", "t_rel_s": 14.72, "declencheur": "rapportent à leur tour"}
    ]
  },
  "overlay_texte": [
    {"ancre": "noeud_1", "t_rel_s": 0.76, "texte_fr": "Versement mensuel", "declencheur": "vous versez"},
    {"ancre": "noeud_2", "t_rel_s": 4.31, "texte_fr": "Enveloppe", "declencheur": "c'est l'enveloppe"},
    {"ancre": "noeud_3", "t_rel_s": 8.63, "texte_fr": "Intérêts", "declencheur": "cinquante-cinq euros"}
  ]
}
```

Ce que ça donne : le versement apparaît sur « vous versez » ; l'enveloppe, la
flèche et « 200 € » sur « deux cents euros », et l'argent circule dès 3 s ;
les intérêts et « 55 € » sur « cinquante-cinq euros » ; le retour des intérêts
vers l'enveloppe ferme la boucle sur « restent dans l'enveloppe », et
s'affirme sur « rapportent à leur tour ». L'écran n'est jamais figé après la
première seconde.

### Pas encore disponible — ne pas utiliser

Tant qu'une famille ne figure pas dans la section *Disponibles*, un segment
qui la demande sera refusé.

- **Aires** (`Areas`, mode `aires`) — aires superposées depuis zéro
  (versements et capital, par exemple). En attente : le moteur le refuse.

### Héritage EP001 — ne pas utiliser

`BarRace`, `StackedBars`, `BarChart`, `StackedAreaChart`, `FunnelScatter`,
`BarStrip`, `Timeline`, et `LineChart` écrit avec des objets
(`{"cagr": …}`, `{"final": …}`) au lieu de tableaux de nombres. Ils
servent à reconstruire l'EP001 : ils écrivent des mots dans la scène et
dessinent un modèle d'épargne fixe (200 €/mois, 5 %/an). Ne les écris pas
dans un nouvel épisode. Attention à la confusion : la famille des barres
s'appelle `Bars`, pas `BarChart`.

---

## 5. Les plans de chaîne : `mention` et `ecran_fin`

Deux valeurs de `type_visuel` qui ne sont pas des familles : le moteur les
compose seul, à l'identique d'un épisode à l'autre. Seule la durée du segment
change, et la voix les cale. Un segment de ce type **ne porte ni
`manim_brief` ni `overlay_texte`** : `make check` et le build refusent
l'épisode sinon.

| `type_visuel` | Ce que le moteur pose |
|---|---|
| `mention` | La mention légale, centrée, en blanc cassé : « Contenu informatif et pédagogique. » puis « Ni conseil en investissement, ni recommandation personnalisée. ». La première ligne apparaît sur le premier mot de la voix, la seconde sur le mot « ni ». Rien d'autre : c'est une respiration. Si le plan dure encore plus de 4 s après la seconde ligne, le texte dérive très lentement (2 % d'échelle) pour que l'écran ne soit pas figé (R6). |
| `ecran_fin` | L'écran de fin de la chaîne. « Clair net enrichi » s'écrit en haut à gauche sur ces mots de la voix ; sur « abonnez-vous », un bouton d'abonnement dessiné (ni logo ni couleur de YouTube) s'enfonce, puis passe à « Abonné » avec une cloche. En fond, une courbe qui monte sous les zones, parcourue par un point, et des pictogrammes de `Flux` (pièces, pousse, hausse) qui dérivent loin des zones. |

**Durée de l'écran de fin** : celle de la voix, prolongée en silence jusqu'à
**20 s** au moins - la durée maximale des éléments de fin de YouTube. Le plan
s'anime pendant toute la prolongation : rien n'y est tenu figé.

**Zones réservées** (pixels 1920×1080, comme dans YouTube Studio), vides de tout
texte et de toute animation, sauf un contour pointillé pendant les 2 premières
secondes :

| Zone | Centre | Taille |
|---|---|---|
| Vidéo suggérée | (1340, 540) | 830 × 467 px |
| Abonnement | (480, 600) | cercle de 300 px |

À chaque build complet, `build/ecran_fin_zones.png` montre l'écran de fin dans
son état final, zones visibles et cotées : c'est le gabarit pour placer les
éléments dans YouTube Studio.

**Ce que la rédaction écrit** : le texte prononcé seulement. La mention doit
contenir le mot « ni » ; le texte du CTA, « Clair net enrichi » et
« abonnez-vous ». Sans ces mots, le moteur pose la ligne, le nom ou le bouton à
un instant par défaut.

**Musique de fin** (règle de chaîne, `video/musique_fin.py`, paramètres dans
`config/charte.json`, clé `musique_fin`) : le morceau de la charte
(`assets/musique/`) entre sous la voix du CTA, **3 s avant la fin de la voix**,
en fondu de 1,5 s, **au moins 20 dB sous la voix** de l'écran de fin, pour ne
jamais couvrir « Clair net enrichi » ni « abonnez-vous ». À la fin de la voix,
il remonte en 1 s jusqu'à **−20 LUFS** et s'y tient pendant la prolongation
silencieuse ; il sort en fondu de 2 s, nul sur la dernière image. Le silence
qui ouvre le morceau est sauté ; chaque niveau est calé sur la sonie du
passage du morceau qui tombe dans sa phase. Le morceau ne boucle jamais :
s'il est trop court, le build le signale. Le mixage se fait sur la piste
finale : l'image n'est pas rendue à nouveau.

**Mastering** (règle de chaîne, `video/mastering.py`, clé `mastering`) : un
gain global sur tout le mix amène l'épisode à **−14 LUFS** ; un limiteur
true-peak le tient sous **−1 dBTP**. Même gain pour la voix et la musique :
l'équilibre ne change pas. Les deux niveaux de la musique s'entendent dans la
vidéo livrée : celui de fin est corrigé du gain global, et l'écart sous la
voix est mesuré après le limiteur (qui rabote les crêtes de la voix) ; sous
20 dB, rien n'est produit. Sur l'EP001c : +3,10 dB de gain, limiteur sur
9,6 % des échantillons (plus de 1 dB sur 3,9 % du temps, 3,9 dB au plus).

### Les miniatures : `make miniature EP=…`

Règle de chaîne (`video/miniature.py`). Le moteur dessine les miniatures YouTube
aux couleurs et dans la police de la charte, une par variante de la section
**`## Miniatures`** de `metadonnees.md` (pour « Tester et comparer » de YouTube
Studio). Sorties dans `build/miniatures/` : 1280×720, version 168×94 (mobile),
planche côte à côte.

**Ce que la rédaction écrit** (exemple réel : EP001c) :

```
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
```

` / ` change de ligne ; `==…==` met la ligne dans un bloc incliné (ambre, ou
blanc si un mot est déjà en ambre) ; `{…}` écrit en ambre (ce que le capital
verse), `[…]` en bleu (ce que vous versez). Le texte s'affiche en capitales.

| Famille | Ce que le moteur pose |
|---|---|
| `chiffre` | Un chiffre géant ambre, son texte à droite ; deux barres (années de bascule calculées) et l'écart entre elles, fléché. Le chiffre **doit** être cet écart. |
| `contraste` | Cumul versé (bleu) et capital (ambre) qui divergent, l'aire entre les deux remplie, la courbe haute fléchée vers le haut du cadre. |
| `bascule` | Versements de l'année (ligne bleue) croisés par les intérêts de l'année (ambre) ; impact lumineux au croisement réel. |

**Le texte** : une phrase qui accroche, **6 mots au plus**, un seul chiffre
géant ; racoleur permis, mensonge interdit. Ni lexique interdit, ni promesse de
gain : un fait du calcul (« quand tes intérêts dépassent tes versements »),
pas une promesse (« tu gagnes plus que… »). Cohérent avec le titre retenu, sans
le recopier mot pour mot.

**Contrôles** (le moteur refuse sinon) : 1280×720, PNG sous 2 Mo ; coin
inférieur droit (200×76 px, où YouTube affiche la durée) laissé au fond ;
mots, chiffre géant et lexique comptés ; hauteur de capitale d'au moins 7 px en
168×94 ; contraste WCAG d'au moins 4,5:1 ; données recalculées avec la
convention 9A de `recherche.md`, et tout nombre affiché présent dans
`recherche.md`.

---

## 6. Avant de rendre un `manim_brief`, vérifie

1. `composant` est une famille *disponible*.
2. Les paramètres obligatoires sont présents : `interpolation` pour
   `LineChart`, `mode` pour `Bars` et `Areas`, `borne` pour une bande à une
   seule valeur, `axes.unite_y` pour ces trois familles, `unite` pour
   `Comparaison`, `noeuds` et `liens` pour `Flux`.
3. Chaque valeur que la voix énonce a sa révélation (`series_k_point_j`,
   `bar_g`, `band_g`, `value_g`, `link_k`…) sur le mot qui l'énonce ; un
   nombre de pictogrammes, sur le mot qui énonce ce nombre (`pictos_k`).
4. Barres, bandes et jauges : chaque catégorie de `donnees` est mentionnée
   par la voix et a sa révélation ; aucune catégorie muette. Un lien de
   `Flux` ne part pas avant ses deux nœuds.
5. Chaque `declencheur` recopie `vo_fr` mot pour mot et n'y apparaît qu'une
   fois.
6. Aucun nombre à l'écran n'est calculé : chaque valeur écrite est dans
   `donnees` ou dans un paramètre, et dans les sources.
7. La première révélation de donnée tombe avant ~4,5 s.
8. Aucun intervalle entre deux révélations ne laisse l'écran figé plus de
   4 s.
9. Aucune révélation pour le cadre, et aucun mot dans la scène : les noms
   des options et des nœuds passent par `option_k`, `noeud_k`, `lien_k`.
10. Chaque pictogramme est dans la liste du catalogue.
