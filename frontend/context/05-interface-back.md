# Interface avec le back

> Hors périmètre de Hugo pour l'instant : la mission front = l'interface. Ce fichier garde juste la piste envisagée pour que le front reste compatible.

## Piste probable (à confirmer par la partenaire back)

- **App locale sur le PC**, pas de site hébergé : un double-clic ouvre une fenêtre Brainy.
- **Serveur Python local** (ex. FastAPI sur localhost) : garde les clés, parle à Gladia (voix vers texte) et à l'agent H Company, renvoie l'avancement au front.
- **Fenêtre** : le front React de `frontend/` affiché dans une fenêtre d'app (pywebview, ou Chrome en mode app).
- **Lanceur** : un seul fichier à double-cliquer (.exe via PyInstaller ou .bat).
- **Raccourci global** possible côté Python (ex. Ctrl+Alt+B) et mot d'activation « Brainy » (Porcupine).

## Points ouverts (côté back)

- Gladia ne fait que la transcription : la voix de Brainy nécessite une synthèse vocale (synthèse intégrée du navigateur, ou API type ElevenLabs).
- L'agent H Company navigue dans un navigateur cloud : connexion aux comptes de l'utilisateur et affichage de ce que fait l'agent à vérifier.

## Ce que le front doit prévoir

- Les états de l'interface sont pilotés par des événements (ex. via WebSocket) : repos, écoute, transcription, l'agent agit, confirmation demandée, terminé, erreur.
- Tant que le back n'existe pas, le front tourne avec un **mode démo simulé** qui joue ces événements.
