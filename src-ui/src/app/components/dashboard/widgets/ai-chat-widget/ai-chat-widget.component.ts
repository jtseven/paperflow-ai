import { Component } from '@angular/core'
import { ChatPanelComponent } from 'src/app/components/chat/chat-panel/chat-panel.component'
import { WidgetFrameComponent } from '../widget-frame/widget-frame.component'

const WELCOME_MESSAGE = $localize`Hello, I am Paperflow AI and I have access to all of your documents. How can I help you today?`

@Component({
  selector: 'pngx-ai-chat-widget',
  templateUrl: './ai-chat-widget.component.html',
  styleUrls: ['./ai-chat-widget.component.scss'],
  imports: [WidgetFrameComponent, ChatPanelComponent],
})
export class AiChatWidgetComponent {
  public welcome = WELCOME_MESSAGE
}
