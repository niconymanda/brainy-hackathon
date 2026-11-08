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

## Getting started / Testing
> *Installation / Tests*

The sections above describe the project vision. Today's terminal implementation offers speech transcription, prompt generation, the local Playwright/Holo web agent and their end-to-end pipeline. Questions and confirmations are typed, not spoken. Run the commands below from the repository root with the virtual environment activated.
> *Les sections précédentes décrivent la vision du projet. L'implémentation actuelle en terminal propose transcription, génération de prompt, agent web local Playwright/Holo et pipeline complet. Questions et confirmations se font au clavier, pas à la voix. Exécutez les commandes depuis la racine du dépôt, environnement virtuel activé.*

### 1. Requirements
> *Prérequis*

- Git and **Python 3.10+** (the code uses union annotations such as `str | None`).
- A Gladia API key from [app.gladia.io](https://app.gladia.io), stored as `GLADIA_API_KEY`.
- An H Company API key in `H_API_KEY` for agent/pipeline runs. Optional `H_MODEL` sets the model; default: `holo3-1-35b-a3b`. `--model` overrides it.
- Internet and a microphone for speech tests, or a compatible WAV file.
- Debian/Ubuntu microphone capture needs `sudo apt install libportaudio2`. On macOS, allow microphone access for Terminal/your IDE in **System Settings → Privacy & Security → Microphone**. Check Windows microphone privacy settings too.
> - *Git et **Python 3.10+** (annotations comme `str | None`).*
> - *Une clé Gladia depuis [app.gladia.io](https://app.gladia.io), dans `GLADIA_API_KEY`.*
> - *Une clé H Company dans `H_API_KEY` pour l'agent/pipeline. `H_MODEL` est facultatif, avec `holo3-1-35b-a3b` par défaut ; `--model` le remplace.*
> - *Internet et un micro pour les tests vocaux, ou un WAV compatible.*
> - *Sous Debian/Ubuntu, installez `libportaudio2` avec la commande ci-dessus. Sous macOS, autorisez le micro pour Terminal/l'IDE dans **Réglages Système → Confidentialité et sécurité → Microphone**. Vérifiez aussi les permissions Windows.*

### 2. Setup
> *Installation*

Use `devin/voice-to-h-agent` for this PR, or `Devin-works` once the PR is merged there. There is no tracked `.env.example`: create `.env` as below and fill in both values with your editor. If it already exists, edit rather than recreate it. Never commit keys or put secrets in goals or command-line arguments.
> *Utilisez `devin/voice-to-h-agent` pour cette PR, ou `Devin-works` après sa fusion sur cette branche. Aucun `.env.example` n'est suivi : créez `.env` puis renseignez les deux valeurs dans votre éditeur. S'il existe déjà, modifiez-le sans le recréer. Ne commitez jamais de clés et ne mettez aucun secret dans les objectifs ou arguments.*

**macOS/Linux:** ensure `python3` is Python 3.10+; install PortAudio as above on Linux.
> ***macOS/Linux :** vérifiez que `python3` est Python 3.10+ ; installez PortAudio comme indiqué sous Linux.*

~~~sh
git clone https://github.com/niconymanda/brainy-hackathon.git
cd brainy-hackathon
git checkout devin/voice-to-h-agent
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m playwright install chromium
printf 'GLADIA_API_KEY=\nH_API_KEY=\n' > .env
~~~

**Windows PowerShell:** ensure `py` selects Python 3.10+. If activation is blocked by execution policy, use `.\.venv\Scripts\python.exe` instead of `python` for installation and tests without activating.
> ***Windows PowerShell :** vérifiez que `py` utilise Python 3.10+. Si la stratégie d'exécution bloque l'activation, remplacez `python` par `.\.venv\Scripts\python.exe` pour l'installation et les tests, sans activation.*

~~~powershell
git clone https://github.com/niconymanda/brainy-hackathon.git
Set-Location brainy-hackathon
git checkout devin/voice-to-h-agent
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m playwright install chromium
New-Item -Path .env -ItemType File
Add-Content -Path .env -Value 'GLADIA_API_KEY='
Add-Content -Path .env -Value 'H_API_KEY='
~~~

### 3. Test in this order
> *Tester dans cet ordre*

**A. Offline unit tests.** No real API key, microphone or browser session is needed. One known test, `test_empty_audio_auto_detection`, currently fails because the client unconditionally includes post-processing settings; this is not an installation error. Investigate additional failures.
> ***A. Tests unitaires hors ligne.** Aucune vraie clé, aucun micro ni session navigateur nécessaires. Le test connu `test_empty_audio_auto_detection` échoue car le client inclut systématiquement les réglages de post-traitement ; ce n'est pas une erreur d'installation. Examinez tout autre échec.*

~~~sh
python -m unittest discover tests
~~~

**B. List microphones.** No key is required. Pick a listed input index/name with `--device` if the default microphone is wrong.
> ***B. Lister les micros.** Aucune clé nécessaire. Sélectionnez un indice/nom d'entrée avec `--device` si le micro par défaut ne convient pas.*

~~~sh
python -m brainy.stt --list-devices
~~~

**C. Speech only.** Speak and watch partial/final transcripts. The first command uses the default mic and automatic language detection; the second enables French/English code switching, a summary and explicit silence/utterance settings. Append `--device INDEX` with a listed index to select another mic.
> ***C. Voix seule.** Parlez et observez les transcriptions partielles/définitives. La première commande utilise le micro par défaut et la détection automatique ; la seconde active français/anglais, résumé et réglages de silence/durée. Ajoutez `--device INDEX` avec un indice de la liste pour changer de micro.*

~~~sh
python -m brainy.stt
python -m brainy.stt --language fr --language en --summary bullet_points --endpointing 0.5 --max-utterance 9
~~~

Without a microphone, supply your own uncompressed **16 kHz, mono, 16-bit PCM WAV**. It still streams to Gladia and needs its key.
> *Sans micro, fournissez votre WAV PCM non compressé **16 kHz, mono, 16 bits**. Il est toujours envoyé à Gladia et nécessite sa clé.*

~~~sh
python -m brainy.stt --file sample.wav --summary concise
~~~

**D. Prompt only.** Summarization is enabled; the prompt prints without calling the agent or requiring an H key. Missing/failed/empty summaries fall back to joined final utterances. Empty input produces an error. The current template contains the summary, not a separate verbatim transcript.
> ***D. Prompt seul.** Le résumé est activé ; le prompt s'affiche sans appel à l'agent ni clé H. Un résumé absent/en erreur/vide est remplacé par les énoncés définitifs joints. Une entrée vide produit une erreur. Le modèle actuel contient le résumé, sans transcription séparée mot pour mot.*

~~~sh
python -m brainy.stt --language fr --language en --h-prompt
~~~

**E. Agent only.** No microphone or Gladia key is used. The browser opens visibly; steps/results and questions print in the terminal. Type replies; confirmation gates accept only `yes` or `oui`. Press Enter when prompted to close the browser, or use `--headless` to skip that closing wait.
> ***E. Agent seul.** Aucun micro ni clé Gladia. Le navigateur s'ouvre et étapes/résultats/questions s'affichent dans le terminal. Répondez au clavier ; les confirmations acceptent seulement `yes` ou `oui`. Fermez avec Entrée à la demande, ou utilisez `--headless` pour éviter cette attente.*

~~~sh
python -m brainy.agent "Describe this page and stop without submitting anything." --url https://example.org
python -m brainy.agent "Fill Customer name with Test User, choose Large, then stop without submitting." --url https://httpbin.org/forms/post --fill "Customer name=Test User" --choose Large
~~~

Interleave `--choose TEXT` and `--fill "FIELD=TEXT"` in command-line order. Only the first pending item is tried; if absent, Holo continues without discarding it. Choices use normalized exact labels, with `|` for alternatives. Fields match normalized label/placeholder/aria-label/name substrings; secret-like fields are refused. Site labels may change; these examples do not guarantee successful automation.
> *Alternez `--choose TEXTE` et `--fill "CHAMP=TEXTE"` dans l'ordre souhaité. Seul le premier élément est essayé ; s'il manque, Holo continue sans le supprimer. Les choix utilisent des libellés exacts normalisés, avec `|` pour les alternatives. Les champs correspondent à des sous-chaînes normalisées de libellé/placeholder/aria-label/nom ; les champs sensibles sont refusés. Les libellés peuvent changer : ces exemples ne garantissent pas le succès.*

**F. End-to-end: speak → H web agent.** Both keys are checked before recording. Run this command and say, for example: “Find Paris to Lyon trains for next Friday morning, one adult, second class. Show options and stop before booking or paying.”
> ***F. De bout en bout : parler → agent web H.** Les deux clés sont vérifiées avant l'enregistrement. Lancez la commande puis dites par exemple : « Cherche des trains Paris–Lyon vendredi prochain matin, un adulte, seconde classe. Présente les options et arrête-toi avant de réserver ou payer. »*

~~~sh
python -m brainy --url https://www.sncf-connect.com
~~~

Press **Ctrl+C once** to stop recording and wait for final transcripts/summary (up to about two minutes per post-processing wait stage). Brainy builds and prints the prompt, then opens the browser with it as the local Playwright/Holo agent's goal. Follow-up questions and confirmations are typed in the terminal, not spoken. Missing summaries use the final transcript; empty input exits without launching the browser.
> *Appuyez **une fois sur Ctrl+C** pour arrêter l'enregistrement et attendre transcription/résumé (environ deux minutes maximum par étape d'attente). Brainy construit et affiche le prompt, puis ouvre le navigateur avec celui-ci comme objectif de l'agent local Playwright/Holo. Questions et confirmations se font au clavier, pas à la voix. Sans résumé, la transcription est utilisée ; une entrée vide quitte sans lancer le navigateur.*

While recording or waiting for final results, **a second Ctrl+C** quits without remaining results (exit 130) and skips the agent. Once the agent phase starts, **one Ctrl+C** quits that phase (exit 130). These recording-stop rules also apply to speech-only and prompt-only commands.
> *Pendant l'enregistrement ou l'attente des résultats, **un deuxième Ctrl+C** quitte sans les résultats restants (code 130) et ne lance pas l'agent. Dès la phase agent, **un seul Ctrl+C** la quitte (code 130). Ces règles d'arrêt de l'enregistrement s'appliquent aussi aux commandes voix seule et prompt seul.*

### 4. Main options
> *Options principales*

- **All three CLIs:** `--help` lists every argument.
- **Speech/pipeline:** repeat `--language CODE`; use either `--device INDEX_OR_NAME` or `--file PATH.wav`; `--summary general|bullet_points|concise`; `--endpointing SECONDS` (0.01–10 seconds of silence); `--max-utterance SECONDS` (5–60 seconds of continuous speech, not silence).
- **Speech only:** `--list-devices`, `--h-prompt`.
- **Agent/pipeline:** `--url URL`, `--model MODEL`, `--headless`, `--channel chrome` or `--channel msedge` (otherwise bundled Chromium), `--profile-dir PATH`, `--debug`, repeatable ordered `--choose TEXT` / `--fill FIELD=TEXT`. Use a dedicated private profile, not one already open elsewhere.
- **Agent only:** required positional `goal`; the pipeline obtains its goal from speech.
> - ***Les trois CLI :** `--help` liste les arguments.*
> - ***Voix/pipeline :** `--language CODE` répétable ; soit `--device INDICE_OU_NOM`, soit `--file CHEMIN.wav` ; `--summary general|bullet_points|concise` ; `--endpointing SECONDES` (0,01–10 secondes de silence) ; `--max-utterance SECONDES` (5–60 secondes de parole continue, pas de silence).*
> - ***Voix seule :** `--list-devices`, `--h-prompt`.*
> - ***Agent/pipeline :** `--url URL`, `--model MODÈLE`, `--headless`, `--channel chrome` ou `--channel msedge` (sinon Chromium fourni), `--profile-dir CHEMIN`, `--debug`, `--choose TEXTE` / `--fill CHAMP=TEXTE` répétables dans l'ordre. Utilisez un profil privé dédié, pas déjà ouvert ailleurs.*
> - ***Agent seul :** objectif positionnel `goal` obligatoire ; le pipeline le déduit de la parole.*

Pipeline and prompt-only mode enable bullet-point summaries unless overridden. Standalone STT help says summaries are disabled by default, but the current client still hardcodes post-processing and a 9-second utterance cap; this explains the known test failure. Explicit options override the corresponding settings.
> *Le pipeline et le mode prompt seul activent le résumé en points sauf option contraire. L'aide STT annonce les résumés désactivés par défaut, mais le client impose encore post-traitement et limite d'énoncé de 9 secondes ; cela explique le test en échec. Les options explicites remplacent les réglages correspondants.*

### 5. Troubleshooting / safe testing
> *Dépannage / tests prudents*

- **`ModuleNotFoundError`:** activate the venv and rerun `python -m pip install -r requirements.txt` with its interpreter.
- **No microphone text:** rerun `--list-devices`, select `--device`, check permissions/PortAudio, then try a compatible `--file` to isolate microphone issues from API/network failures.
- **Missing-key error:** fill the required values in repository-root `.env` or export them. Pipeline needs both keys before recording; STT only Gladia; agent only H.
- **Browser launch failure:** rerun `python -m playwright install chromium`; with `--channel`, ensure that browser is installed. On Linux, follow Playwright's printed missing-system-library instructions.
- **Blocked site / stuck agent:** CAPTCHA/anti-bot bypass is not guaranteed. Try a smaller task or stop. Inspect `--debug` output before sharing: private page content may remain.
> - ***`ModuleNotFoundError` :** activez le venv et relancez `python -m pip install -r requirements.txt` avec son interpréteur.*
> - ***Aucun texte du micro :** relancez `--list-devices`, sélectionnez `--device`, vérifiez permissions/PortAudio, puis essayez un `--file` compatible pour isoler les problèmes du micro de ceux de l'API/réseau.*
> - ***Clé manquante :** renseignez les valeurs dans `.env` à la racine ou dans l'environnement. Pipeline : deux clés avant la parole ; STT : Gladia seule ; agent : H seule.*
> - ***Navigateur impossible à lancer :** relancez `python -m playwright install chromium` ; avec `--channel`, vérifiez son installation. Sous Linux, suivez les instructions Playwright de bibliothèques système manquantes.*
> - ***Site bloqué / agent coincé :** aucun contournement garanti des CAPTCHA/protections anti-bot. Essayez une tâche plus petite ou arrêtez. Vérifiez `--debug` avant partage : du contenu privé peut rester.*

Supervise tests and use fictitious data, never real purchases/payments or sensitive accounts. Keyword confirmation gates and prompt instructions are safeguards, **not guarantees** that all irreversible actions are detected. Audio goes to Gladia; screenshots/page context and non-secret follow-up answers go to H Company. Password masking does not remove all private content. Profiles, stdout and debug logs can also contain private data.
> *Surveillez les tests et utilisez des données fictives, jamais de vrais achats/paiements ni comptes sensibles. Confirmations par mots-clés et consignes du prompt sont des protections, **pas des garanties** de détection de toute action irréversible. L'audio va à Gladia ; captures/contexte de page et réponses non sensibles vont à H Company. Le masquage des mots de passe ne retire pas tout contenu privé. Profils, sortie standard et logs peuvent aussi contenir des données privées.*
