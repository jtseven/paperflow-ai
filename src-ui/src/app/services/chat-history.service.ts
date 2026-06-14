import { Injectable } from '@angular/core'
import { ChatMessage, ChatStep, Citation } from './chat.service'

interface StoredMessage {
  role: 'user' | 'assistant'
  content: string
  error?: boolean
  steps?: ChatStep[]
  stepsExpanded?: boolean
  citations?: [number, Citation][]
}

/**
 * Persists chat threads in localStorage so they survive a page refresh or
 * navigating away and back. Threads are namespaced per context — one per
 * document plus one for the dashboard agentic chat — and can be cleared.
 */
@Injectable({
  providedIn: 'root',
})
export class ChatHistoryService {
  private readonly prefix = 'pngx:chat:'

  /** Storage key for a chat context (a document id, or the dashboard chat). */
  key(documentId?: number): string {
    return documentId != null
      ? `${this.prefix}doc:${documentId}`
      : `${this.prefix}dashboard`
  }

  load(key: string): ChatMessage[] | null {
    try {
      const raw = localStorage.getItem(key)
      if (!raw) {
        return null
      }
      const stored = JSON.parse(raw) as StoredMessage[]
      return stored.map((message) => ({
        role: message.role,
        content: message.content,
        error: message.error,
        steps: message.steps,
        stepsExpanded: message.stepsExpanded,
        citations: message.citations ? new Map(message.citations) : undefined,
        isStreaming: false,
      }))
    } catch {
      return null
    }
  }

  save(key: string, messages: ChatMessage[]): void {
    try {
      const stored: StoredMessage[] = messages
        // Don't persist an in-flight assistant turn.
        .filter((m) => !(m.role === 'assistant' && m.isStreaming))
        .map((m) => ({
          role: m.role,
          content: m.content,
          error: m.error,
          steps: m.steps,
          stepsExpanded: m.stepsExpanded,
          citations: m.citations ? [...m.citations.entries()] : undefined,
        }))
      localStorage.setItem(key, JSON.stringify(stored))
    } catch {
      // Ignore quota / serialization errors — history is best-effort.
    }
  }

  clear(key: string): void {
    try {
      localStorage.removeItem(key)
    } catch {
      // Ignore.
    }
  }
}
