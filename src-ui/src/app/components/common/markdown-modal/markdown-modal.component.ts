import { CommonModule } from '@angular/common'
import { Component, Input, OnInit, inject } from '@angular/core'
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap'
import { LucideAngularModule } from 'lucide-angular'
import { NgxBootstrapIconsModule } from 'ngx-bootstrap-icons'
import { MarkdownModule } from 'ngx-markdown'
import { MarkdownConfigService } from 'src/app/services/markdown-config.service'

@Component({
  selector: 'pngx-markdown-modal',
  templateUrl: './markdown-modal.component.html',
  styleUrls: ['./markdown-modal.component.scss'],
  standalone: true,
  imports: [
    CommonModule,
    NgxBootstrapIconsModule,
    LucideAngularModule,
    MarkdownModule,
  ],
})
export class MarkdownModalComponent implements OnInit {
  @Input() content: string
  @Input() title: string
  @Input() isRTL: boolean
  @Input() documentId: number

  activeModal = inject(NgbActiveModal)
  private markdownConfigService = inject(MarkdownConfigService)

  ngOnInit() {
    if (this.documentId) {
      this.markdownConfigService.setCurrentDocumentId(this.documentId)
    }
  }
}
