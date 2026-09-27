# EP001 — Métadonnées YouTube

Sujet : les intérêts composés · Public : néophyte en investissement et finances personnelles
Audio généré le 10 août 2026 · Durée réelle **8 min 35 s** (515,0 s) · 28 segments

---

## Titre retenu

**L'année où votre argent gagne plus que vous n'épargnez**

### Alternatives

- Intérêts composés : la date qui ne dépend pas de votre salaire
- 96 000 euros versés, 296 000 euros à l'arrivée : comment
- Intérêts composés : la seule chose à comprendre pour débuter

## Texte de miniature

**L'année de la bascule**

Consigne visuelle : deux colonnes de hauteur inégale sur un axe de temps, sans chiffre lisible, et le repère de croisement laissé hors cadre. Le nom de la chaîne n'apparaît pas sur la miniature.

---

## Description YouTube

Il existe une année où votre argent vous rapporte plus, en douze mois, que ce que vous y avez versé pendant ces douze mois. Cette année a un numéro — et il ne dépend pas de la somme que vous mettez de côté.

Épisode pour débuter : d'où vient réellement la puissance des intérêts composés, à quoi ressemble la courbe pendant les cinq premières années, et pourquoi le nombre d'années compte davantage que le montant. Tous les chiffres sont sourcés et les simulations sont annoncées comme telles.

Sources citées à l'écran : AMF, Euronext, Banque de France, INSEE, ACPR, Service Public.

**Chapitres**

```
0:00  L'année dont personne ne parle
0:45  D'où vient vraiment la puissance
3:04  La forme du chemin : les premières années
3:57  Le moment où les intérêts prennent le dessus
5:25  Les deux questions honnêtes
7:41  La bascule
```

Ce contenu est informatif et pédagogique. Il ne constitue ni un conseil en investissement ni une recommandation personnalisée. Les performances passées ne sont pas un indicateur fiable des résultats futurs. Les chiffres présentés sont des hypothèses de calcul.

Clair net enrichi

---

## Timecodes des mid-rolls

Calculés sur les durées audio réelles, non sur l'estimation.

| Mid-roll | Timecode | Fin de segment | Amorce |
|---|---|---|---|
| 1 | **3:04** | S11, fin d'acte 1 | « c'est la forme qui explique pourquoi tant de gens abandonnent avant d'arriver à l'année qui nous intéresse » |
| 2 | **5:25** | S19, fin d'acte 2 | « qu'est-ce qui peut déplacer la fameuse année ? » |
| 3 | **7:41** | S25, fin d'acte 3 | « Ce qui nous ramène à la question du début. » |

Condition de monétisation remplie : la vidéo fait **8 min 35 s**, soit 35 s au-dessus du seuil de 8 minutes qui débloque les coupures intermédiaires, et 15 s au-dessus de la borne basse de la cible chaîne (8 min 20 s).

## Tags

```
intérêts composés, épargne, débuter en bourse, finances personnelles, investir,
liberté financière, PEA, assurance-vie, Livret A, dividendes, CAC 40, ETF,
éducation financière, AMF, capitalisation
```

## Mention légale

À afficher à l'écran pendant tout le segment S28, et reprise en description :

> Ce contenu est informatif et pédagogique. Il ne constitue ni un conseil en investissement ni une recommandation personnalisée.

Complément aligné sur le libellé réglementaire (article 44.4 d du règlement délégué UE 2017/565) : « les performances passées ne sont pas un indicateur fiable des résultats futurs ». C'est la formulation du texte, et non l'usage de place « ne préjugent pas ».

---

## Paramètres techniques de la voix off

| Paramètre | Valeur | Remarque |
|---|---|---|
| Voix | Antoine — Audiobook Narrator (fr) | `1a3lMdKLUcfcMtvN772u` |
| Modèle | `eleven_v3` | |
| Stability | `0.5` | L'API refuse la valeur textuelle « natural » |
| Format source | `mp3_44100_192` | `pcm_44100` est réservé au palier Pro sur ce compte |
| Livrable | WAV 44,1 kHz mono 16 bits | conversion ffmpeg |
| Conditionnement | **absent** | `eleven_v3` refuse `previous_text` / `next_text` (HTTP 400). Arbitrage validé : on conserve les 27 balises de direction de lecture, que `multilingual_v2` vocaliserait au lieu de les interpréter. |
| Débit mesuré | 190,3 mots/minute | contre 155 en référence dans la skill : c'est ce qui a imposé d'allonger le script |

## Écarts assumés par rapport à la skill

1. **Volume de mots : 1 555 au lieu de 1 320 ± 40.** À 190,3 mots/minute, les 1 320 mots de référence donnaient 7 min 13 s d'audio, sous le seuil de monétisation. Les bornes par bloc ont été recalibrées du facteur 190,3 / 155, ce qui restitue les fenêtres visées par la skill : hook de 14,4 s pour une cible de 0:00–0:20, tension jusqu'à 0:45 pour une cible de 0:50. Arbitrage validé, la contrainte des 8 minutes primant sur le volume.
2. **Pas de conditionnement de prosodie entre segments** — voir le tableau ci-dessus.
3. **Vérification à l'écoute : faite, sur un échantillon ciblé.** La skill prévoit une écoute des trois premiers segments avant de lancer le reste ; ne pouvant pas écouter, j'ai généré les 28 segments après vérification mécanique (alignement caractère par caractère identique au texte envoyé, nombres et sigles vocalisés sous leur forme développée), puis soumis à l'écoute les trois segments les plus chargés en nombres et sigles plutôt que les trois premiers — ce qui correspond à l'intention du contrôle.

   **Validé par Mayane le 10 août 2026** sur S07 (« CAC quarante », « cinq virgule cinquante-deux pour cent »), S20 (« AMF », « quatre-vingt-dix-neuf pour cent ») et S24 (« un virgule soixante-dix pour cent »). Les 25 autres segments n'ont pas été écoutés individuellement ; ils ne contiennent aucune forme numérique ou sigle absent de ces trois-là.

   Statut de l'épisode : **bon pour le montage**.
