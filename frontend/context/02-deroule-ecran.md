# Déroulé à l'écran

> Étape par étape : touche, apparition, écoute, réflexion, réponse vocale, confirmation, fin. Pour chaque étape : ce que fait le perso, ce qu'on voit (texte transcrit, taille, position).

## Déclenchement (décidé)

- **Touche H** dans l'onglet/app Brainy : déclencheur principal, celui de la démo.
- **Mot « Brainy » à la voix** : bonus, même déclencheur. Moteur recommandé : Picovoice Porcupine (mot d'activation entraîné, tourne dans le navigateur, hors ligne). À éviter : reconnaissance vocale native de Chrome (peu fiable sur un nom inventé), Gladia en continu (consomme des crédits, latence). Risque : salle bruyante, donc on garde H en secours.

## Accès pour une personne aveugle

- Aujourd'hui, ces utilisateurs passent par un lecteur d'écran (NVDA/JAWS sur Windows, VoiceOver sur Mac) et naviguent au clavier.
- Brainy est installé comme app Chrome (PWA) : raccourci clavier Windows global (ex. Ctrl+Alt+B) et lancement au démarrage. Aucun travail en plus côté code (manifest).
- Bonus : extension Chrome (raccourci depuis n'importe quel onglet), mot d'activation « Brainy ».
- Phrase du pitch : « Brainy se lance au démarrage, s'appelle avec une touche ou à la voix, et parle à l'utilisateur à chaque étape. »

## Étapes

_À remplir avec Hugo (voir 06-demo.md)._
