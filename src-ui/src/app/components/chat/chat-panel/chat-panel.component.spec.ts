import { NgZone, SimpleChange } from '@angular/core'
import { ComponentFixture, TestBed } from '@angular/core/testing'
import { provideRouter, Router } from '@angular/router'
import { jest } from '@jest/globals'
import { provideMarkdown } from 'ngx-markdown'
import { from, Observable, of, Subject } from 'rxjs'
import { ChatEvent, ChatService } from 'src/app/services/chat.service'
import { ChatMarkdownPipe } from './chat-markdown.pipe'
import { ChatPanelComponent } from './chat-panel.component'

describe('ChatPanelComponent', () => {
  let component: ChatPanelComponent
  let fixture: ComponentFixture<ChatPanelComponent>
  let chatService: { streamChat: jest.Mock; getModels: jest.Mock }

  beforeEach(async () => {
    localStorage.clear()
    chatService = {
      streamChat: jest.fn(),
      getModels: jest
        .fn()
        .mockReturnValue(of({ models: [], default_model: null })),
    }
    await TestBed.configureTestingModule({
      imports: [ChatPanelComponent],
      providers: [
        provideMarkdown(),
        provideRouter([]),
        { provide: ChatService, useValue: chatService },
      ],
    }).compileComponents()

    fixture = TestBed.createComponent(ChatPanelComponent)
    component = fixture.componentInstance
    fixture.detectChanges()
  })

  function send(prompt: string, events: ChatEvent[]): void {
    chatService.streamChat.mockReturnValue(from(events))
    component.input = prompt
    component.sendMessage()
  }

  it('loads configured models and sends the chosen model', () => {
    chatService.getModels.mockReturnValue(
      of({
        models: [
          { id: 'anthropic:claude', provider: 'Claude', name: 'Claude' },
        ],
        default_model: 'anthropic:claude',
      })
    )
    component.loadModels()
    send('hello', [{ type: 'done' }])
    expect(chatService.streamChat).toHaveBeenCalledWith(
      null,
      'hello',
      [],
      'anthropic:claude'
    )
  })

  it('cancels a response and retries without duplicating the question', () => {
    const stream = new Subject<ChatEvent>()
    chatService.streamChat.mockReturnValue(stream)
    component.input = 'hello'
    component.sendMessage()
    stream.next({ type: 'token', text: 'partial' })
    component.stop()
    stream.next({ type: 'token', text: 'ignored' })
    expect(component.loading).toBe(false)
    expect(component.messages.at(-1).content).toBe('partial')
    chatService.streamChat.mockReturnValue(
      from([{ type: 'token', text: 'complete' }, { type: 'done' }])
    )
    component.retry()
    expect(component.messages.map((message) => message.content)).toEqual([
      'hello',
      'complete',
    ])
    expect(chatService.streamChat).toHaveBeenLastCalledWith(null, 'hello', [])
  })

  it('cancels the old document stream before loading a different thread', () => {
    const stream = new Subject<ChatEvent>()
    chatService.streamChat.mockReturnValue(stream)
    component.documentId = 1
    component.input = 'old question'
    component.sendMessage()
    component.documentId = 2
    component.ngOnChanges({ documentId: new SimpleChange(1, 2, false) })
    stream.next({ type: 'token', text: 'old answer' })
    expect(component.messages).toEqual([])
    expect(component.loading).toBe(false)
    expect(localStorage.getItem('pngx:chat:doc:2')).toBeNull()
    expect(localStorage.getItem('pngx:chat:doc:1')).toContain('old question')
  })

  it('shows a welcome message when configured', () => {
    component.welcome = 'Hi there'
    component.ngOnInit()
    expect(component.messages[0]).toEqual({
      role: 'assistant',
      content: 'Hi there',
    })
  })

  it('sends prior turns as history on the next message', () => {
    send('first question', [
      { type: 'token', text: 'first answer' },
      { type: 'done' },
    ])
    expect(chatService.streamChat).toHaveBeenNthCalledWith(
      1,
      null,
      'first question',
      []
    )

    send('second question', [{ type: 'done' }])
    expect(chatService.streamChat).toHaveBeenNthCalledWith(
      2,
      null,
      'second question',
      [
        { role: 'user', content: 'first question' },
        { role: 'assistant', content: 'first answer' },
      ]
    )
  })

  it('excludes the welcome greeting from history', () => {
    component.welcome = 'Hi there'
    component.ngOnInit()
    send('a question', [{ type: 'token', text: 'an answer' }, { type: 'done' }])
    expect(chatService.streamChat).toHaveBeenCalledWith(null, 'a question', [])
  })

  it('trims history to the six most recent turns', () => {
    for (let i = 0; i < 7; i++) {
      send(`q${i}`, [{ type: 'token', text: `a${i}` }, { type: 'done' }])
    }
    const sentHistory = chatService.streamChat.mock.calls.at(-1)![2]
    expect(sentHistory).toHaveLength(6)
    expect(sentHistory[0]).toEqual({ role: 'user', content: 'q3' })
    expect(sentHistory.at(-1)).toEqual({ role: 'assistant', content: 'a5' })
  })

  it('reduces a full event stream into a finished assistant message', () => {
    send('How much rent?', [
      { type: 'tool_call', id: 't1', name: 'search_documents', query: 'rent' },
      {
        type: 'tool_result',
        id: 't1',
        name: 'search_documents',
        count: 2,
        documents: [{ id: 5, title: 'Lease' }],
      },
      {
        type: 'citation',
        marker: 1,
        document_id: 5,
        title: 'Lease',
        snippet: 'Rent is 1200/mo',
      },
      { type: 'token', text: 'Your rent is 1200 [1]' },
      { type: 'done' },
    ])

    expect(chatService.streamChat).toHaveBeenCalledWith(
      null,
      'How much rent?',
      []
    )
    const assistant = component.messages[component.messages.length - 1]
    expect(assistant.content).toBe('Your rent is 1200 [1]')
    expect(assistant.isStreaming).toBe(false)
    expect(component.loading).toBe(false)

    const step = assistant.steps![0]
    expect(step.status).toBe('done')
    expect(step.count).toBe(2)

    expect(assistant.citations!.get(1)).toEqual({
      marker: 1,
      documentId: 5,
      title: 'Lease',
      snippet: 'Rent is 1200/mo',
    })
  })

  it('captures the documents found by each search', () => {
    send('How much rent?', [
      { type: 'tool_call', id: 't1', name: 'search_documents', query: 'rent' },
      {
        type: 'tool_result',
        id: 't1',
        name: 'search_documents',
        count: 2,
        documents: [
          { id: 5, title: 'Lease' },
          { id: 8, title: 'Addendum' },
        ],
      },
      { type: 'token', text: 'answer' },
      { type: 'done' },
    ])
    const assistant = component.messages[component.messages.length - 1]
    expect(assistant.steps![0].documents).toEqual([
      { id: 5, title: 'Lease' },
      { id: 8, title: 'Addendum' },
    ])
  })

  it('toggles and persists the search overview expanded state', () => {
    send('q', [
      { type: 'tool_call', id: 't1', name: 'search_documents', query: 'rent' },
      {
        type: 'tool_result',
        id: 't1',
        name: 'search_documents',
        count: 1,
        documents: [{ id: 5, title: 'Lease' }],
      },
      { type: 'token', text: 'answer' },
      { type: 'done' },
    ])
    const assistant = component.messages[component.messages.length - 1]
    expect(assistant.stepsExpanded).toBeFalsy()

    component.toggleSteps(assistant)
    expect(assistant.stepsExpanded).toBe(true)

    // Persisted so a reload restores the expanded state.
    const reloaded = component['history'].load(
      component['history'].key(undefined)
    )
    expect(reloaded?.at(-1)?.stepsExpanded).toBe(true)

    component.toggleSteps(assistant)
    expect(assistant.stepsExpanded).toBe(false)
  })

  it('expands the search overview on a real click bound out-of-zone', () => {
    // Reproduce production: the overview's toggle button is created while the
    // answer streams in, i.e. during change detection that runs outside the
    // Angular zone, so its (click) listener is bound — and later fires — out of
    // zone and won't trigger CD on its own. The component must refresh itself.
    send('q', [
      { type: 'tool_call', id: 't1', name: 'search_documents', query: 'rent' },
      {
        type: 'tool_result',
        id: 't1',
        name: 'search_documents',
        count: 1,
        documents: [{ id: 5, title: 'Lease' }],
      },
      { type: 'token', text: 'answer' },
      { type: 'done' },
    ])

    const zone = TestBed.inject(NgZone)
    // Bind the template (and the click listener) outside the Angular zone.
    zone.runOutsideAngular(() => fixture.detectChanges())

    const button: HTMLButtonElement =
      fixture.nativeElement.querySelector('.steps-toggle')
    expect(button).toBeTruthy()
    expect(fixture.nativeElement.querySelector('.steps-list')).toBeNull()

    // A real click runs the handler in the captured (root) zone. Deliberately
    // no fixture.detectChanges() afterwards — the view must update by itself.
    button.click()

    expect(fixture.nativeElement.querySelector('.steps-list')).toBeTruthy()
  })

  it('rewrites cited [n] markers into document links and leaves unknown ones', () => {
    send('q', [
      {
        type: 'citation',
        marker: 1,
        document_id: 9,
        title: 'Report',
        snippet: 's',
      },
      { type: 'token', text: 'See [1] but not [2]' },
      { type: 'done' },
    ])
    const message = component.messages[component.messages.length - 1]
    const rendered = new ChatMarkdownPipe().transform(
      message.content,
      message.citations
    )
    expect(rendered).toContain('href="/documents/9" title="Report"')
    expect(rendered).toContain('not [2]')
  })

  it('unwraps backtick-wrapped markers so they render as links', () => {
    send('q', [
      {
        type: 'citation',
        marker: 1,
        document_id: 9,
        title: 'Report',
        snippet: 's',
      },
      { type: 'token', text: 'As noted `[1]` in the file' },
      { type: 'done' },
    ])
    const message = component.messages[component.messages.length - 1]
    const rendered = new ChatMarkdownPipe().transform(
      message.content,
      message.citations
    )
    expect(rendered).toContain('href="/documents/9" title="Report"')
    expect(rendered).not.toContain('`[1]`')
  })

  it('lists only the documents actually cited in the answer (agentic)', () => {
    send('q', [
      {
        type: 'citation',
        marker: 1,
        document_id: 1,
        title: 'Used',
        snippet: 's',
      },
      {
        type: 'citation',
        marker: 2,
        document_id: 2,
        title: 'Unused',
        snippet: 's',
      },
      { type: 'token', text: 'Only [1] is referenced' },
      { type: 'done' },
    ])
    const message = component.messages[component.messages.length - 1]
    const cited = component.citedReferences(message)
    expect(cited.map((c) => c.documentId)).toEqual([1])
  })

  it('falls back to all sources for per-document chat without inline markers', () => {
    component.documentId = 7
    send('q', [
      {
        type: 'citation',
        marker: 1,
        document_id: 7,
        title: 'This doc',
        snippet: 's',
      },
      { type: 'token', text: 'An answer with no markers' },
      { type: 'done' },
    ])
    const message = component.messages[component.messages.length - 1]
    expect(component.citedReferences(message).map((c) => c.documentId)).toEqual(
      [7]
    )
    expect(chatService.streamChat).toHaveBeenCalledWith(7, 'q', [])
  })

  it('shows progress and keeps tool activity visible while text streams', () => {
    const stream = new Subject<ChatEvent>()
    chatService.streamChat.mockReturnValue(stream)
    component.input = 'q'
    component.sendMessage()
    fixture.detectChanges()
    const status = () =>
      fixture.nativeElement.querySelector('.chat-activity')?.textContent
    expect(status()).toContain('Preparing your question')
    stream.next({ type: 'status', phase: 'thinking' })
    expect(status()).toContain('Thinking')
    stream.next({
      type: 'tool_call',
      id: 't1',
      name: 'search_documents',
      query: 'rent',
    })
    expect(status()).toContain('Searching documents')
    expect(
      fixture.nativeElement.querySelector('.step-item').textContent
    ).toContain('rent')
    stream.next({ type: 'token', text: 'An answer' })
    expect(fixture.nativeElement.querySelector('.steps-list')).toBeTruthy()
    stream.next({
      type: 'tool_result',
      id: 't1',
      name: 'search_documents',
      count: 1,
      documents: [{ id: 7, title: 'Lease' }],
    })
    expect(status()).toContain('Thinking')
    expect(
      fixture.nativeElement.querySelector('.step-doc').textContent
    ).toContain('Lease')
    stream.next({ type: 'token', text: ' with a source' })
    stream.next({ type: 'done' })
    expect(status()).toBeUndefined()
    expect(component.loading).toBe(false)
    expect(fixture.nativeElement.querySelector('.steps-list')).toBeNull()
    expect(
      fixture.nativeElement.querySelector('.answer').textContent
    ).toContain('An answer with a source')
  })

  it('renders Markdown before completion, including split tokens and late citations', () => {
    jest.useFakeTimers()
    const stream = new Subject<ChatEvent>()
    chatService.streamChat.mockReturnValue(stream)
    component.input = 'q'
    component.sendMessage()
    const zone = TestBed.inject(NgZone)
    const emit = (text: string) =>
      zone.runOutsideAngular(() => stream.next({ type: 'token', text }))
    emit('## Summary\n\n**Hel')
    jest.advanceTimersByTime(32)
    expect(fixture.nativeElement.querySelector('.answer h2').textContent).toBe(
      'Summary'
    )
    emit('lo** [1]\n\n- First\n- Second\n\n```ts\nconst x = 1')
    jest.advanceTimersByTime(32)
    expect(
      fixture.nativeElement.querySelector('.answer strong').textContent
    ).toBe('Hello')
    expect(fixture.nativeElement.querySelectorAll('.answer li')).toHaveLength(2)
    expect(
      fixture.nativeElement.querySelector('.answer pre code').textContent
    ).toContain('const x = 1')
    stream.next({
      type: 'citation',
      marker: 1,
      document_id: 9,
      title: 'Report',
      snippet: 's',
    })
    expect(
      fixture.nativeElement.querySelector('.answer a').getAttribute('href')
    ).toBe('/documents/9')
    expect(component.loading).toBe(true)
    stream.next({ type: 'done' })
    jest.runOnlyPendingTimers()
    jest.useRealTimers()
  })

  it('marks unfinished tools interrupted and preserves partial Markdown on failure', () => {
    const stream = new Subject<ChatEvent>()
    chatService.streamChat.mockReturnValue(stream)
    component.input = 'q'
    component.sendMessage()
    stream.next({
      type: 'tool_call',
      id: 'r1',
      name: 'read_document',
      query: '9',
    })
    expect(
      fixture.nativeElement.querySelector('.chat-activity').textContent
    ).toContain('Reading document')
    stream.next({ type: 'token', text: '**Partial answer**' })
    stream.error(new Error('connection lost'))
    const message = component.messages.at(-1)!
    expect(message.steps[0].status).toBe('interrupted')
    expect(message.content).toBe('**Partial answer**')
    expect(fixture.nativeElement.querySelector('.chat-activity')).toBeNull()
    expect(
      fixture.nativeElement.querySelector('.answer strong').textContent
    ).toBe('Partial answer')
  })

  it('handles an error event and stops streaming', () => {
    send('q', [{ type: 'error', message: 'It broke' }, { type: 'done' }])
    const message = component.messages[component.messages.length - 1]
    expect(message.error).toBe(true)
    expect(message.content).toBe('It broke')
    expect(message.isStreaming).toBe(false)
  })

  it('shows a fallback message when the request errors out', () => {
    chatService.streamChat.mockReturnValue(
      new Observable<ChatEvent>((subscriber) =>
        subscriber.error(new Error('network'))
      )
    )
    component.input = 'q'
    component.sendMessage()
    const message = component.messages[component.messages.length - 1]
    expect(message.error).toBe(true)
    expect(message.content).toContain('error')
    expect(component.loading).toBe(false)
  })

  it('persists a finished turn and restores it on a fresh panel', () => {
    component.welcome = 'Hello'
    component.ngOnInit()
    send('What is X?', [{ type: 'token', text: 'X is Y' }, { type: 'done' }])

    // A freshly created panel (e.g. after refresh) restores the thread.
    const fixture2 = TestBed.createComponent(ChatPanelComponent)
    const restored = fixture2.componentInstance
    restored.ngOnInit()
    expect(restored.messages.map((m) => m.content)).toEqual([
      'Hello',
      'What is X?',
      'X is Y',
    ])
    expect(restored.messages.every((m) => !m.isStreaming)).toBe(true)
  })

  it('scopes history per document', () => {
    component.documentId = 1
    component.ngOnInit()
    send('doc one question', [{ type: 'token', text: 'a' }, { type: 'done' }])

    const other = TestBed.createComponent(ChatPanelComponent).componentInstance
    other.documentId = 2
    other.ngOnInit()
    expect(other.messages).toEqual([])
  })

  it('clears the conversation and storage', () => {
    component.welcome = 'Hello'
    component.ngOnInit()
    send('q', [{ type: 'token', text: 'a' }, { type: 'done' }])
    expect(component.canClear).toBe(true)

    component.clear()
    expect(component.messages).toEqual([
      { role: 'assistant', content: 'Hello' },
    ])
    expect(component.canClear).toBe(false)

    const fresh = TestBed.createComponent(ChatPanelComponent).componentInstance
    fresh.welcome = 'Hello'
    fresh.ngOnInit()
    expect(fresh.messages).toEqual([{ role: 'assistant', content: 'Hello' }])
  })

  it('navigates via the router when a citation link is clicked', () => {
    const router = TestBed.inject(Router)
    const navigate = jest.spyOn(router, 'navigateByUrl').mockResolvedValue(true)
    const anchor = document.createElement('a')
    anchor.setAttribute('href', '/documents/12')
    const event = { target: anchor, preventDefault: jest.fn() } as any
    component.onAnswerClick(event)
    expect(event.preventDefault).toHaveBeenCalled()
    expect(navigate).toHaveBeenCalledWith('/documents/12')
  })
})
