# Brainy

A voice-first assistant that helps people with disabilities, starting with blind and visually impaired users, get everyday online tasks done: buying train and plane tickets, booking appointments, filling in forms.

Many websites still don't work with screen readers. Captchas, date pickers, seat maps, pop-ups and multi-step checkouts turn a five-minute task into a frustrating hour, or make it impossible without help. Brainy lets the user say what they want and then handles the website for them.

## How it works

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

## Core principles

### 1. Voice-first, screen-optional
Every interaction must work without seeing a screen. Visual output is a nice-to-have, never a requirement. Responses are short, structured and easy to follow by ear.

### 2. The user stays in control
Brainy acts on the user's behalf, not instead of them. It never pays, books, cancels or submits personal data without explicit spoken confirmation. The user can say "stop", "go back" or "repeat" at any time.

### 3. Transparency
Brainy says what it is doing ("I'm on the SNCF website, searching trains for Friday…"). When there are options, it presents the few most relevant ones rather than reading out a whole page. When it is unsure, it asks instead of guessing.

### 4. Privacy and trust
Users share sensitive data: identity, payment details, health appointments. Collect only what the task needs, keep it no longer than necessary, and never use it for anything else. Credentials and payment details are handled securely and never logged.

### 5. Graceful failure
Websites change, time out and throw captchas. When Brainy gets stuck, it explains the problem in plain language and offers a way forward: retry, try another provider, or hand off to a human helper. It never fails silently.

### 6. Inclusive by design
Blindness is the starting point, but the same design should serve people with motor impairments, dyslexia, cognitive disabilities, older users and anyone who finds complex websites hard to use. Support several languages and accents, adjustable speaking speed and patient pacing.

### 7. Works with the web as it is
Brainy doesn't wait for every website to become accessible. It works on existing sites through a general-purpose web agent, so it isn't limited to partners or official APIs.

## Technology

| Component | Role |
|-----------|------|
| **[Gladia](https://www.gladia.io/)** | Real-time speech-to-text, so the user can talk to Brainy naturally, in their own language. |
| **[H Company](https://www.hcompany.ai/)** | AI agents that operate websites: navigating, clicking, filling in forms and completing multi-step flows for the user. |
| **[Devin](https://devin.ai/)** | AI software engineer used to build, test and iterate on Brainy quickly during the hackathon. |

## Example use cases

- Buying train or plane tickets
- Booking a doctor's, hairdresser's or government appointment
- Ordering groceries or medication online
- Filling in administrative forms
- Checking and changing existing bookings

## Status

Hackathon project, early stage. Setup and usage instructions will be added as the code lands.
