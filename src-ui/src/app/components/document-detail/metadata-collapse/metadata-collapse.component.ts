import { Component, Input } from '@angular/core'
import { NgbCollapseModule } from '@ng-bootstrap/ng-bootstrap'
import { LucideAngularModule } from 'lucide-angular'
import { NgxBootstrapIconsModule } from 'ngx-bootstrap-icons'

@Component({
  selector: 'pngx-metadata-collapse',
  templateUrl: './metadata-collapse.component.html',
  styleUrls: ['./metadata-collapse.component.scss'],
  imports: [NgbCollapseModule, NgxBootstrapIconsModule, LucideAngularModule],
})
export class MetadataCollapseComponent {
  constructor() {}

  expand = false

  @Input()
  metadata

  @Input()
  title = $localize`Metadata`
}
