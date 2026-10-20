export function conceptHref(uri, path) {
  const params = new URLSearchParams({ uri })
  if (path?.length) params.set('path', JSON.stringify(path))
  return '?' + params
}

export function followLink(event, action) {
  const anchor = event.currentTarget
  if (event.defaultPrevented || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey ||
    anchor?.hasAttribute('download') || (anchor?.target && anchor.target !== '_self')) return
  event.preventDefault()
  action()
}

export function parseRoute(search, namespace) {
  const params = new URLSearchParams(search)
  let uri = params.get('uri') || ''
  if (uri && !uri.includes(':')) uri = namespace + uri
  let path = null
  try { path = JSON.parse(params.get('path') || 'null') } catch { /* Invalid paths are resolved from the graph. */ }
  const page = Number(params.get('page') || 1)
  return {
    view: params.has('q') ? 'search' : uri ? 'concept' : ['about', 'ontology'].includes(params.get('view')) ? params.get('view') : 'home',
    uri, q: params.get('q') || '', type: params.get('type') || '', path,
    page: Number.isSafeInteger(page) && page > 0 ? page - 1 : 0,
  }
}
