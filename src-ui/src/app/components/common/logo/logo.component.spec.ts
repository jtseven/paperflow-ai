import { ComponentFixture, TestBed } from '@angular/core/testing'

import { provideHttpClient, withInterceptorsFromDi } from '@angular/common/http'
import { provideHttpClientTesting } from '@angular/common/http/testing'
import { By } from '@angular/platform-browser'
import { SETTINGS_KEYS } from 'src/app/data/ui-settings'
import { SettingsService } from 'src/app/services/settings.service'
import { environment } from 'src/environments/environment'
import { LogoComponent } from './logo.component'

describe('LogoComponent', () => {
  let component: LogoComponent
  let fixture: ComponentFixture<LogoComponent>
  let settingsService: SettingsService

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [LogoComponent],
      providers: [
        provideHttpClient(withInterceptorsFromDi()),
        provideHttpClientTesting(),
      ],
    })
    settingsService = TestBed.inject(SettingsService)
    fixture = TestBed.createComponent(LogoComponent)
    component = fixture.componentInstance
    fixture.detectChanges()
  })

  it('should support extra classes', () => {
    expect(fixture.debugElement.queryAll(By.css('.foo'))).toHaveLength(0)
    component.extra_classes = 'foo'
    fixture.detectChanges()
    expect(fixture.debugElement.queryAll(By.css('.foo'))).toHaveLength(1)
  })

  it('should support setting height', () => {
    expect(fixture.debugElement.query(By.css('img')).attributes.style).toEqual(
      'height:6em'
    )
    component.height = '10em'
    fixture.detectChanges()
    expect(fixture.debugElement.query(By.css('img')).attributes.style).toEqual(
      'height:10em'
    )
  })

  it('should pick the logo variant for the active theme', () => {
    settingsService.set(SETTINGS_KEYS.DARK_MODE_USE_SYSTEM, false)
    settingsService.set(SETTINGS_KEYS.DARK_MODE_ENABLED, false)
    expect(component.defaultLogo).toContain('paperflow-logo-light.svg')
    settingsService.set(SETTINGS_KEYS.DARK_MODE_ENABLED, true)
    expect(component.defaultLogo).toContain('paperflow-logo-dark.svg')
  })

  it('should support getting custom logo', () => {
    settingsService.set(SETTINGS_KEYS.APP_LOGO, '/logo/test.png')
    expect(component.customLogo).toEqual(
      environment.apiBaseUrl.replace(/\/api\/$/, '/logo/test.png')
    )
  })
})
