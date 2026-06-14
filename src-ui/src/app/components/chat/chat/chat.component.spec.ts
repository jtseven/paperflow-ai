import { ComponentFixture, TestBed } from '@angular/core/testing'
import { NavigationEnd, Router } from '@angular/router'
import { RouterTestingModule } from '@angular/router/testing'
import { allIcons, NgxBootstrapIconsModule } from 'ngx-bootstrap-icons'
import { provideMarkdown } from 'ngx-markdown'
import { EMPTY, Subject } from 'rxjs'
import { ChatService } from 'src/app/services/chat.service'
import { ChatComponent } from './chat.component'

describe('ChatComponent', () => {
  let component: ChatComponent
  let fixture: ComponentFixture<ChatComponent>
  let router: Router
  let routerEvents$: Subject<NavigationEnd>

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        NgxBootstrapIconsModule.pick(allIcons),
        RouterTestingModule,
        ChatComponent,
      ],
      providers: [
        provideMarkdown(),
        { provide: ChatService, useValue: { streamChat: () => EMPTY } },
      ],
    }).compileComponents()

    fixture = TestBed.createComponent(ChatComponent)
    component = fixture.componentInstance
    router = TestBed.inject(Router)
    routerEvents$ = new Subject<NavigationEnd>()
    jest
      .spyOn(router, 'events', 'get')
      .mockReturnValue(routerEvents$.asObservable())
  })

  it('derives the document id from the current document route', () => {
    jest.spyOn(router, 'url', 'get').mockReturnValue('/documents/42')
    component.ngOnInit()
    expect(component.documentId).toBe(42)
    expect(component.placeholder).toContain('this document')
  })

  it('clears the document id when navigating away from a document', () => {
    jest.spyOn(router, 'url', 'get').mockReturnValue('/dashboard')
    component.ngOnInit()
    expect(component.documentId).toBeUndefined()
    expect(component.placeholder).toContain('a document')

    routerEvents$.next(new NavigationEnd(1, '/documents/7', '/documents/7'))
    expect(component.documentId).toBe(7)
  })

  it('renders the shared chat panel', () => {
    jest.spyOn(router, 'url', 'get').mockReturnValue('/documents/3')
    fixture.detectChanges()
    expect(
      fixture.nativeElement.querySelector('pngx-chat-panel')
    ).not.toBeNull()
  })
})
