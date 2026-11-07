import type { HistoryItem, Step, Task, UiState } from '../types'

export type Advance = 'H' | 'auto' | 'end'

export interface Frame {
  ui: UiState
  /** Text typed progressively into `transcript` (or `you` when typeInto is 'you'). */
  type?: string
  typeInto?: 'transcript' | 'you'
  typeMs?: number
  /** Brainy speaks this line (TTS) and shows it in the live region. */
  speak?: string
  advance: Advance
  /** Pause after typing/speech before moving on (auto frames). */
  wait?: number
  history?: HistoryItem[]
}

const REQUEST =
  "Il me faut un dermato pour moi, un samedi de préférence parce qu'en semaine je bosse. Et le dentiste pour Léo et Inès, le mercredi après-midi vu qu'ils n'ont pas école, l'un après l'autre si possible. Pas trop loin de la maison."

const DERMATO = { title: 'Dermatologue', who: 'Sarah' }
const DENTISTE = { title: 'Dentiste', who: 'Léo + Inès' }

const SEARCH: Array<[0 | 1, string, string]> = [
  [0, '12 dermatos à moins de 3 km', 'Je cherche des dermatos près de chez toi…'],
  [1, 'Mercredi 11 nov. : férié, je passe au 18', 'Je regarde mercredi 11…'],
  [0, 'Samedi 14 nov. : complet partout', 'Je regarde ce samedi…'],
  [1, 'Dr Benali : 14h et 14h30 à la suite', 'Je cherche 2 créneaux à la suite…'],
  [0, 'Samedi 21 nov. : 10h30 libre à 1,2 km', 'Je regarde le samedi suivant…'],
]

function searchTasks(k: number): Task[] {
  const lines: Step[][] = [[], []]
  SEARCH.forEach(([t, label, running], i) => {
    if (i < k) lines[t].push({ label, state: 'ok' })
    else if (i === k) lines[t].push({ label: running, state: 'run' })
  })
  return [
    { ...DERMATO, lines: lines[0] },
    { ...DENTISTE, lines: lines[1] },
  ]
}

const BOOKING = ['Dermato · Sarah', 'Dentiste · Léo', 'Dentiste · Inès', 'Ajout à ton agenda']

function bookingSteps(k: number): Step[] {
  return BOOKING.map((label, i) => ({ label, state: i < k ? 'ok' : i === k ? 'run' : 'todo' }))
}

export const INITIAL_HISTORY: HistoryItem[] = [
  { title: 'Courses Carrefour', when: 'Vendredi', status: 'Livré', tone: 'info' },
  { title: 'Inscription judo · Tom', when: 'Mardi', status: 'Envoyée', tone: 'info' },
]

const DONE_HISTORY: HistoryItem[] = [
  { title: 'Dermato · Sarah', when: 'Sam. 21 nov., 10h30', status: 'Réservé', tone: 'paid', isNew: true },
  { title: 'Dentiste · Léo et Inès', when: 'Mer. 18 nov., 14h00', status: 'Réservé', tone: 'paid', isNew: true },
  ...INITIAL_HISTORY,
]

const CONFIRM_LINES = [
  'Sarah · Dermato · sam. 21 nov. 10h30',
  'Léo · Dentiste · mer. 18 nov. 14h00',
  'Inès · Dentiste · mer. 18 nov. 14h30',
]

export const frames: Frame[] = [
  {
    ui: { mascot: 'xl', mic: 'idle', status: 'Bonsoir Sarah', sub: "Qu'est-ce que je peux faire pour toi ?", hint: true },
    advance: 'H',
  },
  {
    ui: { mascot: 'l', mic: 'on', status: "Je t'écoute…" },
    type: REQUEST,
    typeInto: 'transcript',
    typeMs: 9000,
    advance: 'auto',
    wait: 700,
  },
  {
    ui: {
      mascot: 's',
      mic: 'off',
      status: "C'est noté, je m'en occupe",
      tasks: [
        { ...DERMATO, conds: [{ label: 'Samedi de préférence', ok: false }, { label: 'Près de la maison', ok: false }] },
        {
          ...DENTISTE,
          conds: [
            { label: 'Mercredi après-midi', ok: false },
            { label: 'À la suite', ok: false },
            { label: 'Près de la maison', ok: false },
          ],
        },
      ],
      sub: 'Va faire à manger, je te préviens',
    },
    speak: "C'est noté, deux rendez-vous. Je m'en occupe. Va faire à manger, je te préviens dès que j'ai trouvé.",
    advance: 'auto',
    wait: 900,
  },
  ...[0, 1, 2, 3, 4].map(
    (k): Frame => ({
      ui: {
        mascot: 's',
        mascotMood: 'work',
        mic: 'off',
        status: 'Je cherche sur Doctolib…',
        tasks: searchTasks(k),
        progress: 15 + k * 17,
      },
      advance: 'auto',
      wait: 2000,
    }),
  ),
  {
    ui: {
      mascot: 's',
      mic: 'off',
      status: "J'ai trouvé !",
      tasks: [
        {
          ...DERMATO,
          found: 'Sam. 21 nov. · 10h30 · Dr Martin · 1,2 km',
          conds: [{ label: 'Samedi', ok: true }, { label: '1,2 km', ok: true }],
        },
        {
          ...DENTISTE,
          found: 'Mer. 18 nov. · 14h et 14h30 · Dr Benali',
          conds: [{ label: 'Mercredi', ok: true }, { label: 'À la suite', ok: true }, { label: '800 m', ok: true }],
        },
      ],
    },
    speak:
      "Sarah, j'ai trouvé ! Ce samedi était complet, donc je t'ai pris le suivant, le 21 à 10 heures 30. Et comme mercredi 11 est férié, Léo et Inès passent le 18, à 14 heures et 14 heures 30.",
    advance: 'auto',
    wait: 600,
  },
  {
    ui: {
      mascot: 's',
      mic: 'on',
      status: 'Je réserve les 3 ?',
      confirm: CONFIRM_LINES,
      sayHint: 'Dis « oui », ou change ce que tu veux : « pas le samedi 21 »…',
    },
    speak: 'Je réserve les trois rendez-vous ?',
    advance: 'H',
  },
  {
    ui: { mascot: 's', mic: 'on', status: "Je t'écoute…", confirm: CONFIRM_LINES },
    type: 'Oui, parfait, merci !',
    typeInto: 'you',
    typeMs: 1400,
    advance: 'auto',
    wait: 500,
  },
  ...[0, 1, 2, 3].map(
    (k): Frame => ({
      ui: {
        mascot: 's',
        mascotMood: 'work',
        mic: 'off',
        status: 'Je réserve…',
        you: 'Oui, parfait, merci !',
        steps: bookingSteps(k),
        progress: 20 + k * 22,
      },
      speak: k === 0 ? 'Je réserve.' : undefined,
      advance: 'auto',
      wait: 1300,
    }),
  ),
  {
    ui: {
      mascot: 'none',
      mic: 'idle',
      status: "C'est fait !",
      done: [
        { who: 'Sarah', what: 'Dermato', when: 'Sam. 21 · 10h30' },
        { who: 'Léo', what: 'Dentiste', when: 'Mer. 18 · 14h00' },
        { who: 'Inès', what: 'Dentiste', when: 'Mer. 18 · 14h30' },
      ],
      doneNote: 'Ajoutés à ton agenda · rappel la veille',
    },
    speak: "C'est fait ! Les trois rendez-vous sont réservés et dans ton agenda. Je te les rappellerai la veille. Bon appétit !",
    advance: 'end',
    history: DONE_HISTORY,
  },
]

export const CONFIRM_INDEX = frames.findIndex((f) => f.ui.confirm && f.advance === 'H')

export const planB: Frame = {
  ui: {
    mascot: 's',
    mic: 'on',
    status: 'Un petit choix',
    options: [
      { title: 'Option 1', tag: 'Mer. 18 nov.', detail: "Léo 14h00 · Inès 16h00 (1h30 d'attente)" },
      { title: 'Option 2', tag: 'Sam. 21 nov.', detail: 'Léo 9h00 · Inès 9h30 · puis ton dermato à 10h30', best: true },
    ],
    sayHint: 'Dis « la première » ou « la deuxième »',
  },
  speak:
    "Mercredi 18, je n'ai pas deux créneaux à la suite. Soit Léo à 14 heures et Inès à 16 heures, soit les deux à la suite samedi 21, juste avant ton dermato. Tu préfères ?",
  advance: 'H',
}
