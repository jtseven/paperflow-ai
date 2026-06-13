import { Component, Input } from '@angular/core'
import { NgbCollapseModule } from '@ng-bootstrap/ng-bootstrap'
import { NgxBootstrapIconsModule } from 'ngx-bootstrap-icons'
import { LucideAngularModule } from 'lucide-angular'

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
