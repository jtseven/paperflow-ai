import { CommonModule } from '@angular/common'
import { Component, ElementRef, inject, ViewChild } from '@angular/core'
import { FormsModule } from '@angular/forms'
import { RouterModule } from '@angular/router'
import { NgxBootstrapIconsModule } from 'ngx-bootstrap-icons'
import { MarkdownModule } from 'ngx-markdown'
import {
  ChatMessage,
  ChatService,
  parseChatResponse,
} from 'src/app/services/chat.service'
import { WidgetFrameComponent } from '../widget-frame/widget-frame.component'

const WELCOME_MESSAGE = $localize`Hello, I am Paperflow AI and I have access to all of your documents. How can I help you today?`

@Component({
  selector: 'pngx-ai-chat-widget',
  templateUrl: './ai-chat-widget.component.html',
  styleUrls: ['./ai-chat-widget.component.scss'],
  imports: [
    FormsModule,
    WidgetFrameComponent,
    CommonModule,
    MarkdownModule,
    RouterModule,
    NgxBootstrapIconsModule,
  ],
})
export class AiChatWidgetComponent {
  @ViewChild('chatContainer', { static: false }) chatContainer: ElementRef

  public messages: ChatMessage[] = [
    { role: 'assistant', content: WELCOME_MESSAGE },
  ]
  public input = ''
  public loading = false

  private chatService: ChatService = inject(ChatService)

  sendMessage(): void {
    const prompt = this.input.trim()
    if (prompt === '' || this.loading) {
      return
    }

    this.messages.push({ role: 'user', content: prompt })
    this.input = ''
    this.scrollToBottom()

    const assistantMessage: ChatMessage = {
      role: 'assistant',
      content: '',
      isStreaming: true,
    }
    this.messages.push(assistantMessage)
    this.loading = true

    // No documentId: agentic retrieval across all accessible documents.
    this.chatService.streamChat(null, prompt).subscribe({
      next: (chunk) => {
        const parsed = parseChatResponse(chunk)
        assistantMessage.content = parsed.content
        assistantMessage.references = parsed.references
        this.scrollToBottom()
      },
      error: () => {
        assistantMessage.content +=
          (assistantMessage.content ? '\n\n' : '') +
          $localize`⚠️ Sorry, there was an error processing your message. Please try again.`
        assistantMessage.isStreaming = false
        this.loading = false
        this.scrollToBottom()
      },
      complete: () => {
        assistantMessage.isStreaming = false
        this.loading = false
        this.scrollToBottom()
      },
    })
  }

  private scrollToBottom(): void {
    setTimeout(() => {
      if (this.chatContainer) {
        this.chatContainer.nativeElement.scrollTop =
          this.chatContainer.nativeElement.scrollHeight
      }
    })
  }
}
