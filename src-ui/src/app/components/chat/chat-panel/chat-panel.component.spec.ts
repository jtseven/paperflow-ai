import { ComponentFixture, TestBed } from '@angular/core/testing'
import { Router } from '@angular/router'
import { provideMarkdown } from 'ngx-markdown'
import { from, Observable, Subject } from 'rxjs'
import { ChatEvent, ChatService } from 'src/app/services/chat.service'
import { ChatPanelComponent } from './chat-panel.component'

describe('ChatPanelComponent', () => {
  let component: ChatPanelComponent
  let fixture: ComponentFixture<ChatPanelComponent>
  let chatService: { streamChat: jest.Mock }
  let router: { navigateByUrl: jest.Mock }

  beforeEach(async () => {
    localStorage.clear()
    chatService = { streamChat: jest.fn() }
    router = { navigateByUrl: jest.fn() }
    await TestBed.configureTestingModule({
      imports: [ChatPanelComponent],
      providers: [
        provideMarkdown(),
        { provide: ChatService, useValue: chatService },
        { provide: Router, useValue: router },
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

  it('shows a welcome message when configured', () => {
    component.welcome = 'Hi there'
    component.ngOnInit()
    expect(component.messages[0]).toEqual({
      role: 'assistant',
      content: 'Hi there',
    })
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

    expect(chatService.streamChat).toHaveBeenCalledWith(null, 'How much rent?')
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
    const rendered = component.renderAnswer(message)
    expect(rendered).toContain('(/documents/9 "Report")')
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
    const rendered = component.renderAnswer(message)
    expect(rendered).toContain('(/documents/9 "Report")')
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
    expect(component.citedReferences(message).map((c) => c.documentId)).toEqual([
      7,
    ])
    expect(chatService.streamChat).toHaveBeenCalledWith(7, 'q')
  })

  it('shows the typing animation only before steps or content', () => {
    const stream = new Subject<ChatEvent>()
    chatService.streamChat.mockReturnValue(stream as Observable<ChatEvent>)
    component.input = 'q'
    component.sendMessage()
    const message = component.messages[component.messages.length - 1]

    expect(component.showTyping(message)).toBe(true)
    stream.next({
      type: 'tool_call',
      id: 't1',
      name: 'search_documents',
      query: 'x',
    })
    expect(component.showTyping(message)).toBe(false)
    expect(component.showLiveSteps(message)).toBe(true)
    stream.next({ type: 'token', text: 'hello' })
    expect(component.showLiveSteps(message)).toBe(false)
    stream.complete()
  })

  it('handles an error event and stops streaming', () => {
    send('q', [
      { type: 'error', message: 'It broke' },
      { type: 'done' },
    ])
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
    send('What is X?', [
      { type: 'token', text: 'X is Y' },
      { type: 'done' },
    ])

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
    expect(component.messages).toEqual([{ role: 'assistant', content: 'Hello' }])
    expect(component.canClear).toBe(false)

    const fresh = TestBed.createComponent(ChatPanelComponent).componentInstance
    fresh.welcome = 'Hello'
    fresh.ngOnInit()
    expect(fresh.messages).toEqual([{ role: 'assistant', content: 'Hello' }])
  })

  it('navigates via the router when a citation link is clicked', () => {
    const anchor = document.createElement('a')
    anchor.setAttribute('href', '/documents/12')
    const event = { target: anchor, preventDefault: jest.fn() } as any
    component.onAnswerClick(event)
    expect(event.preventDefault).toHaveBeenCalled()
    expect(router.navigateByUrl).toHaveBeenCalledWith('/documents/12')
  })
})
