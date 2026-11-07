# Brainy — frontend

Fenêtre Brainy (Vite + React + TypeScript) : fond blanc, mascot animé, scénario de démo « Sarah ».

## Lancer

```bash
cd frontend
npm install
npm run dev            # http://localhost:5173
```

- `http://localhost:5173/` : mode démo Sarah (voix activée)
- `?mute` : démarre sans voix
- `?ws=ws://localhost:8765` : mode live, branché sur le back (contrat dans `context/05-interface-back.md`, faux back : `python3 scripts/mock_ws.py`)

## Touches (mode démo)

| Touche | Action |
|---|---|
| `H` ou `Espace` | parler / passer à l'étape suivante (début, puis « oui » à la confirmation) |
| `B` | plan B (pas 2 créneaux à la suite) |
| `R` | recommencer |
| `M` | couper / remettre la voix |
| `Échap` | fermer l'historique ou le clavier |

Le reste du scénario s'enchaîne tout seul (écoute → to-do → recherche → trouvé → confirmation → réservation → c'est fait).

## Scripts

- `npm run dev` — serveur de dev
- `npm run build` — vérification des types + build
- `npm run lint` — ESLint

Les clés API restent côté back : ne jamais les exposer via des variables `VITE_*`.
