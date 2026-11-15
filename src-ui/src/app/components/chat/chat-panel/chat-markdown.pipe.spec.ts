import { ChatMarkdownPipe } from './chat-markdown.pipe'

describe('ChatMarkdownPipe', () => {
  const pipe = new ChatMarkdownPipe()
  const citations = new Map([
    [1, { marker: 1, documentId: 9, title: 'Report "Q1" <2026>', snippet: '' }],
  ])

  it('renders incomplete fenced code and progressively completed Markdown', () => {
    expect(pipe.transform('## Summary\n\n**Hel')).toContain('<h2>Summary</h2>')
    const html = pipe.transform(
      '## Summary\n\n**Hello**\n\n- One\n- Two\n\n```ts\nconst x = 1'
    )
    expect(html).toContain('<strong>Hello</strong>')
    expect(html).toContain('<li>Two</li>')
    expect(html).toContain('<code class="language-ts">const x = 1')
  })

  it('supports tables and blockquotes without changing the source', () => {
    const source =
      '| Item | Total |\n| --- | --- |\n| Rent | 1200 |\n\n> Verified'
    const html = pipe.transform(source)
    expect(html).toContain('<table>')
    expect(html).toContain('<td>1200</td>')
    expect(html).toContain('<blockquote>')
  })

  it('renders known citations safely and leaves markers inside fenced code alone', () => {
    const html = pipe.transform(
      'See [1], `[1]`, [2].\n\n```\n[1]\n```',
      citations
    )
    expect(html.match(/href="\/documents\/9"/g)).toHaveLength(2)
    expect(html).toContain('title="Report &quot;Q1&quot; &lt;2026&gt;"')
    expect(html).toContain('[2]')
    expect(html).toContain('<pre><code>[1]')
  })

  it('does not rewrite link labels or create remote images and unsafe links', () => {
    const html = pipe.transform(
      '[1](https://example.com) ![tracking](https://evil.example/pixel) [bad](javascript:alert%281%29)',
      citations
    )
    expect(html).toContain('href="https://example.com"')
    expect(html).not.toContain('/documents/9')
    expect(html).not.toContain('<img')
    expect(html).not.toContain('href="javascript:')
    expect(html).toContain('noopener noreferrer')
  })

  it('escapes raw HTML, including incomplete streamed tags', () => {
    for (const content of [
      '<img src=x onerror=alert(1)>',
      '<script>alert(1)</script>',
      '<img src="',
    ]) {
      const html = pipe.transform(content)
      expect(html).not.toContain('<img')
      expect(html).not.toContain('<script')
    }
  })
})
