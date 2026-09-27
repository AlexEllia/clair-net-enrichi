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
`bar_g` pour une barre, `band_g` pour une bande), calée sur le mot qui
l'énonce (section 2). Sinon le visuel n'illustre rien.

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

**R7 — Pas de mots dans la scène.** Le graphe n'écrit que des chiffres et
les symboles € et %. Tout mot passe par `overlay_texte` : titre, titres
d'axes, légendes, source (section 3).

**R8 — Le cadre n'est pas une révélation.** N'écris pas de révélation pour
le cadre, la grille ou les axes : ils se construisent seuls avant la
première donnée.

**R9 — Pas de catégorie muette.** Sur une famille à catégories distinctes
— `Bars`, `Areas` en bandes —, chaque ligne de `donnees` est une catégorie
que la voix mentionne, et elle a sa révélation. Une catégorie que la voix ne
mentionne pas ne figure pas dans `donnees` : elle s'afficherait pendant que
la voix parle d'autre chose. Les courbes, elles, gardent leurs points
intermédiaires : ils sont sur le chemin du tracé. Le build signale toute
barre ou bande sans révélation.

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

- `axe_x`, `axe_y` et `titre_haut` : poser à ~0,6 s.
- Une légende : poser juste après la première révélation de sa série.
- Les titres d'axes commencent par une majuscule.

---

## 4. Les familles

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

**Une barre qui monte est un tracé** : sa croissance dure jusqu'à 6 s et se
planifie à rebours depuis son mot. La barre suivante commence donc à monter
pendant que la voix parle encore de la précédente — c'est ce qui donne son
rythme au plan. Tu n'as rien à prévoir pour cela : cale chaque barre sur le
mot qui énonce sa valeur.

Une seule barre monte à la fois. Entre deux valeurs énoncées, laisse au
moins 0,7 s. Mise en avant, repère et annotation, eux, surgissent en 1,5 s
sur leur mot. Une catégorie que la voix ne mentionne pas n'a pas sa place
dans `donnees` (R9).

**Exemple réel** — le plan S17 de l'EP001b, validé à l'écran, réécrit dans ce
format. Il est vrai mais **pas exemplaire** : la première valeur n'est
lisible qu'à 9,82 s, contre R5, parce que la phrase d'ouverture (« Une seule
chose déplace la bascule : le rendement. ») ne porte aucun chiffre.

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
« quarante-deuxième » ; la barre 3 commence à monter à 15,73 s, pendant que
la voix parle encore des fonds en euros, et atteint 15 sur « quinzième ».
Les 8,57 s entre `bar_2` et `bar_3` restent vivantes parce que la barre 3
les comble (R6).

**Exemple exemplaire** — le même propos, écrit pour respecter toutes les
règles. **C'est celui-ci qu'il faut imiter.** La première phrase porte la
première valeur ; chaque année de bascule a sa révélation sur le mot qui
l'énonce ; la définition des fonds en euros précède leur valeur, si bien que
la barre suivante monte pendant qu'on l'explique. Les `t_rel_s` sont des
estimations (165 mots/min) que le recalage remplacera.

```json
{
  "vo_fr": "Au Livret A, la bascule n'arrive que la quarante-deuxième année, à un virgule sept pour cent. Aux fonds en euros, la partie garantie de l'assurance-vie, c'est la vingt-huitième, à deux virgule six pour cent en 2025. À cinq pour cent, la quinzième. À huit virgule huit, la neuvième. Une seule chose déplace la bascule : le rendement.",
  "type_visuel": "manim",
  "manim_brief": {
    "composant": "Bars",
    "mode": "simple",
    "donnees": [[1.7, 42], [2.6, 28], [5.0, 15], [8.81, 9]],
    "axes": {"unite_x": "percent_per_year", "unite_y": "years"},
    "couleurs": ["INTEREST"],
    "revelations": [
      {"element": "bar_1", "t_rel_s": 2.91, "declencheur": "quarante-deuxième"},
      {"element": "bar_2", "t_rel_s": 9.82, "declencheur": "vingt-huitième"},
      {"element": "bar_3", "t_rel_s": 14.91, "declencheur": "quinzième"},
      {"element": "bar_4", "t_rel_s": 17.09, "declencheur": "neuvième"}
    ]
  },
  "overlay_texte": [
    {"ancre": "titre_haut", "t_rel_s": 0.6, "texte_fr": "Année de bascule selon le rendement"},
    {"ancre": "axe_x", "t_rel_s": 0.6, "texte_fr": "Rendement net annuel"},
    {"ancre": "axe_y", "t_rel_s": 0.6, "texte_fr": "Année de bascule"}
  ]
}
```

Ce que ça donne : le cadre se pose en 1 s ; la barre 1 monte de 1,2 s à
2,91 s et « 42 » apparaît sur « quarante-deuxième » ; la barre 2 monte
pendant « Aux fonds en euros, la partie garantie de l'assurance-vie » et
atteint 28 sur « vingt-huitième » ; les barres 3 et 4 suivent. L'écran n'est
jamais figé plus de 0,6 s entre deux barres.

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

## 5. Avant de rendre un `manim_brief`, vérifie

1. `composant` est une famille *disponible*.
2. Les paramètres obligatoires sont présents : `interpolation` pour
   `LineChart`, `mode` pour `Bars` et `Areas`, `borne` pour une bande à une
   seule valeur, `axes.unite_y` partout.
3. Chaque valeur que la voix énonce a sa révélation (`series_k_point_j`,
   `bar_g`, `band_g`…) sur le mot qui l'énonce.
4. Barres et bandes : chaque catégorie de `donnees` est mentionnée par la
   voix et a sa révélation ; aucune catégorie muette.
5. Chaque `declencheur` recopie `vo_fr` mot pour mot et n'y apparaît qu'une
   fois.
6. Aucun nombre à l'écran n'est calculé : chaque valeur écrite est dans
   `donnees` ou dans un paramètre, et dans les sources.
7. La première révélation de donnée tombe avant ~4,5 s.
8. Aucun intervalle entre deux révélations ne laisse l'écran figé plus de
   4 s.
9. Aucune révélation pour le cadre, et aucun mot dans la scène.
