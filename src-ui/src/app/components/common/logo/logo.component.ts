import { Component, Input, inject } from '@angular/core'
import { SETTINGS_KEYS } from 'src/app/data/ui-settings'
import { SettingsService } from 'src/app/services/settings.service'
import { environment } from 'src/environments/environment'

@Component({
  selector: 'pngx-logo',
  templateUrl: './logo.component.html',
  styleUrls: ['./logo.component.scss'],
})
export class LogoComponent {
  private settingsService = inject(SettingsService)

  @Input()
  extra_classes: string

  @Input()
  height = '6em'

  get customLogo(): string {
    return this.settingsService.get(SETTINGS_KEYS.APP_LOGO)?.length
      ? environment.apiBaseUrl.replace(
          /\/api\/$/,
          this.settingsService.get(SETTINGS_KEYS.APP_LOGO)
        )
      : null
  }

  /**
   * Whether dark mode is currently effective — either explicitly enabled, or
   * "use system" with the OS in dark mode. The brand SVGs use fixed (not
   * currentColor) fills, so binding a single theme-aware `src` is more reliable
   * than a CSS display swap, which Bootstrap's `!important` `d-*` display
   * utilities (used on the dashboard logo) would defeat.
   */
  get isDarkMode(): boolean {
    if (this.settingsService.get(SETTINGS_KEYS.DARK_MODE_USE_SYSTEM)) {
      return (
        window.matchMedia?.('(prefers-color-scheme: dark)')?.matches ?? false
      )
    }
    return this.settingsService.get(SETTINGS_KEYS.DARK_MODE_ENABLED)
  }

  get defaultLogo(): string {
    return this.isDarkMode
      ? 'assets/paperflow-logo-dark.svg'
      : 'assets/paperflow-logo-light.svg'
  }

  getClasses() {
    return ['logo'].concat(this.extra_classes).join(' ')
  }
}
