# Brainy

A voice-first assistant that helps people with disabilities, starting with blind and visually impaired users, get everyday online tasks done: buying train and plane tickets, booking appointments, filling in forms.

> *Un assistant vocal qui aide les personnes en situation de handicap, à commencer par les personnes aveugles et malvoyantes, à faire leurs démarches en ligne du quotidien : acheter des billets de train ou d'avion, prendre des rendez-vous, remplir des formulaires.*

Many websites still don't work with screen readers. Captchas, date pickers, seat maps, pop-ups and multi-step checkouts turn a five-minute task into a frustrating hour, or make it impossible without help. Brainy lets the user say what they want and then handles the website for them.

> *Beaucoup de sites web ne fonctionnent toujours pas avec les lecteurs d'écran. Captchas, sélecteurs de date, plans de sièges, pop-ups et paiements en plusieurs étapes transforment une tâche de cinq minutes en une heure de frustration, ou la rendent impossible sans aide. Avec Brainy, l'utilisateur dit ce qu'il veut, et Brainy s'occupe du site à sa place.*

## How it works
> *Fonctionnement*

```
 User speaks ──► Gladia (speech-to-text) ──► Brainy core (intent + dialogue)
                                                    │
                                                    ▼
                                    H Company agent (navigates the website)
                                                    │
 User hears  ◄── spoken confirmations / questions ◄─┘
```

1. **Listen.** The user describes the task out loud, e.g. *"Book me a train from Paris to Lyon next Friday morning, second class."* Gladia transcribes it in real time.
2. **Understand.** Brainy pulls out the intent and the details (origin, destination, date, preferences) and asks follow-up questions if anything is missing or unclear.
3. **Act.** An H Company web agent opens the website and goes through it like a sighted user would: search, filter, select, fill in forms.
4. **Confirm.** Before anything that can't be undone (payment, final booking), Brainy reads back a clear summary and waits for an explicit "yes".
5. **Report.** Brainy tells the user the result (booking reference, time, price) and can save or send it to them.

> 1. ***Écouter.** L'utilisateur décrit sa demande à voix haute, par exemple « Réserve-moi un train Paris–Lyon vendredi prochain dans la matinée, en seconde classe. » Gladia la transcrit en temps réel.*
> 2. ***Comprendre.** Brainy identifie l'intention et les détails (départ, destination, date, préférences) et pose des questions si une information manque ou n'est pas claire.*
> 3. ***Agir.** Un agent web de H Company ouvre le site et le parcourt comme le ferait un utilisateur voyant : rechercher, filtrer, sélectionner, remplir les formulaires.*
> 4. ***Confirmer.** Avant toute action irréversible (paiement, réservation finale), Brainy lit un récapitulatif clair et attend un « oui » explicite.*
> 5. ***Informer.** Brainy communique le résultat (référence de réservation, horaire, prix) et peut l'enregistrer ou l'envoyer à l'utilisateur.*

## Core principles
> *Principes fondamentaux*

### 1. Voice-first, screen-optional
> *La voix d'abord, l'écran en option*

Every interaction must work without seeing a screen. Visual output is a nice-to-have, never a requirement. Responses are short, structured and easy to follow by ear.

> *Chaque interaction doit fonctionner sans voir d'écran. L'affichage est un bonus, jamais une obligation. Les réponses sont courtes, structurées et faciles à suivre à l'oreille.*

### 2. The user stays in control
> *L'utilisateur garde le contrôle*

Brainy acts on the user's behalf, not instead of them. It never pays, books, cancels or submits personal data without explicit spoken confirmation. The user can say "stop", "go back" or "repeat" at any time.

> *Brainy agit pour le compte de l'utilisateur, pas à sa place. Il ne paie, ne réserve, n'annule et n'envoie jamais de données personnelles sans confirmation vocale explicite. L'utilisateur peut dire « stop », « retour » ou « répète » à tout moment.*

### 3. Transparency
> *Transparence*

Brainy says what it is doing ("I'm on the SNCF website, searching trains for Friday…"). When there are options, it presents the few most relevant ones rather than reading out a whole page. When it is unsure, it asks instead of guessing.

> *Brainy annonce ce qu'il fait (« Je suis sur le site de la SNCF, je cherche des trains pour vendredi… »). Lorsqu'il y a plusieurs choix, il présente les quelques options les plus pertinentes plutôt que de lire toute la page. En cas de doute, il pose la question au lieu de deviner.*

### 4. Privacy and trust
> *Confidentialité et confiance*

Users share sensitive data: identity, payment details, health appointments. Collect only what the task needs, keep it no longer than necessary, and never use it for anything else. Credentials and payment details are handled securely and never logged.

> *Les utilisateurs partagent des données sensibles : identité, informations de paiement, rendez-vous médicaux. On ne collecte que ce dont la tâche a besoin, on ne le conserve pas plus longtemps que nécessaire, et on ne l'utilise jamais à d'autres fins. Les identifiants et les données de paiement sont traités de manière sécurisée et ne sont jamais enregistrés dans les logs.*

### 5. Graceful failure
> *Gérer les échecs avec élégance*

Websites change, time out and throw captchas. When Brainy gets stuck, it explains the problem in plain language and offers a way forward: retry, try another provider, or hand off to a human helper. It never fails silently.

> *Les sites changent, expirent et affichent des captchas. Quand Brainy est bloqué, il explique le problème simplement et propose une solution : réessayer, passer par un autre site, ou transmettre à une personne qui peut aider. Il n'échoue jamais en silence.*

### 6. Inclusive by design
> *Inclusif dès la conception*

Blindness is the starting point, but the same design should serve people with motor impairments, dyslexia, cognitive disabilities, older users and anyone who finds complex websites hard to use. Support several languages and accents, adjustable speaking speed and patient pacing.

> *La cécité est le point de départ, mais la même conception doit servir les personnes ayant un handicap moteur, une dyslexie, un handicap cognitif, les personnes âgées et toute personne qui trouve les sites complexes difficiles à utiliser. Plusieurs langues et accents, une vitesse de parole réglable et un rythme patient.*

### 7. Works with the web as it is
> *Fonctionne avec le web tel qu'il est*

Brainy doesn't wait for every website to become accessible. It works on existing sites through a general-purpose web agent, so it isn't limited to partners or official APIs.

> *Brainy n'attend pas que chaque site devienne accessible. Il fonctionne sur les sites existants grâce à un agent web généraliste, et ne se limite donc pas aux partenaires ou aux API officielles.*

## Technology
> *Technologies*

| Component | Role |
|-----------|------|
| **[Gladia](https://www.gladia.io/)** | Real-time speech-to-text, so the user can talk to Brainy naturally, in their own language. <br> *Transcription vocale en temps réel, pour que l'utilisateur parle à Brainy naturellement, dans sa propre langue.* |
| **[H Company](https://www.hcompany.ai/)** | AI agents that operate websites: navigating, clicking, filling in forms and completing multi-step flows for the user. <br> *Agents IA qui utilisent les sites web : navigation, clics, remplissage de formulaires et parcours en plusieurs étapes pour l'utilisateur.* |
| **[Devin](https://devin.ai/)** | AI software engineer used to build, test and iterate on Brainy quickly during the hackathon. <br> *Ingénieur logiciel IA utilisé pour développer, tester et faire évoluer Brainy rapidement pendant le hackathon.* |

## Example use cases
> *Exemples d'utilisation*

- Buying train or plane tickets
- Booking a doctor's, hairdresser's or government appointment
- Ordering groceries or medication online
- Filling in administrative forms
- Checking and changing existing bookings

> - *Acheter des billets de train ou d'avion*
> - *Prendre rendez-vous chez le médecin, le coiffeur ou dans une administration*
> - *Commander des courses ou des médicaments en ligne*
> - *Remplir des formulaires administratifs*
> - *Consulter et modifier des réservations existantes*

## Speech-to-text (Gladia)
> *Transcription vocale (Gladia)*

Requires Python 3.10+ and a Gladia API key. From the repository root, create a virtual environment and install the pinned dependencies. On Windows use `py -m venv .venv` and `.venv\Scripts\activate` instead of the first two commands below. Linux microphone capture also needs PortAudio (e.g. `sudo apt install libportaudio2` on Debian/Ubuntu); sounddevice's macOS/Windows wheels bundle it. Allow microphone access in your OS privacy settings.

> *Python 3.10+ et une clé API Gladia sont nécessaires. À la racine du dépôt, créez un environnement virtuel et installez les dépendances épinglées. Sous Windows, utilisez `py -m venv .venv` et `.venv\Scripts\activate` à la place des deux premières commandes. Sous Linux, le microphone nécessite aussi PortAudio (par exemple `sudo apt install libportaudio2` sur Debian/Ubuntu) ; les distributions macOS/Windows de sounddevice l'incluent. Autorisez l'accès au microphone dans les paramètres de confidentialité.*

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Copy `.env.example` to `.env` and set `GLADIA_API_KEY`, or export that environment variable. Never commit your key. Audio is sent to Gladia over the network and may incur usage charges. Transcripts print to stdout; redirected output contains only final utterances.

> *Copiez `.env.example` vers `.env` et renseignez `GLADIA_API_KEY`, ou exportez cette variable d'environnement. Ne commitez jamais votre clé. L'audio est envoyé à Gladia via le réseau et peut entraîner des frais. Les transcriptions s'affichent sur la sortie standard ; une sortie redirigée ne contient que les énoncés définitifs.*

```sh
python -m brainy.stt --help
python -m brainy.stt --list-devices
python -m brainy.stt
python -m brainy.stt --device 0 --language fr
python -m brainy.stt --language fr --language en
python -m brainy.stt --file sample.wav --language fr --language en
python -m brainy.stt --language fr --language en --summary bullet_points --endpointing 0.5 --max-utterance 9
```

The default detects the language automatically. Repeat `--language` to enable code switching between the specified languages (French/English recommended for this team). Partial text updates in place in a terminal; final utterances get their own line. Press Ctrl+C once to stop capture and send `stop_recording`; a message confirms that final results are pending. Keep the process open for the summary. Press Ctrl+C again to quit without remaining results (exit code 130). WAV input must be uncompressed 16 kHz, mono, signed 16-bit PCM and is streamed at real-time speed; no conversion is performed.

> *Par défaut, la langue est détectée automatiquement. Répétez `--language` pour permettre l'alternance entre les langues indiquées (français/anglais recommandés pour cette équipe). Le texte provisoire est mis à jour sur place dans un terminal ; chaque énoncé définitif occupe sa propre ligne. Appuyez une fois sur Ctrl+C pour arrêter la capture et envoyer `stop_recording` ; un message confirme l'attente des résultats. Laissez le programme ouvert pour recevoir le résumé. Un second Ctrl+C quitte sans les résultats restants (code de sortie 130). Le fichier WAV doit être en PCM non compressé, 16 kHz, mono, signé sur 16 bits ; il est envoyé à vitesse réelle, sans conversion.*

Use `--summary general|bullet_points|concise` to print a summary after stopping; addon failures are reported without aborting transcription. `--endpointing` controls the silence ending an utterance (0.01–10 seconds, API default 0.05), rounded by Gladia to whole milliseconds. `--max-utterance` caps speech without endpointing (5–60 seconds, API default 5); it does not set the silence timeout. Both settings are omitted unless supplied. Summaries arrive during the final-result wait after Ctrl+C or WAV completion.

> *Utilisez `--summary general|bullet_points|concise` pour afficher un résumé après l'arrêt ; les erreurs de cet ajout sont signalées sans interrompre la transcription. `--endpointing` règle le silence terminant un énoncé (0,01–10 secondes, valeur API par défaut 0,05), arrondi par Gladia à la milliseconde. `--max-utterance` limite la parole sans coupure (5–60 secondes, valeur API par défaut 5) ; ce n'est pas un délai de silence. Ces réglages sont omis si non fournis. Le résumé arrive pendant l'attente des résultats définitifs après Ctrl+C ou la fin du WAV.*

After stopping, the client waits up to two minutes for WebSocket post-processing. If no summary event arrives, it fetches the live result with the session id, polling queued/processing jobs with backoff for up to two more minutes. A failed, missing or timed-out summary is reported explicitly rather than silently omitted. Network failures and temporary server errors are retried within that bound; this does not create another transcription session.

> *Après l'arrêt, le client attend jusqu'à deux minutes le post-traitement WebSocket. Si aucun événement de résumé n'arrive, il récupère le résultat avec l'identifiant de session et interroge les tâches en attente ou en cours avec des délais croissants pendant deux minutes supplémentaires au maximum. Un résumé absent, en échec ou hors délai est signalé explicitement. Les erreurs réseau et serveur temporaires sont réessayées dans cette limite, sans créer une nouvelle session de transcription.*

Reuse `brainy.stt.GladiaClient.transcribe(audio, callback, stop)` with an async generator of PCM byte chunks, a synchronous callback receiving `Transcript` objects (`text`, `is_final`, `utterance_id`, `language`), and an optional `asyncio.Event` for graceful shutdown. Client keyword options are `summary_type`, `endpointing`, and `maximum_duration_without_endpointing`; `transcribe(..., on_summary=callback)` receives a `Summary` with `results` or `error`. Audio sources live in `brainy/stt/audio.py`; the thin CLI is `brainy/stt/__main__.py`. Run offline protocol tests with `python -m unittest discover -s tests -v`.

> *Réutilisez `brainy.stt.GladiaClient.transcribe(audio, callback, stop)` avec un générateur asynchrone de blocs PCM, un callback synchrone recevant des objets `Transcript` (`text`, `is_final`, `utterance_id`, `language`) et, éventuellement, un `asyncio.Event` pour l'arrêt propre. Les options du client sont `summary_type`, `endpointing` et `maximum_duration_without_endpointing` ; `transcribe(..., on_summary=callback)` reçoit un objet `Summary` contenant `results` ou `error`. Les sources audio sont dans `brainy/stt/audio.py` ; la CLI est dans `brainy/stt/__main__.py`. Lancez les tests hors ligne avec `python -m unittest discover -s tests -v`.*

## Voice prompt for a future H agent
> *Prompt vocal pour un futur agent H*

Use `--h-prompt` to prepare and print a task prompt after the speech session ends. It enables bullet-point summarization unless `--summary` specifies another type and falls back to the joined final transcript if no usable summary arrives. The current template includes the summary, not a separate verbatim transcript section. Empty input produces an error. This only generates text: it does not call H, require an H key or execute a task. Gladia still requires `GLADIA_API_KEY` and may incur charges.

> *Utilisez `--h-prompt` pour préparer et afficher un prompt de tâche après la session vocale. Cette option active le résumé en points sauf si `--summary` indique un autre type et utilise les énoncés définitifs joints si aucun résumé exploitable n'arrive. Le modèle actuel inclut le résumé, sans section séparée de transcription mot pour mot. Une entrée vide produit une erreur. Seul du texte est généré : aucun appel à H, aucune clé H et aucune exécution de tâche. Gladia nécessite toujours `GLADIA_API_KEY` et peut entraîner des frais.*

```sh
python -m brainy.stt --language fr --language en --h-prompt
python -m brainy.stt --file sample.wav --summary concise --h-prompt
```

Press Ctrl+C once and wait for the final results and prompt. The prompt contains private speech content and is printed to stdout. Reuse `brainy.h_task.build_h_prompt(summary, transcript="")` for explicit text, or `brainy.stt.__main__.build_h_prompt_from_results(final_utterances, summaries)` to select a summary and join final utterances. The async CLI `run(args)` also returns the generated prompt string when enabled. The supplied prompt asks a future agent to request missing details and stop before final purchases, bookings, payments or submissions; these are instructions, not an enforced approval gate.

> *Appuyez une seule fois sur Ctrl+C et attendez les résultats définitifs et le prompt. Le prompt contient le contenu privé de la parole et est affiché sur la sortie standard. Réutilisez `brainy.h_task.build_h_prompt(summary, transcript="")` pour du texte explicite, ou `brainy.stt.__main__.build_h_prompt_from_results(final_utterances, summaries)` pour sélectionner un résumé et joindre les énoncés définitifs. La fonction asynchrone `run(args)` de la CLI renvoie aussi le prompt généré lorsque l'option est activée. Le prompt fourni demande au futur agent de poser les questions nécessaires et de s'arrêter avant tout achat, réservation, paiement ou envoi définitif ; ce sont des instructions, pas un verrou de validation imposé par le code.*

## End-to-end: speak → H web agent
> *De bout en bout : parler → agent web H*

Set `GLADIA_API_KEY` and `H_API_KEY` in your environment or `.env` before starting; both are checked before recording. Install the requirements and Playwright's Chromium (`python -m playwright install chromium`), then run:

> *Renseignez `GLADIA_API_KEY` et `H_API_KEY` dans l'environnement ou `.env` avant de commencer ; les deux clés sont vérifiées avant l'enregistrement. Installez les dépendances et Chromium pour Playwright (`python -m playwright install chromium`), puis lancez :*

```sh
python -m brainy
python -m brainy --language fr --language en --channel chrome --url https://www.google.com
```

Speak, then press Ctrl+C once to stop recording and wait for final transcripts and the summary. Brainy builds the same prompt as `python -m brainy.stt --h-prompt`, then passes it to the existing local Playwright/Holo web agent. Steps and results print in the terminal; follow-up questions and confirmations use typed input. Ctrl+C during the agent phase quits with code 130. The browser stays open until Enter unless `--headless` is set. Audio options (`--file`, `--device`, `--summary`, `--endpointing`, `--max-utterance`) and agent options (`--model`, `--profile-dir`, `--debug`) are also available. No hosted H SDK is used; the agent still calls Holo, and speech/browser content may be shared with the respective services.

> *Parlez, puis appuyez une fois sur Ctrl+C pour arrêter l'enregistrement et attendre la transcription définitive et le résumé. Brainy construit le même prompt que `python -m brainy.stt --h-prompt`, puis le transmet à l'agent web local Playwright/Holo existant. Les étapes et résultats s'affichent dans le terminal ; les questions et confirmations se font au clavier. Ctrl+C pendant la phase agent quitte avec le code 130. Le navigateur reste ouvert jusqu'à Entrée, sauf avec `--headless`. Les options audio (`--file`, `--device`, `--summary`, `--endpointing`, `--max-utterance`) et agent (`--model`, `--profile-dir`, `--debug`) sont aussi disponibles. Aucun SDK H hébergé n'est utilisé ; l'agent appelle toujours Holo, et le contenu vocal ou du navigateur peut être partagé avec les services concernés.*

## Web agent (H Company)
> *Agent web (H Company)*

Use `--channel chrome` or `--channel msedge` to launch your installed Google Chrome or Microsoft Edge; otherwise Playwright uses bundled Chromium. Combining `--channel chrome --profile-dir PATH` can reduce bot blocking by keeping a regular browser profile (use a dedicated private profile, not one already open elsewhere). Headed mode also disables Blink's AutomationControlled feature; none of these options guarantees access to sites that block automation. Headed runs wait for Enter before closing; Ctrl+C exits.

> *Utilisez `--channel chrome` ou `--channel msedge` pour lancer Google Chrome ou Microsoft Edge installé ; sinon Playwright utilise Chromium fourni. La combinaison `--channel chrome --profile-dir CHEMIN` peut réduire les blocages anti-bot en conservant un profil de navigateur (utilisez un profil privé dédié, pas un profil déjà ouvert ailleurs). Le mode visible désactive aussi la fonctionnalité Blink AutomationControlled ; aucune option ne garantit l'accès aux sites qui bloquent l'automatisation. En mode visible, Entrée ferme le navigateur en fin d'exécution ; Ctrl+C quitte.*

The agent follows new tabs and can reopen the last URL when every tab closes or crashes, at most twice per run. Form state may be lost; recovery tells Holo to inspect the page and not repeat submissions. A disconnected browser/context or exhausted recovery budget produces a safe categorized error. `--debug` prints local-only exception details and page opened/closed/crashed/navigated events to stderr. API keys, credential/header details and URL query strings are redacted, but debug messages and URL paths may still contain private data: inspect logs before sharing them. Without `--debug`, only safe error categories are shown.

> *L'agent suit les nouveaux onglets et peut rouvrir la dernière URL si tous les onglets se ferment ou plantent, au maximum deux fois par exécution. Les formulaires peuvent perdre leur état ; Holo est averti d'inspecter la page et de ne pas répéter les envois. Un navigateur/contexte déconnecté ou une limite de récupération atteinte produit une erreur catégorisée sans détails sensibles. `--debug` affiche uniquement en local, sur stderr, les détails des exceptions et les événements d'ouverture, fermeture, plantage et navigation. Les clés API, détails d'identifiants/en-têtes et paramètres d'URL sont masqués, mais les messages et chemins d'URL peuvent encore contenir des données privées : vérifiez les journaux avant de les partager. Sans `--debug`, seules les catégories d'erreur sont affichées.*

The standalone text harness implements Brainy's Act step: Playwright captures the page, Holo chooses one action, and Brainy executes it before taking another screenshot. Install the pinned requirements (Python 3.10+) and Chromium, then set `H_API_KEY` in your environment or local `.env`. `H_MODEL` defaults to `holo3-1-35b-a3b`; `--model holo4-35b-a3b` overrides it. Never commit keys.

> *La CLI texte autonome implémente l'étape Agir : Playwright capture la page, Holo choisit une action, puis Brainy l'exécute avant une nouvelle capture. Installez les dépendances épinglées (Python 3.10+) et Chromium, puis renseignez `H_API_KEY` dans l'environnement ou le fichier local `.env`. `H_MODEL` vaut par défaut `holo3-1-35b-a3b` ; `--model holo4-35b-a3b` permet de le changer. Ne commitez jamais les clés.*

```sh
python -m pip install -r requirements.txt
python -m playwright install chromium
python -m brainy.agent "Fill Customer name with Test User, choose Large pizza size, then submit the order." --url https://httpbin.org/forms/post
python -m brainy.agent "Describe the next step" --url https://example.org --headless
```

The browser is visible by default; `--headless` hides it and `--profile-dir PATH` optionally keeps a private browser profile. No microphone is used. The async `WebAgent.run()` iterator emits narration, user questions, confirmation requests, completion and safe errors; its `ask` callback collects replies. Follow-up answers are sent to the model, except when the question mentions secrets (password/mot de passe, card/carte, CVV/CVC, code, PIN, IBAN, OTP/SMS): only a manual-step acknowledgement is sent in those cases. Replies `stop`, `non` or `no` stop the run. Runs stop after 25 decisions by default.

> *Le navigateur est visible par défaut ; `--headless` le masque et `--profile-dir CHEMIN` conserve éventuellement un profil privé. Aucun microphone n'est utilisé. L'itérateur asynchrone `WebAgent.run()` émet narration, questions, confirmations, résultat et erreurs ; le callback `ask` recueille les réponses. Les réponses aux questions sont envoyées au modèle, sauf si la question mentionne un secret (password/mot de passe, card/carte, CVV/CVC, code, PIN, IBAN, OTP/SMS) : seul un accusé d'intervention manuelle est alors transmis. Les réponses `stop`, `non` ou `no` arrêtent l'exécution. Une exécution s'arrête après 25 décisions par défaut.*

Before a model `confirm` action, or a click whose target/narration mentions payment, submission, ordering or booking (English/French keywords), Brainy asks for approval. Only an exact `yes` or `oui` (ignoring case/outer whitespace) allows that single click; any other answer skips it and stops the run. This keyword gate is a first-slice safeguard, not a guarantee that all irreversible actions are detected: supervise it and do not use real purchases or sensitive accounts yet. The next screenshot lets Holo verify results, including radio selections. Screenshots are sent to H Company; password inputs are masked, but other sensitive content may remain visible. Never supply credentials in goals or use pages exposing secrets. There is no credential-entry workflow yet.

> *Avant une action `confirm`, ou un clic dont la cible/narration mentionne paiement, envoi, commande ou réservation (mots-clés français/anglais), Brainy demande l'accord. Seul `yes` ou `oui` exact (sans tenir compte de la casse et des espaces autour) autorise ce clic unique ; toute autre réponse l'annule et arrête l'exécution. Ce filtre est une première protection, pas une garantie de détection de toutes les actions irréversibles : surveillez l'agent et n'utilisez pas encore d'achats réels ni de comptes sensibles. La capture suivante permet à Holo de vérifier le résultat, notamment les boutons radio. Les captures sont envoyées à H Company ; les champs de mot de passe sont masqués, mais d'autres données sensibles peuvent rester visibles. Ne fournissez jamais d'identifiants dans les objectifs et n'utilisez pas de pages exposant des secrets. La saisie sécurisée d'identifiants n'est pas encore implémentée.*

## Status
> *État du projet*

Hackathon project, early stage. Standalone Gladia speech-to-text and H Company web-agent text CLIs are implemented; their voice integration and the rest of the assistant remain a project vision.

> *Projet de hackathon, à un stade précoce. Les CLI autonomes de transcription Gladia et d'agent web H Company sont implémentées ; leur intégration vocale et le reste de l'assistant restent une vision du projet.*
