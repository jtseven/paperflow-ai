import { inject, Injectable } from '@angular/core'
import { Meta } from '@angular/platform-browser'
import { CookieService } from 'ngx-cookie-service'
import { Observable } from 'rxjs'
import { environment } from 'src/environments/environment'

/**
 * Wire events streamed by the chat endpoint as newline-delimited JSON. The
 * `type` discriminators are mirrored from the backend (src/paperless_ai/chat.py)
 * — keep both sides in sync.
 */
export interface ChatTokenEvent {
  type: 'token'
  text: string
}

export interface ChatToolCallEvent {
  type: 'tool_call'
  id: string
  name: string
  query: string
}

export interface ChatToolResultDocument {
  id: number
  title: string
  marker?: number
}

export interface ChatToolResultEvent {
  type: 'tool_result'
  id: string
  name: string
  count: number
  documents: ChatToolResultDocument[]
}

export interface ChatCitationEvent {
  type: 'citation'
  marker: number
  document_id: number
  title: string
  snippet: string
}

export interface ChatErrorEvent {
  type: 'error'
  message: string
}

export interface ChatDoneEvent {
  type: 'done'
}

export type ChatEvent =
  | ChatTokenEvent
  | ChatToolCallEvent
  | ChatToolResultEvent
  | ChatCitationEvent
  | ChatErrorEvent
  | ChatDoneEvent

/** A document the answer drew on, resolved from a `[n]` citation marker. */
export interface Citation {
  marker: number
  documentId: number
  title: string
  snippet: string
}

/** A single retrieval the agent performed, shown live then collapsed. */
export interface ChatStep {
  id: string
  query: string
  status: 'running' | 'done'
  count?: number
  documents?: ChatToolResultDocument[]
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  isStreaming?: boolean
  error?: boolean
  steps?: ChatStep[]
  stepsExpanded?: boolean
  citations?: Map<number, Citation>
}

@Injectable({
  providedIn: 'root',
})
export class ChatService {
  private cookieService: CookieService = inject(CookieService)
  private meta: Meta = inject(Meta)

  /**
   * Stream a chat answer as structured events.
   *
   * With no `documentId` the backend runs an agentic chat across every document
   * the user may view; with one it answers about that single document. Uses the
   * Fetch API + a ReadableStream reader so tokens arrive incrementally and the
   * stream terminates cleanly (explicit `done`/reader-end and `error` events),
   * which the previous HttpClient `partialText` approach could not guarantee.
   */
  streamChat(
    documentId: number | null,
    prompt: string
  ): Observable<ChatEvent> {
    const body: { q: string; document_id?: number } = { q: prompt }
    if (documentId != null) {
      body.document_id = documentId
    }

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    }
    const csrfToken = this.getCsrfToken()
    if (csrfToken) {
      headers['X-CSRFToken'] = csrfToken
    }

    return new Observable<ChatEvent>((subscriber) => {
      const controller = new AbortController()

      fetch(`${environment.apiBaseUrl}documents/chat/`, {
        method: 'POST',
        body: JSON.stringify(body),
        headers,
        credentials: 'include',
        signal: controller.signal,
      })
        .then(async (response) => {
          if (!response.ok || !response.body) {
            throw new Error(`Chat request failed (${response.status})`)
          }

          const reader = response.body.getReader()
          const decoder = new TextDecoder()
          let buffer = ''

          // eslint-disable-next-line no-constant-condition
          while (true) {
            const { value, done } = await reader.read()
            if (done) {
              break
            }
            buffer += decoder.decode(value, { stream: true })

            let newlineIndex: number
            while ((newlineIndex = buffer.indexOf('\n')) >= 0) {
              const line = buffer.slice(0, newlineIndex).trim()
              buffer = buffer.slice(newlineIndex + 1)
              this.emit(subscriber, line)
            }
          }

          // Emit any trailing line not terminated by a newline.
          this.emit(subscriber, buffer.trim())
          subscriber.complete()
        })
        .catch((error) => {
          if (controller.signal.aborted) {
            return
          }
          subscriber.error(error)
        })

      return () => controller.abort()
    })
  }

  private emit(
    subscriber: { next: (event: ChatEvent) => void },
    line: string
  ): void {
    if (!line) {
      return
    }
    let event: ChatEvent
    try {
      event = JSON.parse(line) as ChatEvent
    } catch {
      return
    }
    subscriber.next(event)
  }

  private getCsrfToken(): string {
    let prefix = ''
    const tag = this.meta.getTag('name=cookie_prefix')
    if (tag) {
      prefix = tag.content
    }
    return this.cookieService.get(`${prefix}csrftoken`)
  }
}
