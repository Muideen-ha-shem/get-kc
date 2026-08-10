export type ExportableMessage = {
  role: 'user' | 'assistant';
  content: string;
  sources?: string[];
};

/** Renders a conversation transcript as Markdown — plain text answers, no
 * component tree, so it reads cleanly outside the app (a shared doc, a
 * support ticket, an email). */
export function messagesToMarkdown(title: string, messages: ExportableMessage[]): string {
  const lines: string[] = [`# ${title}`, ''];
  for (const message of messages) {
    const heading = message.role === 'user' ? 'You' : 'HavisIQ';
    lines.push(`**${heading}:**`, '', message.content.trim(), '');
    if (message.sources && message.sources.length > 0) {
      lines.push('_Sources:_ ' + message.sources.join(', '), '');
    }
  }
  return lines.join('\n').trim() + '\n';
}

export function downloadMarkdown(filename: string, content: string): void {
  const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename.endsWith('.md') ? filename : `${filename}.md`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
