import { useState } from 'react'
import type { MascotSize } from '../types'

interface Props {
  size: MascotSize
  speaking: boolean
  working: boolean
}

export function Mascot({ size, speaking, working }: Props) {
  const [appeared, setAppeared] = useState(false)
  const cls = ['mascot', `mascot--${size}`, speaking && 'is-speaking', working && 'is-working', appeared && 'is-idle']
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
