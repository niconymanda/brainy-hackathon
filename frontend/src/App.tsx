import { useEffect, useRef, useState } from 'react'
import { HistoryIcon, KeyboardIcon, MicIcon, SendIcon, SoundIcon } from './components/Icons'
import { Mascot } from './components/Mascot'
import { Content, History } from './components/Panels'
import { useDemo } from './demo/useDemo'
import { useLive } from './live/useLive'

const params = new URLSearchParams(window.location.search)
const WS_URL = params.get('ws')
const IN_APP = params.has('app')
function useLiveEngine(muted: boolean) {
  return useLive(WS_URL ?? '', muted)
}
const useEngine = WS_URL ? useLiveEngine : useDemo

function App() {
  const [muted, setMuted] = useState(params.has('mute'))
  const [historyOpen, setHistoryOpen] = useState(false)
  const [typing, setTyping] = useState(false)
  const [draft, setDraft] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)
  const { ui, speaking, spoken, history, waitingForUser, next, reset, showPlanB, submitText, confirm } = useEngine(muted)

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.metaKey || e.ctrlKey || e.altKey) return
      const k = e.key.toLowerCase()
      if (k === 'h' || k === ' ') {
        e.preventDefault()
        setHistoryOpen(false)
        next()
      } else if (k === 'r') {
        setHistoryOpen(false)
        reset()
      } else if (k === 'b') showPlanB()
      else if (k === 'm') setMuted((m) => !m)
      else if (k === 'escape') {
        setHistoryOpen(false)
        setTyping(false)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [next, reset, showPlanB])

  useEffect(() => {
    if (typing) inputRef.current?.focus()
  }, [typing])

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!draft.trim()) return
    submitText(draft.trim())
    setDraft('')
    setTyping(false)
  }

  const working = ui.mascotMood === 'work'

  return (
    <div className="stage">
      <main className="widget" aria-label="Brainy">
        <div className="titlebar">
          <span className="lights" aria-hidden="true">
            {!IN_APP && (
              <>
                <i />
                <i />
                <i />
              </>
            )}
          </span>
          <span className="title">{historyOpen ? 'Historique' : 'Brainy'}</span>
          <button
            className="sound"
            onClick={() => setMuted((m) => !m)}
            aria-label={muted ? 'Activer la voix' : 'Couper la voix'}
            title="Voix (M)"
          >
            <SoundIcon muted={muted} />
          </button>
        </div>

        <div className="body">
          {historyOpen ? (
            <History items={history} />
          ) : (
            <div className="screen">
              {ui.mascot !== 'none' && <Mascot size={ui.mascot} speaking={speaking} working={working} />}
              <div className="content" key={ui.status}>
                <Content ui={ui} speaking={speaking} onConfirm={confirm} />
              </div>
            </div>
          )}
        </div>

        {ui.hint && !historyOpen && !typing && (
          <p className="hint">
            Appuie sur <kbd>H</kbd> pour parler
          </p>
        )}

        {typing && (
          <form className="type" onSubmit={submit}>
            <input
              ref={inputRef}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="Écris à Brainy…"
              aria-label="Écrire à Brainy"
            />
            <button type="submit" aria-label="Envoyer">
              <SendIcon />
            </button>
          </form>
        )}

        <nav className="bar">
          <button
            className={`side ${historyOpen ? 'side--on' : ''}`}
            onClick={() => setHistoryOpen((o) => !o)}
            aria-pressed={historyOpen}
            aria-label="Historique"
          >
            <HistoryIcon />
          </button>
          <button
            className={`mic mic--${ui.mic}`}
            onClick={() => {
              setHistoryOpen(false)
              next()
            }}
            disabled={ui.mic === 'off' && !waitingForUser}
            aria-label={ui.mic === 'on' ? "Brainy t'écoute" : 'Parler à Brainy (H)'}
          >
            <MicIcon />
          </button>
          <button
            className={`side ${typing ? 'side--on' : ''}`}
            onClick={() => setTyping((t) => !t)}
            aria-pressed={typing}
            aria-label="Écrire au clavier"
          >
            <KeyboardIcon />
          </button>
        </nav>

        <div className="sr-only" aria-live="polite">
          {ui.status}. {spoken}
        </div>
      </main>
    </div>
  )
}

export default App
