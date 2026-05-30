import { Injectable } from '@angular/core'
import { MarkedOptions, MarkedRenderer } from 'ngx-markdown'

@Injectable({ providedIn: 'root' })
export class MarkdownConfigService {
  private currentDocumentId: number = null

  /**
   * Set the current document ID for image resolution
   */
  public setCurrentDocumentId(documentId: number) {
    this.currentDocumentId = documentId
  }

  /**
   * Creates the markdown renderer options used across the app.
   */
  public createMarkedOptions(): MarkedOptions {
    const renderer = new MarkedRenderer()

    return {
      renderer: renderer,
      gfm: true,
      breaks: false,
      pedantic: false,
    }
  }
}
