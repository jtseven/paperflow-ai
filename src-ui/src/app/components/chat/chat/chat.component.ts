import { Component, inject, OnInit } from '@angular/core'
import { NavigationEnd, Router } from '@angular/router'
import { NgbDropdownModule } from '@ng-bootstrap/ng-bootstrap'
import { LucideAngularModule } from 'lucide-angular'
import { NgxBootstrapIconsModule } from 'ngx-bootstrap-icons'
import { filter, map } from 'rxjs'
import { ChatPanelComponent } from '../chat-panel/chat-panel.component'

@Component({
  selector: 'pngx-chat',
  imports: [
    NgbDropdownModule,
    NgxBootstrapIconsModule,
    LucideAngularModule,
    ChatPanelComponent,
  ],
  templateUrl: './chat.component.html',
  styleUrl: './chat.component.scss',
})
export class ChatComponent implements OnInit {
  public documentId?: number

  private router: Router = inject(Router)

  public get placeholder(): string {
    return this.documentId
      ? $localize`Ask a question about this document...`
      : $localize`Ask a question about a document...`
  }

  ngOnInit(): void {
    this.updateDocumentId(this.router.url)
    this.router.events
      .pipe(
        filter((event) => event instanceof NavigationEnd),
        map((event) => (event as NavigationEnd).url)
      )
      .subscribe((url) => {
        this.updateDocumentId(url)
      })
  }

  private updateDocumentId(url: string): void {
    const docIdRe = url.match(/^\/documents\/(\d+)/)
    this.documentId = docIdRe ? +docIdRe[1] : undefined
  }
}
