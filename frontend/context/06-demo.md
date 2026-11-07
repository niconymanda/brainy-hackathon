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
2. Scénario train de bout en bout, avec confirmation orale avant paiement.

Bonus si le cœur marche : mot « Brainy », extension Chrome.

## Scénario, étape par étape

Écrans : `maquettes/v3-sncf/` (storyboard + un PNG par écran). Dates : jeudi 12 novembre (à ajuster au jour du pitch). Prix et horaires fictifs pour les maquettes.

| # | Écran | Utilisateur dit / fait | Brainy dit (oral + texte) | Côté technique |
|---|-------|------------------------|---------------------------|----------------|
| 1 | Repos | Ouvre Brainy | « Salut, je suis Brainy » (texte) | Front |
| 2 | Écoute | Appuie sur H : « Réserve-moi un billet SNCF pour jeudi, en fin d'après-midi, entre 17h et 22h, pour aller voir mon père. Pas plus de 80 €. » | (transcription en direct) | Gladia |
| 3 | Reformule et demande | | « OK : jeudi 12 novembre, départ entre 17h et 22h, 80 € maximum. Tu pars d'où, et ton père habite où ? » | Back |
| 4 | Tu réponds | « Je pars de Paris, il habite à Lyon. » | | Gladia |
| 5 | L'agent travaille | | « Je m'en occupe, ça prend quelques secondes. » Étapes cochées en direct. | Agent H Company |
| 6 | Résultat | | « J'ai trouvé 7 trains. Le moins cher part à 19h04 et coûte 29 €. » | Agent H |
| 7 | Confirmation | | « Je m'apprête à payer 29 € avec ta carte enregistrée. C'est bon pour toi ? » | Back |
| 8 | Paiement | « Ouais carré, tu peux prendre. » | « Parfait, je paie. » | Agent H |
| 9 | C'est réservé | | « C'est réservé ! Jeudi 19h04, voiture 7, place 42. Ton billet est dans tes mails. Bon voyage chez ton père ! » | Agent H |
| 10 | Historique | Clique sur l'historique | | Front |

Variante plan B (écran 11) : « Je n'ai rien trouvé sous 80 € entre 17h et 22h. Le moins cher est à 89 €, ou il y a un train à 22h34 pour 45 €. Je fais quoi ? »

Question ouverte : l'étape 3-4 (demander le départ et l'arrivée) peut sauter si on dit tout dans la première phrase (« … pour aller voir mon père à Lyon, depuis Paris »). Plus court pour le pitch, mais montre moins le dialogue.

## Plan B

- Si l'agent H est lent ou plante :
- Si le réseau lâche :
- Si le micro capte mal dans la salle :
