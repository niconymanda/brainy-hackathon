import { useState } from 'react'
import type { MascotSize } from '../types'

interface Props {
  size: MascotSize
  speaking: boolean
  working: boolean
}

// WebKit (Safari, macOS app window) plays VP9 WebM without its alpha channel.
const VIDEO_ALPHA = !/AppleWebKit/.test(navigator.userAgent) || /Chrome|Chromium|Edg/.test(navigator.userAgent)

export function Mascot({ size, speaking, working }: Props) {
  const [appeared, setAppeared] = useState(!VIDEO_ALPHA)
  const cls = ['mascot', `mascot--${size}`, speaking && 'is-speaking', working && 'is-working', appeared && 'is-idle', !VIDEO_ALPHA && 'is-appearing']
    .filter(Boolean)
    .join(' ')
  return (
    <div className={cls} aria-hidden="true">
      {appeared ? (
        <img src="/mascot/idle.png" alt="" draggable={false} />
      ) : (
        <video
          src="/mascot/apparition.webm"
          poster="/mascot/idle.png"
          autoPlay
          muted
          playsInline
          onEnded={() => setAppeared(true)}
          onError={() => setAppeared(true)}
        />
      )}
    </div>
  )
}
