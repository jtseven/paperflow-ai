import { Component } from '@angular/core'
import { RouterModule } from '@angular/router'
import { LucideAngularModule } from 'lucide-angular'
import { LogoComponent } from '../common/logo/logo.component'

@Component({
  selector: 'pngx-not-found',
  templateUrl: './not-found.component.html',
  styleUrls: ['./not-found.component.scss'],
  imports: [LogoComponent, RouterModule, LucideAngularModule],
})
export class NotFoundComponent {
  constructor() {}
}
