# Le montage vidéo

La skill Cowork produit le script, la voix et les métadonnées. Ce dossier prend
le relais sur votre machine et fabrique la vidéo. C'est l'étape que la skill
annonce par `make video EP=EPxxx`.

## Lancer un montage

`make` n'est pas installé sur cette machine. La commande directe :

```bash
python video/build.py --ep EP001
```

Les autres formes utiles :

| Ce que vous voulez | Commande |
|---|---|
| Le montage complet, 1920×1080 | `python video/build.py --ep EP001` |
| Vérifier vite, en 960×540 | `python video/build.py --ep EP001 --preview` |
| Retravailler un seul plan | `python video/build.py --ep EP001 --only S07 --preview` |
| Remonter sans refaire les rendus | `python video/build.py --ep EP001 --skip-render` |

Un `Makefile` et un `make.cmd` sont là si vous préférez la commande de la skill.
Le `.cmd` marche dans l'invite de commandes (`make video EP=EP001`) ; dans
PowerShell il faut écrire `.\make.cmd video EP=EP001`, parce que PowerShell ne
cherche pas les exécutables dans le dossier courant.

## Ce que ça produit

```
episodes/EP001/video/
├── EP001.mp4          la vidéo, H.264 + AAC, prête pour YouTube
├── EP001.srt          les sous-titres, à téléverser avec la vidéo
├── voix.wav           la voix des 28 segments bout à bout
├── plans/             un rendu Manim par segment
└── plans_cales/       les mêmes, recadrés à la durée exacte de leur voix
```

Les deux derniers dossiers ne servent qu'à `--skip-render`. On peut les effacer.

## Comment c'est construit

**La voix commande.** La durée d'un plan est celle de son fichier audio, lue
dans `audio/durations.json`. Le rendu est ensuite recalé à la milliseconde :
si l'animation finit avant, la dernière image est prolongée ; si elle déborde,
elle est coupée. C'est pour ça que l'écart image/son du montage final est nul.

**Un segment, un plan.** L'identifiant `Sxx` est la clé de jointure entre le
script, l'audio et la vidéo. C'est la raison pour laquelle la skill interdit de
renuméroter les segments après la phase 2.

**Quatre registres visuels**, selon `type_visuel` :

- `manim` — un graphe, choisi par `manim_brief.composant`. Huit composants sont
  implémentés dans `components.py`.
- `typo_cinetique` — le texte des overlays en grand, seul à l'écran.
- `fond_anime` — un champ de points en dérive lente.
- `broll` — des bandes d'horizon en parallaxe. **Ce ne sont pas des rushes :**
  la chaîne est faceless et le dossier ne contient aucune banque d'images. Si
  vous achetez des plans de stock un jour, c'est `ambience_horizon()` dans
  `scenes.py` qu'il faudra remplacer.

**Les overlays sont joués à l'heure dite.** Un texte posé à `t_rel_s: 3.0`
apparaît à 3 secondes, même si un balayage de barres court encore. Chaque repère
devient une voie `Succession(Wait(départ), animation)` et toutes les voies
partent ensemble : voir `SegmentScene.run_cues()`.

## Les apparitions échelonnées

Un composant ne pose pas son contenu d'un bloc. Il déclare ses **parties** —
une année de barres, une courbe, une aire, un jalon — et les confie à un
`Reveal`, qui donne à chacune son top de départ. Sans rien demander, chaque
composant garde sa cadence propre : les briefs déjà écrits se rendent à
l'identique.

Le script reprend la main plan par plan avec la clé facultative
`manim_brief.reveals`. Quatre écritures, au choix :

| Ce que vous voulez | Ce que vous écrivez |
|---|---|
| Des tops, dans l'ordre d'entrée | `"reveals": [1.6, 8.0, 13.0]` |
| Une partie précise, les autres suivent | `"reveals": [{"target": "gross_return", "at": 8.0}]` |
| Une cadence régulière | `"reveals": {"start": 1.4, "step": 2.2}` |
| Tout au même instant | `"reveals": "together"` |

Une entrée nommée accepte aussi `"run_time"`, pour allonger ou raccourcir
l'entrée de cette partie-là. Les parties non citées gardent leur top par
défaut, et celles qui suivent la dernière partie citée se recalent derrière
elle : repousser une courbe repousse ce qui vient après, pas seulement elle.

Les noms de parties, par composant :

| Composant | Parties, dans l'ordre d'entrée |
|---|---|
| `BarRace` | `year_1`…`year_n`, puis `crossover` — ou `cut` et `note` quand la bascule est coupée |
| `StackedBars` | `year_1`…`year_n` |
| `LineChart` | le nom de série du brief (`price_only`, `gross_return`, `uninterrupted`…), puis `values` |
| `BarChart` | `bar_1`, `bar_2`, puis `gap` (S08), `ring` (S12) ou `reference` (S15) |
| `StackedAreaChart` | `contributions`, `interest`, `boundary`, `half` |
| `FunnelScatter` | `envelope`, `cloud`, `point_1`…`point_n` |
| `BarStrip` | `strip_1`…`strip_k`, `tag` — la liste décide du nombre de tranches |
| `Timeline` | `mark_1`…`mark_n` |

Ces noms partent dans le `manim_brief` : ils sont en anglais et sans accent,
comme le reste du brief.

Deux garde-fous, parce que la voix commande. Un top qui déborde de la durée du
plan est ramené à l'intérieur. Un jalon de frise qui n'aurait plus la place
d'être lu est abandonné, pas tassé contre la fin — avec son libellé.

Enfin, les repères dérivés se calculent sur les tops réellement retenus : le
trait de bascule de `BarRace` tombe sur la barre qui bascule, le jalon
« moitié-moitié » de `StackedAreaChart` tombe quand la frontière atteint
l'année. Décaler la partie qui les porte les décale avec elle.

## Les chiffres à l'écran

Règle : **ce qui est écrit vient du script**, jamais du modèle.

`plotting.py` contient un modèle d'épargne (200 €/mois, 5 %/an) qui sert à
dessiner la *silhouette* des courbes. Il est ensuite recalé pour passer
exactement par les points du `manim_brief` — année 1 : 55 €, année 40 :
14 057 €. L'écart avec le modèle brut est d'environ 5 % : la forme ne bouge pas,
mais un spectateur qui lit un chiffre à l'écran entend le même à la voix.

Deux conséquences visibles :

- Les graphes dont le script n'énonce aucun montant n'ont **pas de valeurs sur
  l'axe** — le hook, notamment, dit que l'année de bascule ne dépend pas de la
  somme versée ; y afficher des montants irait contre le propos.
- Les enveloppes purement illustratives (la dispersion de `FunnelScatter`, les
  168 barres de `BarStrip`) ne portent aucun chiffre. Seuls les points sourcés
  en portent.

## Les sous-titres

Ils sont calés sur `audio/alignments/Sxx.json`, l'alignement caractère par
caractère renvoyé par ElevenLabs — pas sur une répartition au prorata des mots.
Les balises de jeu (`[curious]`, `[thoughtful]`) sont retirées : elles figurent
dans le texte envoyé à l'API mais ne sont pas prononcées.

Le fichier n'est pas incrusté dans l'image. Téléversez-le à part sur YouTube :
les sous-titres restent alors cherchables et traduisibles.

## Ajouter un composant

1. Écrire la fonction dans `components.py`. Elle reçoit `(seg, cues)` et
   dépose ses objets fixes avec `cues.add(...)`.
2. Nommer ses parties dans un `Reveal`, puis poser chaque animation avec
   `rev.at("nom_de_partie", animation)` — jamais tout sur un même repère. Elle
   ne joue rien elle-même.
3. L'inscrire dans le dictionnaire `COMPONENTS` en bas du fichier.
4. Le nom de la clé est celui que le script écrira dans `manim_brief.composant`,
   et les noms de parties ceux qu'il écrira dans `manim_brief.reveals`.

La charte — couleurs, tailles, marges — est dans `style.py`, et seulement là.
Le bleu porte ce que vous versez, l'ambre ce que le capital vous verse : c'est
l'opposition centrale de la chaîne, et le couple reste lisible en deutéranopie
et en protanopie.

## Deux pièges Manim, si vous modifiez le code

- **`FadeOut` sur un objet pas encore introduit le fait apparaître à la première
  image.** Manim ajoute à la scène les objets des animations qui ne sont pas des
  « introducers ». Posez l'objet à l'avance avec une opacité nulle.
- **Deux `.animate` sur le même objet se partagent l'attribut `target`** : le
  second écrase la cible du premier, et le premier ne fait plus rien. Utilisez
  `Transform(m, m.copy().set_...)`, comme `_opacity()` dans `scenes.py`.
