import { useCallback, useEffect, useRef, useState } from 'react'
import { speak } from '../tts'
import type { HistoryItem, UiState } from '../types'
import { CONFIRM_INDEX, INITIAL_HISTORY, frames, planB, type Frame } from './sarah'

const sleep = (ms: number, signal: AbortSignal) =>
  new Promise<void>((resolve) => {
    const t = window.setTimeout(resolve, ms)
    signal.addEventListener('abort', () => {
      window.clearTimeout(t)
      resolve()
    })
  })

export function useDemo(muted: boolean) {
  const [index, setIndex] = useState(0)
  const [inPlanB, setInPlanB] = useState(false)
  const [typed, setTyped] = useState(0)
  const [speaking, setSpeaking] = useState(false)
  const [spoken, setSpoken] = useState('')
  const [history, setHistory] = useState<HistoryItem[]>(INITIAL_HISTORY)
  const mutedRef = useRef(muted)
  useEffect(() => {
    mutedRef.current = muted
  })

  const frame: Frame = inPlanB ? planB : frames[index]

  useEffect(() => {
    const ctrl = new AbortController()
    const { signal } = ctrl
    const run = async () => {
      setTyped(0)
      if (frame.history) setHistory(frame.history)
      if (frame.type) {
        const total = frame.type.length
        const stepMs = (frame.typeMs ?? 3000) / total
        for (let i = 1; i <= total && !signal.aborted; i += 2) {
          setTyped(i)
          await sleep(stepMs * 2, signal)
        }
        setTyped(total)
      }
      if (frame.speak && !signal.aborted) {
        setSpoken(frame.speak)
        setSpeaking(true)
        await speak(frame.speak, mutedRef.current, signal)
        setSpeaking(false)
      }
      if (frame.advance === 'auto' && !signal.aborted) {
        await sleep(frame.wait ?? 1000, signal)
        if (!signal.aborted) setIndex((i) => Math.min(i + 1, frames.length - 1))
      }
    }
    run()
    return () => {
      ctrl.abort()
      setSpeaking(false)
    }
  }, [frame])

  const next = useCallback(() => {
    if (inPlanB) {
      setInPlanB(false)
      setIndex(CONFIRM_INDEX)
      return
    }
    if (frame.advance === 'H') setIndex((i) => Math.min(i + 1, frames.length - 1))
    else if (frame.advance === 'end') {
      setHistory(INITIAL_HISTORY)
      setIndex(0)
    }
  }, [frame, inPlanB])

  const reset = useCallback(() => {
    setInPlanB(false)
    setHistory(INITIAL_HISTORY)
    setIndex(0)
  }, [])

  const showPlanB = useCallback(() => setInPlanB(true), [])

  const ui: UiState = { ...frame.ui }
  if (frame.type) {
    const text = frame.type.slice(0, typed)
    if (frame.typeInto === 'you') ui.you = text
    else ui.transcript = text
  }

  return {
    ui,
    speaking,
    spoken,
    history,
    waitingForUser: frame.advance === 'H' || frame.advance === 'end',
    next,
    reset,
    showPlanB,
    submitText: () => next(),
    confirm: (yes: boolean) => (yes ? next() : reset()),
  }
}
