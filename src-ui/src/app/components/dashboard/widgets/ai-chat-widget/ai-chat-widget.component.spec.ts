import { ComponentFixture, TestBed } from '@angular/core/testing'
import { RouterTestingModule } from '@angular/router/testing'
import { allIcons, NgxBootstrapIconsModule } from 'ngx-bootstrap-icons'
import { provideMarkdown } from 'ngx-markdown'
import { EMPTY } from 'rxjs'
import { ChatService } from 'src/app/services/chat.service'
import { AiChatWidgetComponent } from './ai-chat-widget.component'

describe('AiChatWidgetComponent', () => {
  let component: AiChatWidgetComponent
  let fixture: ComponentFixture<AiChatWidgetComponent>

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        AiChatWidgetComponent,
        NgxBootstrapIconsModule.pick(allIcons),
        RouterTestingModule,
      ],
      providers: [
        provideMarkdown(),
        { provide: ChatService, useValue: { streamChat: () => EMPTY } },
      ],
    }).compileComponents()

    fixture = TestBed.createComponent(AiChatWidgetComponent)
    component = fixture.componentInstance
    fixture.detectChanges()
  })

  it('creates and seeds the chat panel with a welcome message', () => {
    expect(component).toBeTruthy()
    expect(component.welcome).toContain('Paperflow AI')
    const panel = fixture.nativeElement.querySelector('pngx-chat-panel')
    expect(panel).not.toBeNull()
  })
})
