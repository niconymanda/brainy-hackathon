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

## Contrat WebSocket (implémenté côté front)

Le front se branche sur le back avec `?ws=ws://localhost:8765` dans l'URL (sinon : mode démo Sarah).
Un message = un objet JSON. Types dans `src/live/protocol.ts`, logique dans `src/live/useLive.ts`.

**Back → front** (calqués sur `brainy/agent/events.py`) :

| `type` | champs | effet à l'écran |
|---|---|---|
| `idle` | – | écran de repos |
| `listening` | – | micro qui pulse, « Je t'écoute… » |
| `transcript` | `text`, `final` | texte de la demande en direct (Gladia) |
| `say` | `text` | Brainy parle (voix + texte) |
| `agent_step` | `narration`, `action` | = `AgentStep` : étape ajoutée à la liste, micro grisé |
| `needs_user` | `question` | = `NeedsUser` : question affichée et lue, micro actif |
| `confirm_request` | `summary` | = `ConfirmRequest` : carte dorée « Je confirme ? » |
| `done` | `result` | = `Done` : écran « C'est fait ! » |
| `error` | `reason`, `suggestion` | = `AgentError` |
| `history` | `items[]` (`title`, `when`, `status`, `tone`) | remplace l'historique |

**Front → back** :

| `type` | champs | quand |
|---|---|---|
| `start_listening` | – | touche H / bouton micro au repos |
| `stop_listening` | – | H pendant l'écoute |
| `user_text` | `text` | message tapé au clavier (ou réponse à `needs_user`) |
| `confirm` | `answer: "oui" \| "non"` | H / micro sur la carte de confirmation |

La voix de Brainy est faite côté front (synthèse vocale du navigateur) : le back envoie juste le texte.
Un faux serveur de test est dans `scripts/mock_ws.py` (`python3 scripts/mock_ws.py`, puis `http://localhost:5173/?ws=ws://localhost:8765`).

## Le pont réel : `brainy/app.py` (branche `app-bridge`)

`python -m brainy.app` (ou double-clic sur `Brainy.command` sur Mac) :
- sert `frontend/dist` et le WebSocket `/ws` sur `127.0.0.1:8765` ;
- ouvre la fenêtre Brainy (pywebview, 360×560, toujours au premier plan, à droite de l'écran) ;
- `start_listening` → micro → Gladia (`fr`), transcription en direct, **arrêt auto après ~2 s de silence** (`BRAINY_SILENCE`) ou à la 2e pression sur H ;
- texte final → `build_h_prompt` → `WebAgent` (Holo) dans un Chrome visible avec un profil dédié `~/.brainy/chrome-profile` (on s'y connecte une fois à Doctolib, ça reste) ;
- si le texte cite un site connu (Doctolib, SNCF, Uber Eats…), l'agent démarre directement dessus ;
- `NeedsUser` / `ConfirmRequest` → la fenêtre affiche la question ; la réponse (voix via H, clavier ou boutons Oui/Non) repart vers l'agent. « oui / ok / parfait / vas-y » = oui, « non / stop / annule » = non ;
- `done` a un champ `ok` (false si l'utilisateur a refusé ou arrêté) ;
- historique sauvegardé dans `~/.brainy/history.json`.

Clés dans `.env` à la racine : `GLADIA_API_KEY`, `H_API_KEY` (ou `HCOMPANY_API_KEY`). Options : `--no-window`, `--channel chrome|msedge`, `--device`, `--language`, `--max-steps`.
