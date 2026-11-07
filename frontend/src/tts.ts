let frVoice: SpeechSynthesisVoice | null = null

function pickVoice() {
  if (!('speechSynthesis' in window)) return
  const voices = window.speechSynthesis.getVoices().filter((v) => v.lang.toLowerCase().startsWith('fr'))
  frVoice = voices.find((v) => /google|natural|neural|amélie|thomas/i.test(v.name)) ?? voices[0] ?? null
}

if ('speechSynthesis' in window) {
  pickVoice()
  window.speechSynthesis.addEventListener('voiceschanged', pickVoice)
}

export function cancelSpeech() {
  if ('speechSynthesis' in window) window.speechSynthesis.cancel()
}

/** Speaks `text` in French; resolves when done (or after a reading-time estimate if muted/unsupported). */
export function speak(text: string, muted: boolean, signal: AbortSignal): Promise<void> {
  const estimate = Math.max(1500, text.length * 55)
  return new Promise((resolve) => {
    let finished = false
    let fallback: number | undefined
    const finish = () => {
      if (finished) return
      finished = true
      window.clearTimeout(fallback)
      resolve()
    }
    signal.addEventListener('abort', () => {
      cancelSpeech()
      finish()
    })
    if (muted || !('speechSynthesis' in window)) {
      fallback = window.setTimeout(finish, estimate)
      return
    }
    const u = new SpeechSynthesisUtterance(text)
    u.lang = 'fr-FR'
    if (frVoice) u.voice = frVoice
    u.rate = 1.05
    u.onend = finish
    u.onerror = finish
    fallback = window.setTimeout(finish, estimate + 6000)
    window.speechSynthesis.cancel()
    window.speechSynthesis.speak(u)
  })
}
