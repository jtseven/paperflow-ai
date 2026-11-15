import { ComponentFixture, TestBed } from '@angular/core/testing'
import { NavigationEnd, Router } from '@angular/router'
import { RouterTestingModule } from '@angular/router/testing'
import { jest } from '@jest/globals'
import { provideMarkdown } from 'ngx-markdown'
import { EMPTY, of, Subject } from 'rxjs'
import { ChatService } from 'src/app/services/chat.service'
import { ChatComponent } from './chat.component'

describe('ChatComponent', () => {
  let component: ChatComponent
  let fixture: ComponentFixture<ChatComponent>
  let router: Router
  let routerEvents$: Subject<NavigationEnd>

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [RouterTestingModule, ChatComponent],
      providers: [
        provideMarkdown(),
        {
          provide: ChatService,
          useValue: {
            streamChat: () => EMPTY,
            getModels: () => of({ models: [], default_model: null }),
          },
        },
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

  it('keeps the conversation open when the nested model menu is used', async () => {
    fixture.detectChanges()
    fixture.nativeElement.querySelector('#chatDropdown').click()
    fixture.detectChanges()
    fixture.nativeElement.querySelector('.model-toggle').click()
    fixture.detectChanges()

    const refresh = fixture.nativeElement.querySelector('.refresh-models')
    refresh.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }))
    refresh.dispatchEvent(new MouseEvent('mouseup', { bubbles: true }))
    refresh.click()
    // ng-bootstrap defers dismissal until after the pointer events complete.
    await new Promise((resolve) => setTimeout(resolve, 0))
    fixture.detectChanges()
    expect(
      fixture.nativeElement.querySelector('[aria-labelledby="chatDropdown"]')
        .classList
    ).toContain('show')
    expect(
      fixture.nativeElement.querySelector('.model-menu').classList
    ).not.toContain('show')
  })
})
