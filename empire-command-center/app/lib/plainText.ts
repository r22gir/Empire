/** Strip Telegram/HTML tags so Studio screens never show raw <b>. */
export function stripTelegramHtml(text: string | null | undefined): string {
  if (!text) return '';
  return String(text)
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/<\/?(?:b|strong|i|em|u|code|pre|s|a)(?:\s[^>]*)?>/gi, '')
    .replace(/<[^>]+>/g, '')
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .trim();
}
