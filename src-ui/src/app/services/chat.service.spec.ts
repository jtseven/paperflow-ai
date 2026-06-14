import { TestBed } from '@angular/core/testing'
import { Meta } from '@angular/platform-browser'
import { CookieService } from 'ngx-cookie-service'
import { environment } from 'src/environments/environment'
import { ChatEvent, ChatService } from './chat.service'

/**
 * Build a fake `fetch` Response whose body reader yields the given string
 * chunks. Chunk boundaries are deliberately arbitrary so tests can split a
 * single NDJSON line across reads.
 */
function fakeResponse(chunks: string[], ok = true, status = 200): Response {
  const encoder = new TextEncoder()
  const queue = chunks.map((chunk) => encoder.encode(chunk))
  let index = 0
  const reader = {
    read: () =>
      Promise.resolve(
        index < queue.length
          ? { value: queue[index++], done: false }
          : { value: undefined, done: true }
      ),
  }
  return {
    ok,
    status,
    body: { getReader: () => reader },
  } as unknown as Response
}

describe('ChatService', () => {
  let service: ChatService
  let cookieGet: jest.Mock
  let fetchMock: jest.Mock
  const originalFetch = globalThis.fetch

  beforeEach(() => {
    cookieGet = jest.fn().mockReturnValue('csrf-token-value')
    fetchMock = jest.fn()
    globalThis.fetch = fetchMock as unknown as typeof fetch
    TestBed.configureTestingModule({
      providers: [
        ChatService,
        { provide: CookieService, useValue: { get: cookieGet } },
        { provide: Meta, useValue: { getTag: () => null } },
      ],
    })
    service = TestBed.inject(ChatService)
  })

  afterEach(() => {
    globalThis.fetch = originalFetch
    jest.restoreAllMocks()
  })

  it('parses NDJSON events split across chunk boundaries', (done) => {
    const events: ChatEvent[] = []
    const blob =
      '{"type":"tool_call","id":"t1","name":"search_documents","query":"rent"}\n' +
      '{"type":"token","text":"Hello "}\n{"type":"token","text":"world"}\n' +
      '{"type":"done"}\n'
    // Re-chunk so lines are split mid-JSON.
    const chunks = [blob.slice(0, 30), blob.slice(30, 95), blob.slice(95)]

    fetchMock.mockResolvedValue(fakeResponse(chunks))

    service.streamChat(null, 'How much rent?').subscribe({
      next: (event) => events.push(event),
      complete: () => {
        expect(events).toEqual([
          {
            type: 'tool_call',
            id: 't1',
            name: 'search_documents',
            query: 'rent',
          },
          { type: 'token', text: 'Hello ' },
          { type: 'token', text: 'world' },
          { type: 'done' },
        ])
        expect(fetchMock).toHaveBeenCalledWith(
          `${environment.apiBaseUrl}documents/chat/`,
          expect.objectContaining({
            method: 'POST',
            credentials: 'include',
            headers: expect.objectContaining({
              'Content-Type': 'application/json',
              'X-CSRFToken': 'csrf-token-value',
            }),
          })
        )
        const init = fetchMock.mock.calls[0][1] as RequestInit
        expect(JSON.parse(init.body as string)).toEqual({ q: 'How much rent?' })
        done()
      },
    })
  })

  it('includes document_id when provided', (done) => {
    fetchMock.mockResolvedValue(fakeResponse(['{"type":"done"}\n']))

    service.streamChat(42, 'About this doc?').subscribe({
      complete: () => {
        const init = fetchMock.mock.calls[0][1] as RequestInit
        expect(JSON.parse(init.body as string)).toEqual({
          q: 'About this doc?',
          document_id: 42,
        })
        done()
      },
    })
  })

  it('includes history when provided and omits it when empty', (done) => {
    fetchMock.mockResolvedValue(fakeResponse(['{"type":"done"}\n']))

    const history = [
      { role: 'user' as const, content: 'first question' },
      { role: 'assistant' as const, content: 'first answer' },
    ]

    service.streamChat(null, 'follow up', history).subscribe({
      complete: () => {
        const init = fetchMock.mock.calls[0][1] as RequestInit
        expect(JSON.parse(init.body as string)).toEqual({
          q: 'follow up',
          history,
        })

        // A second call with no history must not include the key at all.
        service.streamChat(null, 'no history here').subscribe({
          complete: () => {
            const init2 = fetchMock.mock.calls[1][1] as RequestInit
            expect(JSON.parse(init2.body as string)).toEqual({
              q: 'no history here',
            })
            done()
          },
        })
      },
    })
  })

  it('errors when the response is not ok', (done) => {
    fetchMock.mockResolvedValue(fakeResponse([], false, 403))

    service.streamChat(null, 'hi').subscribe({
      next: () => fail('should not emit'),
      error: (error) => {
        expect(error).toBeInstanceOf(Error)
        done()
      },
    })
  })

  it('ignores malformed lines but keeps valid events', (done) => {
    const events: ChatEvent[] = []
    fetchMock.mockResolvedValue(
      fakeResponse([
        'not-json\n{"type":"token","text":"ok"}\n{"type":"done"}\n',
      ])
    )

    service.streamChat(null, 'hi').subscribe({
      next: (event) => events.push(event),
      complete: () => {
        expect(events).toEqual([
          { type: 'token', text: 'ok' },
          { type: 'done' },
        ])
        done()
      },
    })
  })
})
