import { Pipe, PipeTransform } from '@angular/core'
import { Marked, Renderer } from 'marked'
import { Citation } from 'src/app/services/chat.service'

function escapeHtml(text: string): string {
  const entities: Record<string, string> = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;',
  }
  return text.replace(/[&<>"']/g, (character) => entities[character])
}

/** Synchronous parsing keeps streamed updates in Angular's render pass. */
@Pipe({ name: 'chatMarkdown' })
export class ChatMarkdownPipe implements PipeTransform {
  transform(content: string, citations?: Map<number, Citation>): string {
    const citationLink = (marker: string): string | undefined => {
      const citation = citations?.get(+marker)
      if (
        !citation ||
        !Number.isSafeInteger(citation.documentId) ||
        citation.documentId <= 0
      )
        return
      return `<a href="/documents/${citation.documentId}" title="${escapeHtml(citation.title)}" class="chat-citation">[${marker}]</a>`
    }
    const markdown = new Marked({
      async: false,
      gfm: true,
      breaks: true,
      renderer: {
        // No model-supplied HTML or remote images. Angular also sanitizes the
        // resulting HTML at the binding; never bypassSecurityTrustHtml here.
        html: ({ text }) => escapeHtml(text),
        image: ({ text }) => escapeHtml(text),
        link(token) {
          let allowed = /^\/documents\/[1-9]\d*$/.test(token.href)
          try {
            allowed ||= ['https:', 'http:', 'mailto:'].includes(
              new URL(token.href).protocol
            )
          } catch {
            // Relative and incomplete links stay plain text until complete.
          }
          if (!allowed) return this.parser.parseInline(token.tokens)
          return Renderer.prototype.link
            .call(this, token)
            .replace('<a ', '<a rel="noopener noreferrer nofollow" ')
        },
        codespan(token) {
          const marker = /^\[(\d+)\]$/.exec(token.text)
          return (
            (marker && citationLink(marker[1])) ||
            Renderer.prototype.codespan.call(this, token)
          )
        },
      },
      extensions: [
        {
          name: 'citation',
          level: 'inline',
          start: (text) => text.search(/\[\d+\]/),
          tokenizer(text) {
            const match = /^\[(\d+)\](?![\[(])/.exec(text)
            if (match && citationLink(match[1])) {
              return { type: 'citation', raw: match[0], marker: match[1] }
            }
            return undefined
          },
          renderer: (token) => citationLink(token['marker']) ?? token.raw,
        },
      ],
    })
    // Marked handles unfinished fences and reparses partial inline syntax as
    // subsequent chunks arrive. Keep the stored answer as the original text.
    return markdown.parse(content) as string
  }
}
