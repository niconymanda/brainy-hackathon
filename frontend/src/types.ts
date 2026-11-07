export type MascotSize = 'xl' | 'l' | 's' | 'none'
export type MicState = 'idle' | 'on' | 'off'
export type StepState = 'ok' | 'run' | 'todo'

export interface Cond {
  label: string
  ok: boolean
}

export interface Step {
  label: string
  state: StepState
}

export interface Task {
  title: string
  who: string
  conds?: Cond[]
  lines?: Step[]
  found?: string
}

export interface Option {
  title: string
  tag: string
  detail: string
  best?: boolean
}

export interface DoneRow {
  who: string
  what: string
  when: string
}

export interface HistoryItem {
  title: string
  when: string
  status: string
  tone: 'paid' | 'info' | 'wait'
  isNew?: boolean
}

export interface UiState {
  mascot: MascotSize
  mascotMood?: 'calm' | 'work'
  mic: MicState
  status: string
  sub?: string
  hint?: boolean
  transcript?: string
  bubble?: string
  you?: string
  tasks?: Task[]
  steps?: Step[]
  progress?: number
  confirm?: string[]
  options?: Option[]
  say?: string
  sayHint?: string
  done?: DoneRow[]
  doneNote?: string
}
