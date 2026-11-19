import { NS } from './vocabulary.js'

// Every viewer page lives in one directory: index.html, 404.html and a generated
// <LocalName>.html per concept, which GitHub Pages serves at /<LocalName>.
export function appRoot() {
  let base = './'
  try { base = import.meta.env.BASE_URL || base } catch { /* Outside a Vite build, such as in tests. */ }
  if (base.startsWith('/')) return base
  return typeof location === 'undefined' ? '/' : location.pathname.replace(/[^/]*$/, '')
}

// Links name SoilVoc's own resources by local name; parseRoute expands them again.
export function routeId(uri, namespace = NS.eusoilvoc) {
  const local = uri.startsWith(namespace) ? uri.slice(namespace.length) : ''
  return local && !local.includes(':') ? local : uri
}

// Concepts get a page only when their name is safe as a file name and URL segment;
// any other resource is addressed as ?uri=.
export function isPageName(name) {
  return /^[A-Za-z0-9][A-Za-z0-9._~-]*$/.test(name) && name.toLowerCase() !== 'index' && !/\.html$/i.test(name)
}

// The concept name in a page address, or '' for the home page.
export function pageName(pathname, root) {
  if (!pathname.startsWith(root)) return ''
  let name
  try { name = decodeURIComponent(pathname.slice(root.length)) } catch { return '' }
  name = name.replace(/\.html$/i, '')
  return name.toLowerCase() === 'index' ? '' : name
}

function expandId(value, namespace) {
  return value && !value.includes(':') ? namespace + value : value
}

// A branch other than the default one lists the concept's ancestors, separated by "/".
function pathParam(uri, path, namespace) {
  if (!path?.length) return null
  const ids = path.map(entry => routeId(entry, namespace))
  if (ids.at(-1) === routeId(uri, namespace)) ids.pop()
  if (!ids.length) return null
  return ids.every(id => !/[/:]/.test(id)) ? ids.map(encodeURIComponent).join('/') : encodeURIComponent(JSON.stringify(path))
}

export function conceptHref(uri, path, root = appRoot(), namespace = NS.eusoilvoc) {
  const id = routeId(uri, namespace), param = pathParam(uri, path, namespace)
  if (id !== uri && isPageName(id)) return root + encodeURIComponent(id) + (param ? '?path=' + param : '')
  return root + '?uri=' + encodeURIComponent(id) + (param ? '&path=' + param : '')
}

// Address of any route: a concept page, or the home page with query parameters.
export function routeHref(params = {}, root = appRoot(), namespace = NS.eusoilvoc) {
  if (params.uri) return conceptHref(params.uri, params.path, root, namespace)
  const query = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) if (value !== undefined && value !== null) query.set(key, String(value))
  const search = query.toString()
  return root + (search ? '?' + search : '')
}

// The short page address for a concept opened by an older ?uri= link or a W3ID #fragment.
// Other query parameters, such as a branch or a sign-in callback, are kept.
export function conceptLocation(href, uri, root, namespace = NS.eusoilvoc) {
  const url = new URL(href), id = routeId(uri, namespace), page = id !== uri && isPageName(id)
  url.pathname = root + (page ? encodeURIComponent(id) : '')
  const query = page ? [] : ['uri=' + encodeURIComponent(id)]
  // Other parameters stay exactly as written; only an older JSON branch becomes the
  // short list of ancestors.
  for (const pair of url.search.slice(1).split('&').filter(Boolean)) {
    const [rawKey, ...rest] = pair.split('=')
    let key, value
    try { [key, value] = [rawKey, rest.join('=')].map(part => decodeURIComponent(part.replace(/\+/g, ' '))) }
    catch { query.push(pair); continue }
    if (key === 'uri') continue
    let path = null
    if (key === 'path' && value.trim().startsWith('[')) try { path = JSON.parse(value) } catch { /* Kept as given. */ }
    if (!Array.isArray(path)) query.push(pair)
    else {
      const param = pathParam(uri, path, namespace)
      if (param) query.push('path=' + param)
    }
  }
  url.search = query.length ? '?' + query.join('&') : ''
  url.hash = ''
  return url.href
}

export function followLink(event, action) {
  const anchor = event.currentTarget
  if (event.defaultPrevented || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey ||
    anchor?.hasAttribute('download') || (anchor?.target && anchor.target !== '_self')) return
  event.preventDefault()
  action()
}

// The concept comes from ?uri=, then the page address, then a #fragment.
export function parseRoute(search, namespace, hash = '', pageId = '') {
  const params = new URLSearchParams(search)
  let uri = params.get('uri') || pageId || ''
  if (!uri && hash && hash !== '#') {
    try { uri = decodeURIComponent(hash.slice(1)).trim() }
    catch { /* Malformed fragments must not prevent the viewer from loading. */ }
  }
  uri = expandId(uri, namespace)
  const rawPath = params.get('path')
  let path = null
  if (rawPath?.trim().startsWith('[')) {
    try { path = JSON.parse(rawPath) } catch { /* Invalid paths are resolved from the graph. */ }
  } else if (rawPath) path = rawPath.split('/').filter(Boolean)
  if (Array.isArray(path)) {
    // Older links use complete URIs and include the concept; short links list ancestors only.
    path = path.map(entry => typeof entry === 'string' ? expandId(entry, namespace) : entry)
    if (uri && path.at(-1) !== uri) path.push(uri)
  }
  const page = Number(params.get('page') || 1)
  return {
    view: uri ? 'concept' : params.has('q') ? 'search' : ['about', 'ontology'].includes(params.get('view')) ? params.get('view') : 'home',
    uri, q: params.get('q') || '', type: params.get('type') || '', path,
    page: Number.isSafeInteger(page) && page > 0 ? page - 1 : 0,
  }
}
