import { provideHttpClient, withInterceptorsFromDi } from '@angular/common/http'
import { provideHttpClientTesting } from '@angular/common/http/testing'
import { ComponentFixture, TestBed } from '@angular/core/testing'
import { RouterTestingModule } from '@angular/router/testing'
import { allIcons, NgxBootstrapIconsModule } from 'ngx-bootstrap-icons'
import { provideMarkdown } from 'ngx-markdown'
import { Subject } from 'rxjs'
import {
  CHAT_METADATA_DELIMITER,
  ChatService,
} from 'src/app/services/chat.service'
import { AiChatWidgetComponent } from './ai-chat-widget.component'

describe('AiChatWidgetComponent', () => {
  let component: AiChatWidgetComponent
  let fixture: ComponentFixture<AiChatWidgetComponent>
  let chatService: ChatService
  let mockStream$: Subject<string>

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        AiChatWidgetComponent,
        NgxBootstrapIconsModule.pick(allIcons),
        RouterTestingModule,
      ],
      providers: [
        provideHttpClient(withInterceptorsFromDi()),
        provideHttpClientTesting(),
        provideMarkdown(),
      ],
    }).compileComponents()

    fixture = TestBed.createComponent(AiChatWidgetComponent)
    component = fixture.componentInstance
    chatService = TestBed.inject(ChatService)
    mockStream$ = new Subject<string>()
    jest
      .spyOn(chatService, 'streamChat')
      .mockReturnValue(mockStream$.asObservable())
    fixture.detectChanges()
  })

  it('should create with a welcome message', () => {
    expect(component).toBeTruthy()
    expect(component.messages.length).toBe(1)
    expect(component.messages[0].role).toBe('assistant')
  })

  it('should send a message agentically (no document id) and stream the reply', () => {
    component.input = 'Hello'
    component.sendMessage()

    expect(chatService.streamChat).toHaveBeenCalledWith(null, 'Hello')
    // welcome + user + assistant placeholder
    expect(component.messages.length).toBe(3)
    expect(component.messages[1]).toEqual({ role: 'user', content: 'Hello' })
    expect(component.loading).toBe(true)

    mockStream$.next('Hi')
    expect(component.messages[2].content).toBe('Hi')
    mockStream$.next('Hi there')
    expect(component.messages[2].content).toBe('Hi there')

    mockStream$.complete()
    expect(component.loading).toBe(false)
    expect(component.messages[2].isStreaming).toBe(false)
  })

  it('should not send when input is empty or already loading', () => {
    component.input = '   '
    component.sendMessage()
    expect(chatService.streamChat).not.toHaveBeenCalled()

    component.input = 'Hello'
    component.loading = true
    component.sendMessage()
    expect(chatService.streamChat).not.toHaveBeenCalled()
  })

  it('should parse references from the metadata trailer without showing it', () => {
    component.input = 'Hello'
    component.sendMessage()

    mockStream$.next(
      `Hi there${CHAT_METADATA_DELIMITER}{"references":[{"id":42,"title":"Bread Recipe"}]}`
    )

    expect(component.messages[2].content).toBe('Hi there')
    expect(component.messages[2].references).toEqual([
      { id: 42, title: 'Bread Recipe' },
    ])
  })

  it('should render document reference links under assistant messages', () => {
    component.input = 'Hello'
    component.sendMessage()

    mockStream$.next(
      `Hi there${CHAT_METADATA_DELIMITER}{"references":[{"id":42,"title":"Bread Recipe"}]}`
    )
    mockStream$.complete()
    fixture.detectChanges()

    const link = fixture.nativeElement.querySelector('.chat-references a')
    expect(link.textContent).toContain('Bread Recipe')
    expect(link.getAttribute('href')).toContain('/documents/42')
  })

  it('should handle errors during streaming', () => {
    component.input = 'Hello'
    component.sendMessage()

    mockStream$.error('Error')
    expect(component.messages[2].content).toContain('⚠️')
    expect(component.loading).toBe(false)
    expect(component.messages[2].isStreaming).toBe(false)
  })
})
