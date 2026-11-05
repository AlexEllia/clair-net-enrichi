# Clair Net Enrichi : identité de chaîne

Logo : **la pièce frappée**. Un sablier ouvert, d'où sort une pousse, gravé sur
une pièce : le temps (sablier), la croissance (pousse), la liberté (le sablier
n'a plus de couvercle) et l'argent (la pièce).

## Couleurs

| Rôle | Hex | Où |
|---|---|---|
| Pièce | `#F2B33D` ambre | fond de la pièce ; ce que le capital rapporte |
| Gravure | `#5B8DEF` bleu ardoise | sablier et pousse ; ce que l'on verse |
| Cercle | `#0F1319` encre | cercle intérieur de la pièce, bord de l'avatar |
| Fond | `#0F1319` encre, `#161C25` en haut des fonds | bannière, avatar |
| Texte | `#F4F6F8` (nom), `#C8D0DA` (signature) | bannière, logo + nom |
| Grille | `#232C38` | bannière |

La couleur de perte `#E2725B` et la sarcelle `#3FC0A5` n'entrent pas dans le logo.

Relief de la pièce : des teintes tirées de l'ambre, `#F7D18B` (lumière),
`#A97D2B` (ombre), `#795A1E` (tranche), `#D59E36` et `#F5C468` (creux du
centre). Toutes les versions couleur (avatar, bannière, filigrane, logos) portent
la même pièce en relief ; `logo_couleur_aplat` et les monochromes restent en aplat.

Contraste : la gravure bleue sur l'ambre n'a que 1,74:1 (les deux teintes ont
presque la même clarté). Elle reste lisible en couleur jusqu'à 16 px, mais
s'efface en niveaux de gris : pour une impression en noir et blanc ou un fond
chargé, utiliser une version monochrome.

## Polices

- **Selawik Bold** : le nom « Clair Net Enrichi » (trois majuscules). **Selawik Semibold** : le sous-titre.
  Selawik (Microsoft, licence SIL OFL 1.1, dans `polices/`) est l'équivalent
  libre de Segoe UI, aux mêmes métriques. Elle n'a pas de crénage : l'espacement
  est celui dessiné par la police.
- Dans les SVG, tout le texte est vectorisé en tracés : aucune police n'est
  nécessaire pour les ouvrir. Les polices ne servent qu'à composer un nouveau texte.
- Les vidéos gardent Segoe UI (charte des animations, `video/style.py`).

## Fichiers et usages

| Fichier | Usage |
|---|---|
| `youtube/avatar_800x800` | photo de profil, pièce en relief ; YouTube la recadre en rond et l'affiche en 98 px |
| `youtube/banniere_2560x1440` | bannière, sous-titre « Faites travailler votre argent. Pas l'inverse. » ; texte et logo dans la zone sûre 1546 × 423 |
| `youtube/filigrane_150x150` | filigrane de marque des vidéos, pièce en relief ; fond transparent |
| `logo/logo_blanc` | écran de fin, miniatures, tout fond sombre ou photo |
| `logo/logo_noir` | fonds clairs, impression en noir et blanc |
| `logo/logo_couleur` | logo maître, pièce en relief, fond transparent |
| `logo/logo_couleur_aplat` | même pièce sans relief : impression, très petites tailles |
| `logo/logo_nom_fond_sombre`, `logo/logo_nom_blanc` | logo et nom côte à côte |
| `controles/` | zones sûres superposées aux exports, et le rapport des mesures |

Chaque visuel existe en SVG (maître, vectoriel) et en PNG.

## Règles

- Ne pas déformer, recolorer, ombrer ni encadrer le logo : YouTube déconseille
  aussi ombres, bordures et cadres autour de la bannière. Le relief fait partie
  de la pièce : il ne s'ajoute pas à un autre visuel.
- Laisser autour du logo un espace libre d'au moins un quart de son diamètre.
- En dessous de 32 px, préférer la version couleur ou blanche, jamais le logo et le nom.
- Le croisement des courbes de la bannière (bleu, puis ambre au-dessus) est la
  signature de la chaîne : le moment où les intérêts dépassent les versements.

Fichiers régénérés par `python identite/declinaisons.py` (géométrie dans `identite/logo.py`).
