# Démo

> Écran et machine de démo, échéance, scénario exact du pitch, plan B si le réseau lâche.

## Cadre

- Échéance (date/heure du pitch) :
- Durée de la démo :
- Machine et écran (PC de qui ? projecteur ?) :
- Navigateur : Chrome
- Réseau (wifi du lieu ? partage de connexion en secours ?) :

## Ce qui doit marcher à coup sûr

1. Brainy installé en app, appelé avec la touche **H**.
2. Scénario Sarah (Doctolib) de bout en bout, avec confirmation orale avant de réserver.

Bonus si le cœur marche : mot « Brainy », extension Chrome.

## Scénario retenu : la charge mentale de Sarah

Sarah, maman de 4 enfants, rentre de l'école à 18h45. Elle a en tête un dermato pour elle et le dentiste pour Léo (l'aîné) et Inès (la 3e), alors que les enfants réclament le dîner. Elle délègue tout à Brainy à l'oral, va cuisiner, et ne revient que pour dire « oui ». Le cœur du pitch : Brainy gère les petites conditions (samedi, après l'école, à la suite, près de la maison, jour férié).

Écrans : `maquettes/v5-demo-sarah/`. Dates du storyboard : soir du lundi 9 novembre (à caler sur le jour du pitch). Médecins et créneaux fictifs.

| # | Écran | Sarah dit / fait | Brainy dit (oral + texte) | Côté technique |
|---|-------|------------------|---------------------------|----------------|
| 1 | Repos | Ouvre Brainy | « Bonsoir Sarah » (texte) | Front |
| 2 | Écoute | Appuie sur H : « Il me faut un dermato pour moi, un samedi de préférence parce qu'en semaine je bosse. Et le dentiste pour Léo et Inès, le mercredi après-midi vu qu'ils n'ont pas école, l'un après l'autre si possible. Pas trop loin de la maison. » | (transcription en direct) | Gladia |
| 3 | To-do | | « C'est noté, 2 rendez-vous. Je m'en occupe, va faire à manger, je te préviens dès que j'ai trouvé. » | Back (découpe en tâches + conditions) |
| 4 | L'agent travaille | (cuisine) | Étapes en direct : samedi 14 complet, mercredi 11 férié… | Agent H Company sur Doctolib |
| 5 | Trouvé | | « Sarah, j'ai trouvé ! Ce samedi était complet, donc je t'ai pris le suivant. Et comme mercredi 11 est férié, les enfants passent le 18. » | Agent H |
| 6 | Confirmation | | « Je réserve les 3 rendez-vous ? Le dermato samedi 21 à 10h30, et le dentiste mercredi 18 : Léo à 14h, Inès à 14h30. » | Back |
| 7 | Réservation | « Oui, parfait, merci ! » | « Je réserve. » | Agent H |
| 8 | C'est fait | | « C'est fait ! Les 3 rendez-vous sont réservés et dans ton agenda. Je te les rappellerai la veille. Bon appétit ! » | Agent H |
| 9 | Historique | Clique sur l'historique | | Front |

Plan B (écran 10) : pas deux créneaux à la suite le mercredi : « Soit Léo à 14h et Inès à 16h, soit les deux à la suite samedi 21, juste avant ton dermato. Tu préfères ? »

Ancien scénario (billet SNCF) gardé en réserve : `maquettes/v3-sncf/`.

## Plan B

- Si l'agent H est lent ou plante :
- Si le réseau lâche :
- Si le micro capte mal dans la salle :
