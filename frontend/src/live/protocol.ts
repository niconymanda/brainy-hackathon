/**
 * Front <-> back WebSocket contract (JSON, one object per message).
 * Back -> front events mirror brainy/agent/events.py (AgentStep, NeedsUser,
 * ConfirmRequest, Done, AgentError) plus STT / voice / history events.
 * See frontend/context/05-interface-back.md.
 */
import type { HistoryItem } from '../types'

export type ServerEvent =
  | { type: 'idle' }
  | { type: 'listening' }
  | { type: 'transcript'; text: string; final: boolean }
  | { type: 'say'; text: string }
  | { type: 'agent_step'; narration: string; action: string }
  | { type: 'needs_user'; question: string }
  | { type: 'confirm_request'; summary: string }
  | { type: 'done'; result: string; ok?: boolean }
  | { type: 'error'; reason: string; suggestion: string }
  | { type: 'history'; items: HistoryItem[] }

export type ClientEvent =
  | { type: 'start_listening' }
  | { type: 'stop_listening' }
  | { type: 'user_text'; text: string }
  | { type: 'confirm'; answer: 'oui' | 'non' }
