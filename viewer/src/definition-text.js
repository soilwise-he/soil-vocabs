const markup = /<\/?(?:a|abbr|b|blockquote|br|code|dd|div|dl|dt|em|h[1-6]|hr|i|li|ol|p|pre|s|small|span|strong|sub|sup|table|tbody|td|th|thead|tr|u|ul|script|style|iframe|object|embed|template|img|svg|math)\b[^>]*>/i
const entity = /&(?:#[0-9]+|#x[0-9a-f]+|[a-z][a-z0-9]+);/i
const omitted = new Set(['script', 'style', 'iframe', 'object', 'embed', 'template', 'noscript', 'title'])
const blocks = new Set(['blockquote', 'dd', 'div', 'dl', 'dt', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'ol', 'p', 'pre', 'table', 'tr', 'ul'])

export function definitionText(text) {
  if (!markup.test(text) && !entity.test(text)) return text
  // Parse in an inert template; never insert source elements or attributes into the page.
  const template = document.createElement('template')
  template.innerHTML = markup.test(text) ? text : text.replaceAll('<', '&lt;').replaceAll('>', '&gt;')
  function read(node) {
    if (node.nodeType === 3) return node.textContent
    if (node.nodeType !== 1 && node.nodeType !== 11) return ''
    const tag = node.localName
    if (omitted.has(tag)) return ''
    if (tag === 'br' || tag === 'hr') return '\n'
    const content = Array.from(node.childNodes, read).join('')
    if (blocks.has(tag)) return `\n${content}\n`
    return tag === 'td' || tag === 'th' ? `${content} ` : content
  }
  return read(template.content).replace(/[\t\r \u00a0]+/g, ' ')
    .replace(/ *\n */g, '\n').replace(/\n{3,}/g, '\n\n').trim()
}
