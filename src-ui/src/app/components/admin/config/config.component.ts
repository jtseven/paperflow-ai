import { AsyncPipe } from '@angular/common'
import { Component, OnDestroy, OnInit, inject } from '@angular/core'
import {
  AbstractControl,
  FormControl,
  FormGroup,
  FormsModule,
  ReactiveFormsModule,
} from '@angular/forms'
import { NgbNavModule } from '@ng-bootstrap/ng-bootstrap'
import { DirtyComponent, dirtyCheck } from '@ngneat/dirty-check-forms'
import { LucideAngularModule } from 'lucide-angular'
import { NgxBootstrapIconsModule } from 'ngx-bootstrap-icons'
import {
  BehaviorSubject,
  Observable,
  Subscription,
  first,
  takeUntil,
} from 'rxjs'
import {
  ConfigCategory,
  ConfigOption,
  ConfigOptionType,
  PaperlessConfig,
  PaperlessConfigOptions,
} from 'src/app/data/paperless-config'
import { ConfigService } from 'src/app/services/config.service'
import { SettingsService } from 'src/app/services/settings.service'
import { ToastService } from 'src/app/services/toast.service'
import { FileComponent } from '../../common/input/file/file.component'
import { NumberComponent } from '../../common/input/number/number.component'
import { PasswordComponent } from '../../common/input/password/password.component'
import { SelectComponent } from '../../common/input/select/select.component'
import { SwitchComponent } from '../../common/input/switch/switch.component'
import { TextComponent } from '../../common/input/text/text.component'
import { PageHeaderComponent } from '../../common/page-header/page-header.component'
import { LoadingComponentWithPermissions } from '../../loading-component/loading.component'

@Component({
  selector: 'pngx-config',
  templateUrl: './config.component.html',
  styleUrl: './config.component.scss',
  imports: [
    PageHeaderComponent,
    SelectComponent,
    SwitchComponent,
    TextComponent,
    NumberComponent,
    FileComponent,
    PasswordComponent,
    AsyncPipe,
    NgbNavModule,
    FormsModule,
    ReactiveFormsModule,
    NgxBootstrapIconsModule,
    LucideAngularModule,
  ],
})
export class ConfigComponent
  extends LoadingComponentWithPermissions
  implements OnInit, OnDestroy, DirtyComponent
{
  private configService = inject(ConfigService)
  private toastService = inject(ToastService)
  private settingsService = inject(SettingsService)

  public readonly ConfigOptionType = ConfigOptionType

  // generated dynamically
  public configForm = new FormGroup({})

  public errors = {}

  get optionCategories(): string[] {
    return Object.values(ConfigCategory)
  }

  getCategoryOptions(category: string): ConfigOption[] {
    return PaperlessConfigOptions.filter((o) => o.category === category)
  }

  initialConfig: PaperlessConfig
  store: BehaviorSubject<any>
  storeSub: Subscription
  isDirty$: Observable<boolean>

  // Inherited values (environment / config file / defaults), shown as
  // placeholders when a field has no stored override.
  public defaults: { [key: string]: any } = {}

  constructor() {
    super()
    this.configForm.addControl('id', new FormControl())
    PaperlessConfigOptions.forEach((option) => {
      this.configForm.addControl(option.key, new FormControl())
    })
  }

  ngOnInit(): void {
    this.configService
      .getConfig()
      .pipe(takeUntil(this.unsubscribeNotifier))
      .subscribe({
        next: (config) => {
          this.loading = false
          this.initialize(config)
        },
        error: (e) => {
          this.loading = false
          this.toastService.showError($localize`Error retrieving config`, e)
        },
      })

    // validate JSON inputs
    PaperlessConfigOptions.filter(
      (o) => o.type === ConfigOptionType.JSON
    ).forEach((option) => {
      this.configForm
        .get(option.key)
        .addValidators((control: AbstractControl) => {
          if (!control.value || control.value.toString().length === 0)
            return null
          try {
            JSON.parse(control.value)
          } catch (e) {
            return [
              {
                user_args: e,
              },
            ]
          }
          return null
        })
      this.configForm.get(option.key).statusChanges.subscribe((status) => {
        this.errors[option.key] =
          status === 'INVALID' ? $localize`Invalid JSON` : null
      })
      this.configForm.get(option.key).updateValueAndValidity()
    })
  }

  ngOnDestroy(): void {
    this.unsubscribeNotifier.next(true)
    this.unsubscribeNotifier.complete()
  }

  private initialize(config: PaperlessConfig) {
    // "defaults" is a read-only sibling of the editable fields; keep it out of
    // the form/dirty-check store so it never registers as an unsaved change.
    this.defaults = config.defaults ?? {}
    const { defaults, ...formConfig } = config

    if (!this.store) {
      this.store = new BehaviorSubject(formConfig)

      this.store
        .asObservable()
        .pipe(takeUntil(this.unsubscribeNotifier))
        .subscribe((state) => {
          this.configForm.patchValue(state, { emitEvent: false })
        })

      this.isDirty$ = dirtyCheck(this.configForm, this.store.asObservable())
    }
    this.configForm.patchValue(formConfig)

    this.initialConfig = formConfig as PaperlessConfig
  }

  getDocsUrl(key: string) {
    return `https://docs.paperless-ngx.com/configuration/#${key}`
  }

  public saveConfig() {
    this.loading = true
    this.configService
      .saveConfig(this.configForm.value as PaperlessConfig)
      .pipe(takeUntil(this.unsubscribeNotifier), first())
      .subscribe({
        next: (config) => {
          this.loading = false
          this.initialize(config)
          this.store.next(this.initialConfig)
          this.settingsService.initializeSettings().subscribe()
          this.toastService.showInfo($localize`Configuration updated`)
        },
        error: (e) => {
          this.loading = false
          this.toastService.showError(
            $localize`An error occurred updating configuration`,
            e
          )
        },
      })
  }

  public discardChanges() {
    this.configForm.reset(this.initialConfig)
  }

  public uploadFile(file: File, key: string) {
    this.loading = true
    this.configService
      .uploadFile(file, this.configForm.value['id'], key)
      .pipe(takeUntil(this.unsubscribeNotifier), first())
      .subscribe({
        next: (config) => {
          this.loading = false
          this.initialize(config)
          this.store.next(this.initialConfig)
          this.settingsService.initializeSettings().subscribe()
          this.toastService.showInfo($localize`File successfully updated`)
        },
        error: (e) => {
          this.loading = false
          this.toastService.showError(
            $localize`An error occurred uploading file`,
            e
          )
        },
      })
  }

  public isSet(key: string): boolean {
    return this.configForm.get(key).value != null
  }

  /** True when a field has no stored override but an inherited value exists. */
  public isInherited(option: ConfigOption): boolean {
    const value = this.defaults?.[option.key]
    return !this.isSet(option.key) && value != null && value !== ''
  }

  /** The inherited value formatted for display (choice label, On/Off, etc.). */
  public inheritedDisplay(option: ConfigOption): string {
    const value = this.defaults?.[option.key]
    if (value == null) {
      return ''
    }
    switch (option.type) {
      case ConfigOptionType.Boolean:
        return value ? $localize`Enabled` : $localize`Disabled`
      case ConfigOptionType.Select:
        return (
          option.choices?.find((c) => c.id === value)?.name ?? String(value)
        )
      case ConfigOptionType.JSON:
        return typeof value === 'string' ? value : JSON.stringify(value)
      default:
        return String(value)
    }
  }

  public resetOption(key: string) {
    this.configForm.get(key).setValue(null)
  }
}
