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
## Quick Start (Windows)

**Requirements:** an H Company API key, a Gladia API key, and an ElevenLabs API key.

1. Install dependencies (do not install `webview` separately):
```powershell
   pip install -r requirements.txt
```
2. Add your three API keys to a `.env` file in the project root.
3. Launch the app:
```powershell
   .\Brainy.bat
```
