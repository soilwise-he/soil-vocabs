import { Lexer, Parser, Store, Writer, DataFactory } from 'n3'

export const NS = {
  rdf: 'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
  rdfs: 'http://www.w3.org/2000/01/rdf-schema#',
  skos: 'http://www.w3.org/2004/02/skos/core#',
  sosa: 'http://www.w3.org/ns/sosa/',
  dcterms: 'http://purl.org/dc/terms/',
  dc: 'http://purl.org/dc/elements/1.1/',
  eusoilvoc: 'https://w3id.org/eusoilvoc#',
  agrontology: 'http://aims.fao.org/aos/agrontology#',
  sio: 'http://semanticscience.org/resource/',
  owl: 'http://www.w3.org/2002/07/owl#',
  xsd: 'http://www.w3.org/2001/XMLSchema#',
}
export const TYPE = NS.rdf + 'type'
export const CONCEPT = NS.skos + 'Concept'
export const PROCEDURE = NS.sosa + 'Procedure'
export const PROPERTY = NS.sosa + 'ObservableProperty'
export const DISPLAY_PARENT = NS.eusoilvoc + 'skosmosHierarchyParent'
const { namedNode } = DataFactory
const omitted = new Set([
  TYPE, NS.skos + 'prefLabel', NS.skos + 'definition', NS.skos + 'inScheme',
  NS.skos + 'topConceptOf', NS.skos + 'broaderTransitive', NS.skos + 'narrowerTransitive', DISPLAY_PARENT,
])
const propertyOrder = [
  NS.skos + 'broader', NS.skos + 'narrower', NS.sosa + 'hasProcedure', NS.sosa + 'isProcedureFor',
  NS.skos + 'related', NS.skos + 'exactMatch', NS.skos + 'closeMatch', NS.skos + 'altLabel',
  NS.skos + 'note', NS.skos + 'scopeNote', NS.skos + 'historyNote', NS.rdfs + 'comment',
]
const captions = {
  [NS.skos + 'broader']: 'Broader concepts', [NS.skos + 'narrower']: 'Narrower concepts',
  [NS.sosa + 'hasProcedure']: 'Has procedure', [NS.sosa + 'isProcedureFor']: 'Is procedure for',
  [NS.skos + 'exactMatch']: 'Exact matches', [NS.skos + 'closeMatch']: 'Close matches',
  [NS.skos + 'altLabel']: 'Alternative labels', [NS.skos + 'related']: 'Related concepts',
}
const propertyHelp = {
  [TYPE]: 'The classes assigned to this resource, such as Concept, Observable Property or Procedure.',
  [NS.skos + 'definition']: 'A description of this concept. Each source shown belongs to the definition immediately above it.',
  [NS.skos + 'prefLabel']: 'The preferred name used to display this concept in a given language.',
  [NS.skos + 'altLabel']: 'Other names or synonyms that can also be used to find this concept.',
  [NS.skos + 'hiddenLabel']: 'Names used for searching but not normally presented as preferred or alternative labels.',
  [NS.skos + 'broader']: 'Concepts directly broader than this concept in the SKOS hierarchy.',
  [NS.skos + 'narrower']: 'Concepts directly narrower than this concept in the SKOS hierarchy.',
  [NS.skos + 'related']: 'Associated concepts. This relationship does not establish a broader or narrower hierarchy.',
  [NS.skos + 'exactMatch']: 'Mappings to concepts in other vocabularies recorded as equivalent in meaning.',
  [NS.skos + 'closeMatch']: 'Mappings to concepts in other vocabularies recorded as similar, without asserting exact equivalence.',
  [NS.sosa + 'hasProcedure']: 'Procedures associated with this observable property. SoilVoc also includes them in sidebar navigation.',
  [NS.sosa + 'isProcedureFor']: 'The observable properties associated with this procedure.',
  [NS.dcterms + 'source']: 'A resource from which this information was derived.',
  [NS.skos + 'notation']: 'A code or other notation assigned to this concept.',
  [NS.skos + 'scopeNote']: 'Information clarifying the intended scope or use of this concept.',
  [NS.skos + 'historyNote']: 'Information about changes to this concept.',
  [NS.skos + 'note']: 'Additional information recorded about this concept.',
  [NS.rdfs + 'comment']: 'A descriptive comment recorded about this resource.',
}

export const pathKey = path => JSON.stringify(path)
export const safeExternalUrl = value => /^https?:\/\//i.test(value) ? value : null
export function compact(uri) {
  for (const [prefix, namespace] of Object.entries(NS)) {
    if (uri.startsWith(namespace)) return `${prefix}:${uri.slice(namespace.length)}`
  }
  return uri
}
export function localName(uri) { return decodeURIComponent(uri.split(/[#/]/).filter(Boolean).at(-1) || uri) }
function humanName(uri) { return localName(uri).replace(/([a-z])([A-Z])/g, '$1 $2') }
function pickLabel(values, language = 'en') {
  return values.find(t => t.language === language)?.value || values.find(t => !t.language)?.value || values[0]?.value
}
function fold(value) { return value.normalize('NFKD').replace(/\p{M}/gu, '').toLocaleLowerCase() }
function queryParts(query) { return fold(query.trim()).split('*').filter(Boolean) }
function locateParts(text, parts) {
  const normalized = fold(text), ranges = []
  let cursor = 0
  for (const part of parts) {
    const start = normalized.indexOf(part, cursor)
    if (start < 0) return null
    cursor = start + part.length
    ranges.push([start, cursor])
  }
  return ranges
}
export function matchLabel(text, query) {
  const parts = queryParts(query), normalizedRanges = locateParts(text, parts)
  if (!normalizedRanges) return null
  // Folded text can have different offsets from its original Unicode spelling.
  const starts = [], ends = []
  let offset = 0
  for (const char of text) {
    const normalized = fold(char), start = offset
    offset += char.length
    if (!normalized.length && ends.length) ends[ends.length - 1] = offset
    for (let i = 0; i < normalized.length; i++) { starts.push(start); ends.push(offset) }
  }
  const ranges = []
  for (const [start, end] of normalizedRanges) {
    const original = [starts[start], ends[end - 1]]
    if (ranges.length && original[0] <= ranges.at(-1)[1]) ranges.at(-1)[1] = Math.max(ranges.at(-1)[1], original[1])
    else ranges.push(original)
  }
  return { ranges }
}
function xmlEscape(value) {
  return value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
}

async function serializeConceptTurtle(quads) {
  const store = new Store(quads), references = new Map()
  for (const { object } of quads) if (object.termType === 'BlankNode') {
    references.set(object.value, (references.get(object.value) || 0) + 1)
  }
  // In a rooted concept graph, single-reference nodes can be nested without
  // duplicating shared nodes or breaking cycles, whose entry nodes stay named.
  const inline = term => term.termType === 'BlankNode' && references.get(term.value) === 1
  function write(prefixes) {
    return new Promise((resolve, reject) => {
      const writer = new Writer({ format: 'text/turtle', prefixes })
      const object = term => inline(term)
        ? writer.blank(store.getQuads(term, null, null, null).map(q => ({ predicate: q.predicate, object: object(q.object) })))
        : term
      for (const subject of store.getSubjects(null, null, null)) {
        if (inline(subject)) continue
        for (const q of store.getQuads(subject, null, null, null)) writer.addQuad(subject, q.predicate, object(q.object), q.graph)
      }
      writer.end((error, result) => error ? reject(error) : resolve(result))
    })
  }
  // Inspect Turtle tokens so literals, full IRIs, `a`, and abbreviated numeric
  // datatypes do not introduce declarations that the output never uses.
  const preview = await write(NS)
  const used = new Set(new Lexer({ format: 'text/turtle' }).tokenize(preview)
    .filter(token => token.type === 'prefixed' || token.type === 'type').map(token => token.prefix))
  const result = await write(Object.fromEntries(Object.entries(NS).filter(([prefix]) => used.has(prefix))))
  const lines = result.split('\n'), visitedLines = new Set()
  let depth = 0
  // Use syntax tokens rather than bracket characters inside literals or IRIs.
  for (const token of new Lexer({ format: 'text/turtle' }).tokenize(result)) {
    if (token.type === ']') depth--
    if (!visitedLines.has(token.line) && (depth > 0 || token.type === ']')) {
      lines[token.line - 1] = ' '.repeat((depth + 1) * 4) + lines[token.line - 1].slice(token.start)
    }
    visitedLines.add(token.line)
    if (token.type === '[') depth++
  }
  return lines.join('\n')
}

export function createVocabulary(turtle) {
  const quads = new Parser({ format: 'text/turtle' }).parse(turtle)
  const store = new Store(quads)
  const objects = (uri, predicate) => store.getObjects(namedNode(uri), namedNode(predicate), null)
  const label = uri => pickLabel(objects(uri, NS.skos + 'prefLabel')) || pickLabel(objects(uri, NS.rdfs + 'label')) || humanName(uri)
  const sort = values => [...values].sort((a, b) => label(a).localeCompare(label(b), 'en', { numeric: true }) || a.localeCompare(b))
  const schemes = store.getSubjects(namedNode(TYPE), namedNode(NS.skos + 'ConceptScheme'), null).map(t => t.value)
  const schemeUri = schemes[0] || 'https://w3id.org/eusoilvoc'
  const conceptUris = new Set(store.getSubjects(namedNode(TYPE), namedNode(CONCEPT), null).map(t => t.value))
  const parents = new Map([...conceptUris].map(uri => [uri, new Set()]))
  const children = new Map([...conceptUris].map(uri => [uri, new Set()]))
  const concepts = new Map()
  for (const uri of conceptUris) {
    const types = objects(uri, TYPE).map(t => t.value)
    const labels = objects(uri, NS.skos + 'prefLabel')
    const altLabels = objects(uri, NS.skos + 'altLabel')
    const hiddenLabels = objects(uri, NS.skos + 'hiddenLabel')
    const notations = objects(uri, NS.skos + 'notation')
    concepts.set(uri, {
      uri, label: label(uri), types, isProcedure: types.includes(PROCEDURE), isProperty: types.includes(PROPERTY),
      prefLabel: Object.fromEntries(labels.map(t => [t.language || 'und', t.value])),
      altLabels: altLabels.map(t => ({ text: t.value, language: t.language })),
      labelEntries: [[labels, 'prefLabel'], [altLabels, 'altLabel'], [hiddenLabels, 'hiddenLabel'], [notations, 'notation']]
        .flatMap(([terms, kind]) => terms.map(t => ({ text: t.value, language: t.language, kind }))),
      definitions: objects(uri, NS.skos + 'definition').map(term => {
        if (term.termType === 'Literal') return { text: term.value, language: term.language, sources: [], term }
        const texts = store.getObjects(term, namedNode(NS.rdf + 'value'), null)
        const legacy = texts.length ? texts : store.getObjects(term, namedNode('https://schema.org/text'), null)
        return {
          text: pickLabel(legacy) || '', language: legacy.find(t => t.language === 'en')?.language || legacy[0]?.language || '',
          texts: legacy.map(t => ({ text: t.value, language: t.language })),
          sources: store.getObjects(term, namedNode(NS.dcterms + 'source'), null), term,
        }
      }),
    })
  }
  // Only the navigation projection combines SKOS and SOSA. Semantic triples stay untouched.
  const addEdge = (child, parent) => {
    if (!conceptUris.has(child) || !conceptUris.has(parent) || child === parent) return
    parents.get(child).add(parent)
    children.get(parent).add(child)
  }
  for (const [predicate, inverse] of [
    [NS.skos + 'broader', false], [NS.skos + 'narrower', true],
    [NS.sosa + 'isProcedureFor', false], [NS.sosa + 'hasProcedure', true], [DISPLAY_PARENT, false],
  ]) {
    for (const quad of store.getQuads(null, namedNode(predicate), null, null)) {
      addEdge(inverse ? quad.object.value : quad.subject.value, inverse ? quad.subject.value : quad.object.value)
    }
  }
  const roots = sort([...conceptUris].filter(uri => !parents.get(uri).size))
  const rootSet = new Set(roots)
  const sortedConcepts = sort(conceptUris).map(uri => concepts.get(uri))
  const typeUris = sort(new Set(sortedConcepts.flatMap(c => c.types)))

  const pathCache = new Map()
  function pathsTo(uri) {
    if (!concepts.has(uri)) return []
    if (pathCache.has(uri)) return pathCache.get(uri)
    const paths = [], pending = [[uri]]
    while (pending.length) {
      const reverse = pending.pop(), current = reverse.at(-1)
      if (rootSet.has(current)) paths.push([...reverse].reverse())
      else for (const parent of sort(parents.get(current)).reverse()) {
        if (!reverse.includes(parent)) pending.push([...reverse, parent])
      }
    }
    pathCache.set(uri, paths)
    return paths
  }

  function pathTo(uri, hint = []) {
    if (!concepts.has(uri)) return []
    if (hint.includes(uri)) return hint.slice(0, hint.indexOf(uri) + 1)
    if (hint.length && children.get(hint.at(-1))?.has(uri) && !hint.includes(uri)) return [...hint, uri]
    const queue = [[uri]], seen = new Set([uri])
    let fallback = null
    for (let i = 0; i < queue.length; i++) {
      const reverse = queue[i], current = reverse.at(-1)
      if (rootSet.has(current)) {
        const path = [...reverse].reverse()
        if (!hint[0] || current === hint[0]) return path
        fallback ||= path
      }
      for (const parent of sort(parents.get(current) || [])) {
        if (!seen.has(parent)) { seen.add(parent); queue.push([...reverse, parent]) }
      }
    }
    return fallback || [uri]
  }
  function validPath(path, target) {
    return Array.isArray(path) && path.length > 0 && path.at(-1) === target && rootSet.has(path[0]) &&
      new Set(path).size === path.length && path.every((uri, i) => concepts.has(uri) && (!i || children.get(path[i - 1]).has(uri)))
  }
  function searchMatches(query, type = '', limit = Infinity) {
    const parts = queryParts(query), results = []
    for (const concept of sortedConcepts) {
      if (type && !concept.types.includes(type)) continue
      if (!parts.length) { results.push({ concept, match: null, score: 0 }); continue }
      let best = null
      for (const entry of concept.labelEntries) {
        const ranges = locateParts(entry.text, parts)
        if (!ranges) continue
        const preferred = entry.text === concept.label
        const score = preferred ? (parts.length === 1 && fold(entry.text) === parts[0] ? 0 : ranges[0][0] === 0 ? 1 : 2) : 3
        if (!best || score < best.score) best = { ...entry, preferred, score }
      }
      if (best) results.push({ concept, match: { ...best, ...matchLabel(best.text, query) }, score: best.score })
    }
    if (parts.length) results.sort((a, b) => a.score - b.score || a.concept.label.localeCompare(b.concept.label))
    return results.slice(0, limit)
  }
  function search(query, type = '', limit = Infinity) {
    return searchMatches(query, type, limit).map(result => result.concept)
  }
  function propertyTooltip(predicate) {
    return pickLabel(objects(predicate, NS.rdfs + 'comment')) || propertyHelp[predicate] || `Values recorded for the ${label(predicate)} relationship in the vocabulary.`
  }
  function describe(term, seen = new Set()) {
    if (term.termType === 'Literal') return { kind: 'literal', text: term.value, language: term.language, datatype: term.datatype?.value }
    if (term.termType === 'NamedNode') {
      const resourceLabel = pickLabel(objects(term.value, NS.skos + 'prefLabel')) || pickLabel(objects(term.value, NS.rdfs + 'label')) || term.value
      return { kind: 'resource', uri: term.value, label: resourceLabel, local: concepts.has(term.value), defined: store.countQuads(term, null, null, null) > 0 }
    }
    if (seen.has(term.value)) return { kind: 'literal', text: 'Circular blank-node reference' }
    const nextSeen = new Set([...seen, term.value])
    return { kind: 'blank', id: term.value, properties: store.getQuads(term, null, null, null).map(q => ({ predicate: q.predicate.value, label: label(q.predicate.value), value: describe(q.object, nextSeen) })) }
  }
  function propertiesFor(uri, technical = false) {
    const grouped = new Map()
    for (const q of store.getQuads(namedNode(uri), null, null, null)) {
      const predicate = q.predicate.value
      if (!technical && omitted.has(predicate)) continue
      if (!grouped.has(predicate)) grouped.set(predicate, [])
      grouped.get(predicate).push(describe(q.object))
    }
    return [...grouped].map(([predicate, values]) => ({ predicate, label: captions[predicate] || label(predicate), values }))
      .sort((a, b) => {
        const x = propertyOrder.indexOf(a.predicate), y = propertyOrder.indexOf(b.predicate)
        return (x < 0 ? 999 : x) - (y < 0 ? 999 : y) || a.label.localeCompare(b.label)
      })
  }
  function asJskos(uri) {
    const c = concepts.get(uri)
    if (!c) return { uri, prefLabel: { en: label(uri) } }
    return {
      uri, prefLabel: c.prefLabel, type: c.types, notation: objects(uri, NS.skos + 'notation').map(t => xmlEscape(t.value)),
      altLabel: { en: c.altLabels.map(t => t.text) }, inScheme: [{ uri: schemeUri }],
    }
  }
  function conceptQuads(uri) {
    const collected = [], seen = new Set()
    function visit(subject) {
      const key = subject.termType + ':' + subject.value
      if (seen.has(key)) return
      seen.add(key)
      for (const q of store.getQuads(subject, null, null, null)) {
        collected.push(q)
        if (q.object.termType === 'BlankNode') visit(q.object)
      }
    }
    visit(namedNode(uri))
    return collected
  }
  async function serialize(uri, format) {
    const selected = uri ? conceptQuads(uri) : quads
    if (format === 'ttl') {
      if (!uri) return turtle
      return serializeConceptTurtle(selected)
    }
    if (format === 'jsonld') {
      const nodes = new Map()
      const id = term => term.termType === 'BlankNode' ? '_:' + term.value : term.value
      for (const q of selected) {
        const key = id(q.subject)
        if (!nodes.has(key)) nodes.set(key, { '@id': key })
        const node = nodes.get(key), predicate = q.predicate.value
        const value = q.object.termType === 'Literal'
          ? { '@value': q.object.value, ...(q.object.language ? { '@language': q.object.language } : q.object.datatype.value !== NS.xsd + 'string' ? { '@type': q.object.datatype.value } : {}) }
          : { '@id': id(q.object) }
        ;(node[predicate] ||= []).push(value)
      }
      return JSON.stringify({ '@graph': [...nodes.values()] }, null, 2)
    }
    if (format === 'rdf') {
      const namespaces = new Map(), nodes = new Map()
      for (const q of selected) {
        const predicate = q.predicate.value
        const match = predicate.match(/^(.*[#/])([^#/]+)$/)
        if (!match || !/^[A-Za-z_][\w.-]*$/.test(match[2])) throw new Error('Predicate cannot be represented in RDF/XML: ' + predicate)
        if (!namespaces.has(match[1])) namespaces.set(match[1], 'p' + namespaces.size)
        const key = q.subject.termType + ':' + q.subject.value
        if (!nodes.has(key)) nodes.set(key, { subject: q.subject, values: [] })
        nodes.get(key).values.push({ q, namespace: match[1], name: match[2] })
      }
      const nodeIds = new Map()
      const nodeId = term => {
        if (!nodeIds.has(term.value)) nodeIds.set(term.value, 'b' + nodeIds.size)
        return nodeIds.get(term.value)
      }
      let out = '<?xml version="1.0" encoding="UTF-8"?>\n<rdf:RDF xmlns:rdf="' + NS.rdf + '"'
      for (const [namespace, prefix] of namespaces) out += ` xmlns:${prefix}="${xmlEscape(namespace)}"`
      out += '>\n'
      for (const { subject, values } of nodes.values()) {
        out += `  <rdf:Description ${subject.termType === 'BlankNode' ? `rdf:nodeID="${nodeId(subject)}"` : `rdf:about="${xmlEscape(subject.value)}"`}>\n`
        for (const { q, namespace, name } of values) {
          const tag = namespaces.get(namespace) + ':' + name, object = q.object
          if (object.termType === 'NamedNode') out += `    <${tag} rdf:resource="${xmlEscape(object.value)}"/>\n`
          else if (object.termType === 'BlankNode') out += `    <${tag} rdf:nodeID="${nodeId(object)}"/>\n`
          else out += `    <${tag}${object.language ? ` xml:lang="${object.language}"` : object.datatype.value !== NS.xsd + 'string' ? ` rdf:datatype="${xmlEscape(object.datatype.value)}"` : ''}>${xmlEscape(object.value)}</${tag}>\n`
        }
        out += '  </rdf:Description>\n'
      }
      return out + '</rdf:RDF>\n'
    }
    throw new Error('Unsupported format: ' + format)
  }
  const declaredClasses = new Set(store.getSubjects(namedNode(TYPE), namedNode(NS.rdfs + 'Class'), null).map(t => t.value))
  const declaredProperties = new Set(store.getSubjects(namedNode(TYPE), namedNode(NS.rdf + 'Property'), null).map(t => t.value))
  const declarations = new Set([...declaredClasses, ...declaredProperties])
  const usedClasses = new Set(), usedProperties = new Set(), visited = new Set()
  const pending = [...conceptUris, ...schemes].map(uri => namedNode(uri))
  // Follow instance metadata, including definition nodes, without treating
  // ontology descriptions themselves as evidence that a term is in use.
  while (pending.length) {
    const subject = pending.pop(), key = subject.termType + ':' + subject.value
    if (visited.has(key)) continue
    visited.add(key)
    for (const { predicate, object } of store.getQuads(subject, null, null, null)) {
      usedProperties.add(predicate.value)
      if (predicate.value === TYPE) {
        if (object.termType === 'NamedNode') usedClasses.add(object.value)
      } else if (object.termType === 'BlankNode' || (object.termType === 'NamedNode' && !declarations.has(object.value))) {
        pending.push(object)
      }
    }
  }
  const ontology = {
    classes: sort([...declaredClasses].filter(uri => usedClasses.has(uri))),
    properties: sort([...declaredProperties].filter(uri => usedProperties.has(uri))),
  }
  return {
    store, concepts, sortedConcepts, parents, children, roots, typeUris, schemeUri, ontology,
    objects, label, sort, pathTo, pathsTo, validPath, search, searchMatches, matchLabel, propertyTooltip, describe, propertiesFor, asJskos, conceptQuads, serialize,
    sourceText: turtle,
    stats: { concepts: concepts.size, procedures: sortedConcepts.filter(c => c.isProcedure).length,
      properties: sortedConcepts.filter(c => c.isProperty).length,
      definitions: sortedConcepts.reduce((n, c) => n + c.definitions.length, 0),
      navigationEdges: [...children.values()].reduce((n, values) => n + values.size, 0), triples: quads.length,
      preferredLabels: sortedConcepts.reduce((n, c) => n + c.labelEntries.filter(l => l.kind === 'prefLabel').length, 0),
      alternativeLabels: sortedConcepts.reduce((n, c) => n + c.labelEntries.filter(l => l.kind === 'altLabel').length, 0),
      hiddenLabels: sortedConcepts.reduce((n, c) => n + c.labelEntries.filter(l => l.kind === 'hiddenLabel').length, 0) },
  }
}
