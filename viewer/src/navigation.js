import { NS } from './vocabulary.js'

// Links name SoilVoc's own resources by local name; parseRoute expands them again.
export function routeId(uri, namespace = NS.eusoilvoc) {
  const local = uri.startsWith(namespace) ? uri.slice(namespace.length) : ''
  return local && !local.includes(':') ? local : uri
}

function expandId(value, namespace) {
  return value && !value.includes(':') ? namespace + value : value
}

export function conceptParams(uri, path, namespace = NS.eusoilvoc) {
  const params = { uri: routeId(uri, namespace) }
  if (path?.length) params.path = JSON.stringify(path.map(entry => routeId(entry, namespace)))
  return params
}

export function conceptHref(uri, path, namespace) {
  return '?' + new URLSearchParams(conceptParams(uri, path, namespace))
}

export function followLink(event, action) {
  const anchor = event.currentTarget
  if (event.defaultPrevented || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey ||
    anchor?.hasAttribute('download') || (anchor?.target && anchor.target !== '_self')) return
  event.preventDefault()
  action()
}

export function parseRoute(search, namespace, hash = '') {
  const params = new URLSearchParams(search)
  let uri = params.get('uri') || ''
  if (!uri && hash && hash !== '#') {
    try { uri = decodeURIComponent(hash.slice(1)).trim() }
    catch { /* Malformed fragments must not prevent the viewer from loading. */ }
  }
  uri = expandId(uri, namespace)
  let path = null
  try { path = JSON.parse(params.get('path') || 'null') } catch { /* Invalid paths are resolved from the graph. */ }
  // Older links use complete URIs in the path; shorter links use local names.
  if (Array.isArray(path)) path = path.map(entry => typeof entry === 'string' ? expandId(entry, namespace) : entry)
  const page = Number(params.get('page') || 1)
  return {
    view: uri ? 'concept' : params.has('q') ? 'search' : ['about', 'ontology'].includes(params.get('view')) ? params.get('view') : 'home',
    uri, q: params.get('q') || '', type: params.get('type') || '', path,
    page: Number.isSafeInteger(page) && page > 0 ? page - 1 : 0,
  }
}
