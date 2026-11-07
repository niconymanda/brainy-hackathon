import type { HistoryItem, UiState } from '../types'
import { CheckIcon } from './Icons'

export function Wave() {
  return (
    <span className="wave" aria-hidden="true">
      <i />
      <i />
      <i />
      <i />
      <i />
    </span>
  )
}

export function Content({ ui, speaking, onConfirm }: { ui: UiState; speaking: boolean; onConfirm?: (yes: boolean) => void }) {
  return (
    <>
      {ui.done && (
        <div className="done-badge" aria-hidden="true">
          <CheckIcon size={34} />
        </div>
      )}
      <h1 className="status">
        {ui.status}
        {speaking && <Wave />}
      </h1>
      {ui.sub && !ui.tasks && <p className="sub">{ui.sub}</p>}
      {ui.transcript !== undefined && <p className="transcript">« {ui.transcript} »</p>}
      {ui.you && <p className="you">{ui.you}</p>}
      {ui.tasks && (
        <div className="tasks">
          {ui.tasks.map((t) => (
            <section key={t.title} className={`task ${t.found ? 'task--found' : ''}`}>
              <header>
                <strong>{t.title}</strong>
                <span className="who">{t.who}</span>
              </header>
              {t.found && <p className="found">{t.found}</p>}
              {t.lines && (
                <ul className="lines">
                  {t.lines.map((l) => (
                    <li key={l.label} className={`line line--${l.state}`}>
                      <span className="dot">{l.state === 'ok' && <CheckIcon size={10} />}</span>
                      {l.label}
                    </li>
                  ))}
                </ul>
              )}
              {t.conds && (
                <div className="chips">
                  {t.conds.map((c) => (
                    <span key={c.label} className={`chip ${c.ok ? 'chip--ok' : ''}`}>
                      {c.ok && <CheckIcon size={10} />}
                      {c.label}
                    </span>
                  ))}
                </div>
              )}
            </section>
          ))}
        </div>
      )}
      {ui.sub && ui.tasks && <p className="sub">{ui.sub}</p>}
      {ui.steps && (
        <ul className="steps">
          {ui.steps.map((s) => (
            <li key={s.label} className={`line line--${s.state}`}>
              <span className="dot">{s.state === 'ok' && <CheckIcon size={10} />}</span>
              {s.label}
            </li>
          ))}
        </ul>
      )}
      {ui.progress !== undefined && (
        <div className="progress" role="progressbar" aria-valuenow={ui.progress} aria-valuemin={0} aria-valuemax={100}>
          <span style={{ width: `${ui.progress}%` }} />
        </div>
      )}
      {ui.confirm && (
        <div className="confirm">
          {ui.confirm.map((line) => {
            const [who, ...rest] = line.split(' · ')
            if (!rest.length) return <p key={line}><strong>{line}</strong></p>
            return (
              <p key={line}>
                <strong>{who}</strong> · {rest.join(' · ')}
              </p>
            )
          })}
        </div>
      )}
      {ui.confirm && onConfirm && (
        <div className="confirm-actions">
          <button className="btn btn--yes" onClick={() => onConfirm(true)}>
            Oui, vas-y
          </button>
          <button className="btn btn--no" onClick={() => onConfirm(false)}>
            Non
          </button>
        </div>
      )}
      {ui.options && (
        <div className="options">
          {ui.options.map((o) => (
            <section key={o.title} className={`task ${o.best ? 'task--found' : ''}`}>
              <header>
                <strong>{o.title}</strong>
                <span className="who">{o.tag}</span>
              </header>
              <p className="detail">{o.detail}</p>
            </section>
          ))}
        </div>
      )}
      {ui.done && ui.done.length > 0 && (
        <div className="ticket">
          {ui.done.map((r) => (
            <p key={r.who + r.when}>
              <span>
                <strong>{r.who}</strong> · {r.what}
              </span>
              <span className="muted">{r.when}</span>
            </p>
          ))}
        </div>
      )}
      {ui.doneNote && <p className="sub">{ui.doneNote}</p>}
      {ui.sayHint && <p className="say-hint">{ui.sayHint}</p>}
    </>
  )
}

export function History({ items }: { items: HistoryItem[] }) {
  return (
    <div className="history">
      <h2 className="sr-only">Historique</h2>
      {items.map((h) => (
        <section key={h.title + h.when} className={`hist ${h.isNew ? 'hist--new' : ''}`}>
          <div>
            <strong>{h.title}</strong>
            <span className="muted">{h.when}</span>
          </div>
          <span className={`pill pill--${h.tone}`}>{h.status}</span>
        </section>
      ))}
    </div>
  )
}
