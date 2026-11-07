# Personnage et animation

> Photo du personnage, références d'animation, ce que fait le perso selon l'état.

## Fichiers fournis par Hugo

- `assets/mascot-poster.png` : visuel fixe du personnage (1122×1402, portrait 4:5).
- `assets/mascot-apparition.mp4` : animation d'apparition (H.264, 1122×1402, 30 fps, 4,5 s, sans son).

## Le personnage

- Boule bleue texturée (bleu roi, aspect un peu usé et granuleux).
- Les yeux sont deux touches de clavier crème : à gauche **« tab → »**, à droite **« ● H »**.
- Anneau doré lumineux en orbite, qui descend en spirale sous le perso.
- Étoiles bleues (sparkles) et deux petits traits « d'attention » en haut à droite.
- Ombre dorée au sol : le perso flotte.
- Fond crème clair, halo chaud autour du perso.

## Ce que fait l'animation d'apparition (observé)

| Temps | Ce qui se passe |
|-------|-----------------|
| 0 → ~0,6 s | Le perso apparaît en fondu en grossissant depuis le centre, puis passe légèrement au-dessus de sa taille finale. |
| ~0,6 → ~1,2 s | Il se stabilise à sa taille finale, avec un léger halo ou une onde lumineuse circulaire autour. |
| ~1,2 → 4,5 s | Quasi immobile (léger mouvement de lueur et de flottement). |

## Questions ouvertes

- Raccourci : les yeux « tab » + « H », ça veut dire que le raccourci est **Tab + H** ?
- Le fond de la vidéo est crème et opaque. Pour faire apparaître le perso par-dessus une page, il faut une version à fond transparent (WebM avec alpha, séquence PNG ou Lottie), ou alors une interface entièrement sur fond crème.
- Autres états (écoute, réflexion, parle, demande de confirmation, disparition) : il y a des animations prévues, ou je les crée en code à partir du visuel fixe ?
- Après l'apparition, la vidéo doit-elle boucler sur la partie « flottement » ?
