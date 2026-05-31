import { TestBed } from '@angular/core/testing'
import { ChatHistoryService } from './chat-history.service'
import { ChatMessage } from './chat.service'

describe('ChatHistoryService', () => {
  let service: ChatHistoryService

  beforeEach(() => {
    localStorage.clear()
    TestBed.configureTestingModule({ providers: [ChatHistoryService] })
    service = TestBed.inject(ChatHistoryService)
  })

  it('namespaces keys per context', () => {
    expect(service.key()).toContain('dashboard')
    expect(service.key(5)).toContain('doc:5')
    expect(service.key(5)).not.toEqual(service.key())
  })

  it('round-trips messages including the citation map', () => {
    const messages: ChatMessage[] = [
      { role: 'user', content: 'q' },
      {
        role: 'assistant',
        content: 'a [1]',
        isStreaming: false,
        citations: new Map([
          [1, { marker: 1, documentId: 9, title: 'Doc', snippet: 's' }],
        ]),
      },
    ]
    const key = service.key(9)
    service.save(key, messages)

    const restored = service.load(key)!
    expect(restored).toHaveLength(2)
    expect(restored[1].citations).toBeInstanceOf(Map)
    expect(restored[1].citations!.get(1)).toEqual({
      marker: 1,
      documentId: 9,
      title: 'Doc',
      snippet: 's',
    })
    expect(restored[1].isStreaming).toBe(false)
  })

  it('does not persist an in-flight assistant turn', () => {
    const key = service.key()
    service.save(key, [
      { role: 'user', content: 'q' },
      { role: 'assistant', content: '', isStreaming: true },
    ])
    const restored = service.load(key)!
    expect(restored).toHaveLength(1)
    expect(restored[0]).toMatchObject({ role: 'user', content: 'q' })
  })

  it('returns null for an unknown key and clears stored threads', () => {
    const key = service.key(1)
    expect(service.load(key)).toBeNull()
    service.save(key, [{ role: 'user', content: 'q' }])
    expect(service.load(key)).not.toBeNull()
    service.clear(key)
    expect(service.load(key)).toBeNull()
  })
})
