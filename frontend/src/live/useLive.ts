import { useCallback, useEffect, useReducer, useRef, useState } from 'react'
import { cancelSpeech, speak, ttsUrl } from '../tts'
import type { HistoryItem, UiState } from '../types'
import type { ClientEvent, ServerEvent } from './protocol'

const IDLE: UiState = {
  mascot: 'xl',
  mic: 'idle',
  status: 'Bonjour',
  sub: "Qu'est-ce que je peux faire pour toi ?",
  hint: true,
}

type Action = ServerEvent | { type: 'thinking' }

function reduce(ui: UiState, e: Action): UiState {
  switch (e.type) {
    case 'thinking':
      return { ...ui, mic: 'off', status: 'Je réfléchis…', mascotMood: 'work' }
    case 'idle':
      return IDLE
    case 'listening':
      return { mascot: 'l', mic: 'on', status: "Je t'écoute…", transcript: '' }
    case 'transcript':
      return { ...ui, transcript: e.text }
    case 'say':
      return { ...ui, sub: e.text, transcript: undefined }
    case 'agent_step': {
      const steps = (ui.steps ?? []).map((s) => ({ ...s, state: 'ok' as const }))
      return {
        mascot: 's',
        mascotMood: 'work',
        mic: 'off',
        status: "Je m'en occupe…",
        steps: [...steps, { label: e.narration, state: 'run' as const }].slice(-6),
      }
    }
    case 'needs_user':
      return { mascot: 's', mic: 'idle', status: e.question, steps: ui.steps, sayHint: 'Appuie sur H pour répondre' }
    case 'confirm_request':
      return {
        mascot: 's',
        mic: 'idle',
        status: 'Je confirme ?',
        confirm: [e.summary],
        sayHint: 'Appuie sur H et dis « oui » ou « non »',
      }
    case 'done':
      return e.ok === false
        ? { mascot: 'l', mic: 'idle', status: e.result, hint: true }
        : { mascot: 'none', mic: 'idle', status: "C'est fait !", done: [], doneNote: e.result }
    case 'error':
      return { mascot: 's', mic: 'idle', status: 'Oups, un souci', sub: `${e.reason} ${e.suggestion}` }
    default:
      return ui
  }
}

const spokenText = (e: ServerEvent) =>
  e.type === 'say' ? e.text
  : e.type === 'needs_user' ? e.question
  : e.type === 'confirm_request' ? `${e.summary}. Je confirme ?`
  : e.type === 'done' ? (e.ok === false ? e.result : `C'est fait ! ${e.result}`)
  : e.type === 'error' ? `${e.reason}. ${e.suggestion}`
  : null

/** Live mode: drives the same UI from the Python backend over WebSocket. */
export function useLive(url: string, muted: boolean) {
  const [ui, dispatch] = useReducer(reduce, IDLE)
  const [history, setHistory] = useState<HistoryItem[]>([])
  const [speaking, setSpeaking] = useState(false)
  const [spoken, setSpoken] = useState('')
  const ws = useRef<WebSocket | null>(null)
  const mutedRef = useRef(muted)
  const uiRef = useRef(ui)
  const nextRef = useRef(() => {})

  useEffect(() => {
    mutedRef.current = muted
    uiRef.current = ui
  })

  useEffect(() => {
    let closed = false
    let speech: AbortController | null = null
    const connect = () => {
      const sock = new WebSocket(url)
      ws.current = sock
      sock.onmessage = (m) => {
        const e = JSON.parse(m.data) as ServerEvent
        if (e.type === 'history') return setHistory(e.items)
        if (e.type === 'hotkey') return nextRef.current()
        dispatch(e)
        const text = spokenText(e)
        if (text) {
          speech?.abort()
          speech = new AbortController()
          setSpoken(text)
          setSpeaking(true)
          speak(text, mutedRef.current, speech.signal, ttsUrl(url)).then(() => setSpeaking(false))
        }
      }
      sock.onclose = () => {
        if (!closed) window.setTimeout(connect, 1500)
      }
    }
    connect()
    return () => {
      closed = true
      speech?.abort()
      ws.current?.close()
    }
  }, [url])

  const send = useCallback((e: ClientEvent) => {
    if (ws.current?.readyState === WebSocket.OPEN) ws.current.send(JSON.stringify(e))
  }, [])

  const next = useCallback(() => {
    cancelSpeech()
    if (uiRef.current.mic === 'on') {
      send({ type: 'stop_listening' })
      dispatch({ type: 'thinking' })
    } else if (uiRef.current.mic === 'idle') send({ type: 'start_listening' })
  }, [send])

  useEffect(() => {
    nextRef.current = next
  }, [next])

  const confirm = useCallback(
    (yes: boolean) => {
      cancelSpeech()
      send({ type: 'confirm', answer: yes ? 'oui' : 'non' })
      dispatch({ type: 'thinking' })
    },
    [send],
  )

  const submitText = useCallback(
    (text: string) => {
      send({ type: 'user_text', text })
      dispatch({ type: 'thinking' })
    },
    [send],
  )
  const reset = useCallback(() => dispatch({ type: 'idle' }), [])

  return { ui, speaking, spoken, history, waitingForUser: ui.mic !== 'off', next, reset, showPlanB: () => {}, submitText, confirm }
}
