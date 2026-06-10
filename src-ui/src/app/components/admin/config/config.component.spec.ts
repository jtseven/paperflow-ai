import { ComponentFixture, TestBed } from '@angular/core/testing'

import { provideHttpClient, withInterceptorsFromDi } from '@angular/common/http'
import { provideHttpClientTesting } from '@angular/common/http/testing'
import { FormsModule, ReactiveFormsModule } from '@angular/forms'
import { BrowserModule } from '@angular/platform-browser'
import { NgbModule } from '@ng-bootstrap/ng-bootstrap'
import { NgSelectModule } from '@ng-select/ng-select'
import { NgxBootstrapIconsModule, allIcons } from 'ngx-bootstrap-icons'
import { of, throwError } from 'rxjs'
import {
  OutputTypeConfig,
  PaperlessConfigOptions,
} from 'src/app/data/paperless-config'
import { ConfigService } from 'src/app/services/config.service'
import { SettingsService } from 'src/app/services/settings.service'
import { ToastService } from 'src/app/services/toast.service'
import { FileComponent } from '../../common/input/file/file.component'
import { NumberComponent } from '../../common/input/number/number.component'
import { SelectComponent } from '../../common/input/select/select.component'
import { SwitchComponent } from '../../common/input/switch/switch.component'
import { TextComponent } from '../../common/input/text/text.component'
import { PageHeaderComponent } from '../../common/page-header/page-header.component'
import { ConfigComponent } from './config.component'

describe('ConfigComponent', () => {
  let component: ConfigComponent
  let fixture: ComponentFixture<ConfigComponent>
  let configService: ConfigService
  let toastService: ToastService
  let settingService: SettingsService

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [
        BrowserModule,
        NgbModule,
        NgSelectModule,
        FormsModule,
        ReactiveFormsModule,
        NgxBootstrapIconsModule.pick(allIcons),
        ConfigComponent,
        TextComponent,
        SelectComponent,
        NumberComponent,
        SwitchComponent,
        FileComponent,
        PageHeaderComponent,
      ],
      providers: [
        provideHttpClient(withInterceptorsFromDi()),
        provideHttpClientTesting(),
      ],
    }).compileComponents()

    configService = TestBed.inject(ConfigService)
    toastService = TestBed.inject(ToastService)
    settingService = TestBed.inject(SettingsService)
    fixture = TestBed.createComponent(ConfigComponent)
    component = fixture.componentInstance
    fixture.detectChanges()
  })

  it('should load config on init, show error if necessary', () => {
    const getSpy = jest.spyOn(configService, 'getConfig')
    const errorSpy = jest.spyOn(toastService, 'showError')
    getSpy.mockReturnValueOnce(
      throwError(() => new Error('Error getting config'))
    )
    component.ngOnInit()
    expect(getSpy).toHaveBeenCalled()
    expect(errorSpy).toHaveBeenCalled()
    getSpy.mockReturnValueOnce(
      of({ output_type: OutputTypeConfig.PDF_A } as any)
    )
    component.ngOnInit()
    expect(component.initialConfig).toEqual({
      output_type: OutputTypeConfig.PDF_A,
    })
  })

  it('should save config, show error if necessary', () => {
    const saveSpy = jest.spyOn(configService, 'saveConfig')
    const errorSpy = jest.spyOn(toastService, 'showError')
    saveSpy.mockReturnValueOnce(
      throwError(() => new Error('Error saving config'))
    )
    component.saveConfig()
    expect(saveSpy).toHaveBeenCalled()
    expect(errorSpy).toHaveBeenCalled()
    saveSpy.mockReturnValueOnce(
      of({ output_type: OutputTypeConfig.PDF_A } as any)
    )
    component.saveConfig()
    expect(component.initialConfig).toEqual({
      output_type: OutputTypeConfig.PDF_A,
    })
  })

  it('should support discard changes', () => {
    component.initialConfig = { output_type: OutputTypeConfig.PDF_A2 } as any
    component.configForm.patchValue({ output_type: OutputTypeConfig.PDF_A })
    component.discardChanges()
    expect(component.configForm.get('output_type').value).toEqual(
      OutputTypeConfig.PDF_A2
    )
  })

  it('should support JSON validation for e.g. user_args', () => {
    component.configForm.patchValue({ user_args: '{ foo bar }' })
    expect(component.errors['user_args']).toEqual('Invalid JSON')
    component.configForm.patchValue({ user_args: '{ "foo": "bar" }' })
    expect(component.errors['user_args']).toBeNull()
  })

  it('should upload file, show error if necessary', () => {
    const uploadSpy = jest.spyOn(configService, 'uploadFile')
    const errorSpy = jest.spyOn(toastService, 'showError')
    uploadSpy.mockReturnValueOnce(
      throwError(() => new Error('Error uploading file'))
    )
    component.uploadFile(new File([], 'test.png'), 'app_logo')
    expect(uploadSpy).toHaveBeenCalled()
    expect(errorSpy).toHaveBeenCalled()
    uploadSpy.mockReturnValueOnce(
      of({ app_logo: 'https://example.com/logo/test.png' } as any)
    )
    component.uploadFile(new File([], 'test.png'), 'app_logo')
    expect(component.initialConfig).toEqual({
      app_logo: 'https://example.com/logo/test.png',
    })
  })

  it('should refresh ui settings after save or upload', () => {
    const saveSpy = jest.spyOn(configService, 'saveConfig')
    const initSpy = jest.spyOn(settingService, 'initializeSettings')
    saveSpy.mockReturnValueOnce(
      of({ output_type: OutputTypeConfig.PDF_A } as any)
    )
    component.saveConfig()
    expect(initSpy).toHaveBeenCalled()

    const uploadSpy = jest.spyOn(configService, 'uploadFile')
    uploadSpy.mockReturnValueOnce(
      of({ app_logo: 'https://example.com/logo/test.png' } as any)
    )
    component.uploadFile(new File([], 'test.png'), 'app_logo')
    expect(initSpy).toHaveBeenCalled()
  })

  it('should reset option to null', () => {
    component.configForm.patchValue({ output_type: OutputTypeConfig.PDF_A })
    expect(component.isSet('output_type')).toBeTruthy()
    component.resetOption('output_type')
    expect(component.configForm.get('output_type').value).toBeNull()
    expect(component.isSet('output_type')).toBeFalsy()
    component.configForm.patchValue({ app_title: 'Test Title' })
    component.resetOption('app_title')
    expect(component.configForm.get('app_title').value).toBeNull()
    component.configForm.patchValue({ barcodes_enabled: true })
    component.resetOption('barcodes_enabled')
    expect(component.configForm.get('barcodes_enabled').value).toBeNull()
  })

  it('marks unset fields with a default as inherited and formats the value', () => {
    const llmModel = PaperlessConfigOptions.find((o) => o.key === 'llm_model')
    const aiEnabled = PaperlessConfigOptions.find((o) => o.key === 'ai_enabled')
    component.defaults = { llm_model: 'env-model', ai_enabled: true }

    component.configForm.get('llm_model').setValue(null)
    expect(component.isInherited(llmModel)).toBeTruthy()
    expect(component.inheritedDisplay(llmModel)).toBe('env-model')

    // Boolean defaults render as a label.
    component.configForm.get('ai_enabled').setValue(null)
    expect(component.inheritedDisplay(aiEnabled)).toBe('Enabled')

    // Once overridden in the UI, the field is no longer inherited.
    component.configForm.get('llm_model').setValue('ui-model')
    expect(component.isInherited(llmModel)).toBeFalsy()
  })

  it('does not mark fields without a default as inherited', () => {
    const llmModel = PaperlessConfigOptions.find((o) => o.key === 'llm_model')
    component.defaults = {}
    component.configForm.get('llm_model').setValue(null)
    expect(component.isInherited(llmModel)).toBeFalsy()
    expect(component.inheritedDisplay(llmModel)).toBe('')
  })
})
