import { useCallback, useEffect, useReducer, useRef, useState } from 'react'
import { cancelSpeech, speak } from '../tts'
import type { HistoryItem, UiState } from '../types'
import type { ClientEvent, ServerEvent } from './protocol'

const IDLE: UiState = { mascot: 'xl', mic: 'idle', status: 'Bonjour', sub: "Qu'est-ce que je peux faire pour toi ?", hint: true }

function reduce(ui: UiState, e: ServerEvent): UiState {
  switch (e.type) {
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
      return { mascot: 's', mic: 'on', status: e.question, steps: ui.steps }
    case 'confirm_request':
      return { mascot: 's', mic: 'on', status: 'Je confirme ?', confirm: [e.summary], sayHint: 'Dis « oui » ou « non »' }
    case 'done':
      return { mascot: 'none', mic: 'idle', status: "C'est fait !", done: [], doneNote: e.result }
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
  : e.type === 'done' ? e.result
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
        dispatch(e)
        const text = spokenText(e)
        if (text) {
          speech?.abort()
          speech = new AbortController()
          setSpoken(text)
          setSpeaking(true)
          speak(text, mutedRef.current, speech.signal).then(() => setSpeaking(false))
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
    const cur = uiRef.current
    if (cur.confirm) send({ type: 'confirm', answer: 'oui' })
    else if (cur.mic === 'on') send({ type: 'stop_listening' })
    else send({ type: 'start_listening' })
  }, [send])

  const submitText = useCallback((text: string) => send({ type: 'user_text', text }), [send])
  const reset = useCallback(() => dispatch({ type: 'idle' }), [])

  return { ui, speaking, spoken, history, waitingForUser: ui.mic !== 'off', next, reset, showPlanB: () => {}, submitText }
}
