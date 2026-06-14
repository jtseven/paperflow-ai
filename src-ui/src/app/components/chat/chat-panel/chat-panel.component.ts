import { CommonModule } from '@angular/common'
import {
  ChangeDetectorRef,
  Component,
  ElementRef,
  inject,
  Input,
  OnChanges,
  OnDestroy,
  OnInit,
  SimpleChanges,
  ViewChild,
} from '@angular/core'
import { FormsModule } from '@angular/forms'
import { Router, RouterModule } from '@angular/router'
import { LucideAngularModule } from 'lucide-angular'
import { NgxBootstrapIconsModule } from 'ngx-bootstrap-icons'
import { MarkdownModule } from 'ngx-markdown'
import { Subscription } from 'rxjs'
import { ChatHistoryService } from 'src/app/services/chat-history.service'
import {
  ChatEvent,
  ChatHistoryTurn,
  ChatMessage,
  ChatService,
  Citation,
} from 'src/app/services/chat.service'

const CITATION_MARKER_RE = /\[(\d+)\]/g

/**
 * How many recent turns to send as short-term memory. Mirrors the backend's
 * MAX_HISTORY_MESSAGES (paperless_ai/chat.py); the backend re-trims defensively.
 */
const CHAT_HISTORY_TURNS = 6

/**
 * Shared chat surface used by both the dashboard agentic widget (no
 * `documentId`) and the per-document chat (`documentId` set). Renders streamed
 * tokens as markdown, shows the agent's live search steps (collapsing into a
 * summary once the answer begins), and turns inline `[n]` markers into
 * clickable citations with a hover preview, listing only the documents the
 * answer actually used.
 */
@Component({
  selector: 'pngx-chat-panel',
  templateUrl: './chat-panel.component.html',
  styleUrls: ['./chat-panel.component.scss'],
  imports: [
    CommonModule,
    FormsModule,
    RouterModule,
    NgxBootstrapIconsModule,
    LucideAngularModule,
    MarkdownModule,
  ],
})
export class ChatPanelComponent implements OnInit, OnChanges, OnDestroy {
  /** When set, chat is scoped to this document; otherwise it is agentic. */
  @Input() documentId?: number
  /** Optional greeting shown as the first assistant message. */
  @Input() welcome: string | null = null
  @Input() placeholder: string = $localize`Ask me anything`

  @ViewChild('chatContainer') chatContainer!: ElementRef<HTMLDivElement>
  @ViewChild('chatInput') chatInput!: ElementRef<HTMLInputElement>

  public messages: ChatMessage[] = []
  public input = ''
  public loading = false

  public hoveredCitation: Citation | null = null
  public popoverTop = 0
  public popoverLeft = 0

  private chatService: ChatService = inject(ChatService)
  private history: ChatHistoryService = inject(ChatHistoryService)
  private router: Router = inject(Router)
  private cdr: ChangeDetectorRef = inject(ChangeDetectorRef)

  private streamSub?: Subscription
  private destroyed = false

  ngOnInit(): void {
    this.loadHistory()
  }

  ngOnDestroy(): void {
    this.destroyed = true
    this.streamSub?.unsubscribe()
  }

  ngOnChanges(changes: SimpleChanges): void {
    // The per-document chat reuses one panel and swaps documentId as the user
    // navigates; load that document's thread when it changes.
    if (changes['documentId'] && !changes['documentId'].firstChange) {
      this.loadHistory()
    }
  }

  private loadHistory(): void {
    const stored = this.history.load(this.history.key(this.documentId))
    if (stored?.length) {
      this.messages = stored
    } else {
      this.messages = this.welcome
        ? [{ role: 'assistant', content: this.welcome }]
        : []
    }
  }

  private persist(): void {
    this.history.save(this.history.key(this.documentId), this.messages)
  }

  /**
   * Build the short-term-memory window sent to the backend: the most recent
   * completed turns reduced to `{role, content}`. Skips in-flight/errored/empty
   * turns and drops the leading assistant greeting so history starts at a user
   * turn, then keeps only the last `CHAT_HISTORY_TURNS`.
   */
  private buildHistory(): ChatHistoryTurn[] {
    const usable = this.messages.filter(
      (m) => !m.isStreaming && !m.error && !!m.content
    )
    let start = 0
    while (start < usable.length && usable[start].role === 'assistant') {
      start++
    }
    return usable
      .slice(start)
      .slice(-CHAT_HISTORY_TURNS)
      .map((m) => ({ role: m.role, content: m.content }))
  }

  public get canClear(): boolean {
    return this.messages.some((m) => m.role === 'user')
  }

  public clear(): void {
    if (this.loading) {
      return
    }
    this.history.clear(this.history.key(this.documentId))
    this.messages = this.welcome
      ? [{ role: 'assistant', content: this.welcome }]
      : []
  }

  sendMessage(): void {
    const prompt = this.input.trim()
    if (prompt === '' || this.loading) {
      return
    }

    // Snapshot prior turns before pushing the new prompt so the history window
    // excludes the question we're about to ask.
    const history = this.buildHistory()

    this.messages.push({ role: 'user', content: prompt })
    this.input = ''
    this.focusInput()

    const assistantMessage: ChatMessage = {
      role: 'assistant',
      content: '',
      isStreaming: true,
      steps: [],
      citations: new Map(),
    }
    this.messages.push(assistantMessage)
    this.loading = true
    this.scrollToBottom()

    this.streamSub = this.chatService
      .streamChat(this.documentId ?? null, prompt, history)
      .subscribe({
        next: (event) => {
          this.handleEvent(event, assistantMessage)
          this.render()
          this.scrollToBottom()
        },
        error: () => {
          if (!assistantMessage.content) {
            assistantMessage.content = $localize`⚠️ Sorry, there was an error processing your message. Please try again.`
          }
          assistantMessage.error = true
          assistantMessage.isStreaming = false
          this.loading = false
          this.persist()
          this.render()
          this.scrollToBottom()
          this.focusInput()
        },
        complete: () => {
          assistantMessage.isStreaming = false
          this.loading = false
          this.persist()
          this.render()
          this.scrollToBottom()
          this.focusInput()
        },
      })
  }

  /**
   * Run change detection for this view explicitly.
   *
   * The chat stream is read from a `fetch` ReadableStream, whose reader promises
   * aren't reliably patched by zone.js, so streamed updates — and the DOM (plus
   * `(click)` listeners) of the views they render, such as the search-overview
   * toggle — land outside Angular's zone. Out-of-zone changes don't trigger
   * change detection on their own (the answer wouldn't render live; the toggle
   * appeared dead until some unrelated event ran CD). Anything that mutates view
   * state off the back of the stream, or from a listener created by it, calls
   * this so the view updates immediately and predictably.
   */
  private render(): void {
    if (!this.destroyed) {
      this.cdr.detectChanges()
    }
  }

  private handleEvent(event: ChatEvent, message: ChatMessage): void {
    switch (event.type) {
      case 'tool_call':
        message.steps = message.steps ?? []
        message.steps.push({
          id: event.id,
          query: event.query,
          status: 'running',
        })
        break
      case 'tool_result': {
        const step = message.steps?.find((s) => s.id === event.id)
        if (step) {
          step.status = 'done'
          step.count = event.count
          step.documents = event.documents
        }
        break
      }
      case 'citation':
        message.citations = message.citations ?? new Map()
        message.citations.set(event.marker, {
          marker: event.marker,
          documentId: event.document_id,
          title: event.title,
          snippet: event.snippet,
        })
        break
      case 'token':
        message.content += event.text
        break
      case 'error':
        message.content = event.message
        message.error = true
        break
      case 'done':
        break
    }
  }

  /**
   * Rewrite inline `[n]` markers into markdown links to the cited document so
   * they render as clickable citations (with the document title as a native
   * tooltip). Markers without a known citation are left as plain text.
   */
  public renderAnswer(message: ChatMessage): string {
    const citations = message.citations
    if (!citations?.size) {
      return message.content
    }
    // The model occasionally wraps markers in backticks (inline code); unwrap
    // them first so the substituted link isn't rendered as literal code.
    const content = message.content.replace(/`(\[\d+\])`/g, '$1')
    return content.replace(CITATION_MARKER_RE, (match, num: string) => {
      const citation = citations.get(+num)
      if (!citation) {
        return match
      }
      const title = (citation.title ?? '').replace(/"/g, "'")
      return `[\\[${num}\\]](/documents/${citation.documentId} "${title}")`
    })
  }

  /** Documents the answer actually cited (falls back to all for per-doc chat). */
  public citedReferences(message: ChatMessage): Citation[] {
    if (!message.citations?.size) {
      return []
    }
    const markers = new Set<number>()
    let match: RegExpExecArray | null
    const regex = new RegExp(CITATION_MARKER_RE)
    while ((match = regex.exec(message.content)) !== null) {
      markers.add(+match[1])
    }
    const all = [...message.citations.values()].sort(
      (a, b) => a.marker - b.marker
    )
    const used = all.filter((c) => markers.has(c.marker))
    if (used.length) {
      return used
    }
    // Per-document chat answers don't carry inline markers — show the sources
    // that were retrieved. Agentic answers show nothing if nothing was cited.
    return this.documentId != null ? all : []
  }

  /**
   * Expand/collapse a finished message's search overview. Persisted so the
   * chosen state survives a reload (the thread is restored from localStorage).
   *
   * Calls `render()` because this button is created while the answer streams in,
   * so its `(click)` listener is bound out-of-zone (see `render()`) and the
   * toggle would otherwise not refresh the view on its own.
   */
  public toggleSteps(message: ChatMessage): void {
    message.stepsExpanded = !message.stepsExpanded
    this.persist()
    this.render()
  }

  public showTyping(message: ChatMessage): boolean {
    return !!message.isStreaming && !message.content && !message.steps?.length
  }

  public showLiveSteps(message: ChatMessage): boolean {
    return !!message.isStreaming && !message.content && !!message.steps?.length
  }

  public onAnswerClick(event: MouseEvent): void {
    const anchor = (event.target as HTMLElement)?.closest<HTMLAnchorElement>(
      'a[href^="/documents/"]'
    )
    if (!anchor) {
      return
    }
    event.preventDefault()
    this.router.navigateByUrl(anchor.getAttribute('href') ?? anchor.pathname)
  }

  public onAnswerHover(event: MouseEvent, message: ChatMessage): void {
    const anchor = (event.target as HTMLElement)?.closest<HTMLAnchorElement>(
      'a[href^="/documents/"]'
    )
    if (!anchor || !message.citations?.size) {
      this.onAnswerLeave()
      return
    }
    const id = +(anchor.getAttribute('href')?.split('/').pop() ?? '')
    const citation = [...message.citations.values()].find(
      (c) => c.documentId === id
    )
    if (!citation) {
      this.onAnswerLeave()
      return
    }
    const containerRect =
      this.chatContainer?.nativeElement.getBoundingClientRect()
    const rect = anchor.getBoundingClientRect()
    this.popoverTop =
      rect.bottom - (containerRect?.top ?? 0) + this.scrollOffset() + 4
    this.popoverLeft = rect.left - (containerRect?.left ?? 0)
    this.hoveredCitation = citation
    // Same out-of-zone caveat as the toggle: this listener is bound while the
    // answer streams in, so refresh the popover explicitly.
    this.render()
  }

  public onAnswerLeave(): void {
    this.hoveredCitation = null
    this.render()
  }

  private scrollOffset(): number {
    return this.chatContainer?.nativeElement.scrollTop ?? 0
  }

  /**
   * Keep the cursor in the input so the user can keep replying without having
   * to click back into the box after each answer. Deferred a tick so it runs
   * after the view (re-)renders.
   */
  private focusInput(): void {
    setTimeout(() => this.chatInput?.nativeElement.focus())
  }

  private scrollToBottom(): void {
    setTimeout(() => {
      if (this.chatContainer) {
        this.chatContainer.nativeElement.scrollTop =
          this.chatContainer.nativeElement.scrollHeight
      }
    })
  }
}
