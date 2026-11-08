let frVoice: SpeechSynthesisVoice | null = null
const canSpeak = 'speechSynthesis' in window

function pickVoice() {
  if (!('speechSynthesis' in window)) return
  const voices = window.speechSynthesis.getVoices().filter((v) => v.lang.toLowerCase().startsWith('fr'))
  frVoice = voices.find((v) => /google|natural|neural|amélie|thomas/i.test(v.name)) ?? voices[0] ?? null
}

if ('speechSynthesis' in window) {
  pickVoice()
  window.speechSynthesis.addEventListener('voiceschanged', pickVoice)
}

let audio: HTMLAudioElement | null = null

export function cancelSpeech() {
  audio?.pause()
  audio = null
  if ('speechSynthesis' in window) window.speechSynthesis.cancel()
}

/** The bridge's ElevenLabs endpoint, served next to its WebSocket (keeps the WebSocket URL's token). */
export function ttsUrl(wsUrl: string): string {
  const url = new URL(wsUrl)
  url.protocol = url.protocol === 'wss:' ? 'https:' : 'http:'
  url.pathname = '/tts'
  return url.toString()
}

/**
 * Speaks `text` in French with ElevenLabs when `tts` (the bridge endpoint) is given, else with the browser voice,
 * which is also the fallback if ElevenLabs fails. Resolves when done (or after a reading-time estimate if muted).
 */
export function speak(text: string, muted: boolean, signal: AbortSignal, tts?: string): Promise<void> {
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
    const browserSpeak = () => {
      if (finished || signal.aborted) return
      window.clearTimeout(fallback)
      if (!canSpeak) {
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
    }
    if (muted) {
      fallback = window.setTimeout(finish, estimate)
      return
    }
    if (!tts) return browserSpeak()
    cancelSpeech()
    const player = new Audio(`${tts}?text=${encodeURIComponent(text)}`)
    audio = player
    const failed = () => {
      if (audio === player) audio = null
      browserSpeak()
    }
    player.onended = finish
    player.onerror = failed
    fallback = window.setTimeout(finish, estimate + 15000)
    player.play().catch(failed)
  })
}
