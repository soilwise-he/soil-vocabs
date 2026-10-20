import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { Lexer, Parser, Store, DataFactory } from 'n3'
import { createVocabulary, NS, TYPE, CONCEPT, PROCEDURE, PROPERTY, DISPLAY_PARENT, pathKey, safeExternalUrl, matchLabel } from '../src/vocabulary.js'
import { parseRoute } from '../src/navigation.js'

const source = readFileSync(new URL('../../skosmos/SoilVoc_skosmos.ttl', import.meta.url), 'utf8')
const model = createVocabulary(source)
const uri = name => NS.eusoilvoc + name
const { namedNode } = DataFactory

test('loads the full source, including procedures and ontology', () => {
  assert.deepEqual(model.stats, { concepts: 1464, procedures: 249, properties: 192, definitions: 1110, navigationEdges: 2230, triples: 27157, preferredLabels: 1464, alternativeLabels: 426, hiddenLabels: 0 })
  assert.equal(model.roots.length, 17)
  assert.equal(model.ontology.classes.length, 4)
  assert.equal(model.ontology.properties.length, 35)
  assert.equal(model.label(PROPERTY), 'Observable Property')
  assert.equal(model.label(PROCEDURE), 'Procedure')
  assert.equal(model.sourceText, source)
})

test('every current concept resolves through its canonical fragment identifier', () => {
  for (const concept of model.concepts.values()) {
    assert.ok(concept.uri.startsWith(NS.eusoilvoc))
    const hash = '#' + encodeURIComponent(concept.uri.slice(NS.eusoilvoc.length))
    const route = parseRoute('', NS.eusoilvoc, hash)
    assert.equal(route.uri, concept.uri)
    assert.equal(route.view, 'concept')
  }
  assert.equal(model.concepts.get(NS.eusoilvoc + 'CulturalServices').label, 'cultural services')
})

test('every direct SKOS, SOSA and projected edge is available in navigation', () => {
  for (const [predicate, inverse] of [[NS.skos + 'broader', false], [NS.skos + 'narrower', true], [NS.sosa + 'isProcedureFor', false], [NS.sosa + 'hasProcedure', true], [DISPLAY_PARENT, false]]) {
    for (const q of model.store.getQuads(null, namedNode(predicate), null, null)) {
      const child = inverse ? q.object.value : q.subject.value, parent = inverse ? q.subject.value : q.object.value
      if (!model.concepts.has(child) || !model.concepts.has(parent) || child === parent) continue
      assert.ok(model.parents.get(child).has(parent), `${predicate}: ${child}`)
      assert.ok(model.children.get(parent).has(child), `${predicate}: ${parent}`)
    }
  }
})

test('every concept has a valid complete path and all branches are acyclic', () => {
  for (const concept of model.sortedConcepts) assert.ok(model.validPath(model.pathTo(concept.uri), concept.uri), concept.uri)
  const visiting = new Set(), complete = new Set()
  function visit(current) {
    assert.ok(!visiting.has(current), `Cycle at ${current}`)
    if (complete.has(current)) return
    visiting.add(current)
    for (const child of model.children.get(current)) visit(child)
    visiting.delete(current); complete.add(current)
  }
  for (const root of model.roots) visit(root)
  assert.equal(complete.size, model.concepts.size)
})

test('base saturation has both procedures and nested pH procedures have a full path', () => {
  assert.deepEqual(model.sort(model.children.get(uri('BaseSaturation'))).map(model.label), ['BSat_calcul-cec', 'BSat_calcul-ecec'])
  const target = uri('pHProcedure-pHCaCl2_ratio1-1'), path = model.pathTo(target)
  assert.equal(path.at(-2), uri('pHProcedure-pHCaCl2'))
  assert.ok(path.includes(uri('SoilpH')))
  assert.equal(model.concepts.get(target).isProcedure, true)
  for (const concept of model.sortedConcepts) assert.equal(concept.isProcedure, concept.types.includes(PROCEDURE))
})

test('polyhierarchy preserves distinct occurrence paths without changing concept URIs', () => {
  const shared = model.sortedConcepts.filter(c => model.parents.get(c.uri).size > 1)
  assert.equal(shared.length, 186)
  for (const concept of shared) {
    const paths = [...model.parents.get(concept.uri)].map(parent => [...model.pathTo(parent), concept.uri])
    for (const path of paths) assert.ok(model.validPath(path, concept.uri))
    assert.equal(new Set(paths.map(pathKey)).size, paths.length)
  }
  const target = uri('SoilpH')
  for (const parent of model.parents.get(target)) {
    const context = model.pathTo(parent)
    assert.deepEqual(model.pathTo(target, context), [...context, target])
  }
  assert.equal(model.validPath(['not-a-concept', target], target), false)
  assert.equal(model.validPath([model.roots[0], target, target], target), false)
})

test('all four hydraulic-conductivity paths are exposed, including shared-parent paths', () => {
  const target = uri('SoilHydraulicConductivity'), paths = model.pathsTo(target)
  assert.equal(paths.length, 4)
  assert.equal(new Set(paths.map(pathKey)).size, 4)
  assert.equal(new Set(paths.map(p => p.at(-2))).size, 3)
  for (const path of paths) assert.ok(model.validPath(path, target))
  const current = paths.at(-1)
  assert.deepEqual(model.pathTo(target, current), current)
  for (const concept of model.sortedConcepts) {
    const alternatives = model.pathsTo(concept.uri)
    assert.ok(alternatives.length > 0, concept.uri)
    for (const path of alternatives) assert.ok(model.validPath(path, concept.uri))
  }
})

test('every definition retains its own RDF value, source and blank-node identity', () => {
  let sources = 0, blanks = 0, literals = 0
  for (const concept of model.sortedConcepts) for (const definition of concept.definitions) {
    assert.ok(definition.text.length, concept.uri)
    if (definition.term.termType === 'BlankNode') {
      blanks++
      const rawTexts = model.store.getObjects(definition.term, namedNode(NS.rdf + 'value'), null)
      assert.ok(rawTexts.some(t => t.value === definition.text))
      assert.deepEqual(definition.sources, model.store.getObjects(definition.term, namedNode(NS.dcterms + 'source'), null))
    } else literals++
    sources += definition.sources.length
  }
  assert.equal(blanks, 1109); assert.equal(literals, 1); assert.equal(sources, 1109)
  const base = model.concepts.get(uri('BaseSaturation'))
  assert.equal(base.definitions.length, 2)
  assert.notEqual(base.definitions[0].sources[0].value, base.definitions[1].sources[0].value)
})

test('substring search includes prefLabels and synonyms with readable type labels', () => {
  const results = model.search('*Hydraulic conductivity*')
  assert.equal(results.length, 3)
  assert.ok(results.some(c => c.uri === uri('SoilHydraulicConductivity')))
  assert.deepEqual(model.search('HYDRAULIC CONDUCTIVITY').map(c => c.uri), results.map(c => c.uri))
  assert.equal(model.search('hydraulic conductivity', PROPERTY).length, 1)
  assert.equal(model.search('not-present-24931723').length, 0)
  assert.doesNotThrow(() => model.search('['))
  assert.equal(model.search('', PROCEDURE).length, 249)
  for (const concept of model.sortedConcepts.filter(c => c.altLabels.length)) {
    assert.ok(model.search(concept.altLabels[0].text).some(result => result.uri === concept.uri))
  }
})

test('internal wildcards match ordered chunks without interpreting regex syntax', () => {
  const expected = model.search('hydraulic conductivity').map(c => c.uri)
  for (const query of ['hydraulic*conductivity', '*HYDRAULIC**CONDUCTIVITY*', 'hydraulic*conduct*']) {
    assert.deepEqual(model.search(query).map(c => c.uri), expected)
  }
  assert.equal(model.search('conductivity*hydraulic').length, 0)
  assert.equal(model.search('hydraulic.*conductivity').length, 0)
  assert.equal(model.search('*').length, 1464)
})

test('autocomplete explains alternative-label matches and supplies original-text highlights', () => {
  const [result] = model.searchMatches('alluvial deposits')
  assert.equal(result.concept.label, 'alluvium')
  assert.equal(result.match.text, 'alluvial deposits')
  assert.equal(result.match.kind, 'altLabel')
  assert.equal(result.match.preferred, false)
  assert.deepEqual(result.match.ranges, [[0, 17]])
  assert.deepEqual(matchLabel('Soil Hydraulic conductivity', 'hydraulic*conductivity').ranges, [[5, 14], [15, 27]])
  assert.deepEqual(matchLabel('Cafe\u0301 soil', 'cafe').ranges, [[0, 5]])
  assert.deepEqual(matchLabel('Caf\u00e9 soil', 'cafe').ranges, [[0, 4]])
  assert.equal(matchLabel('alluvium', 'alluvial deposits'), null)
  assert.deepEqual(matchLabel('[safe]', '[safe]').ranges, [[0, 6]])
})

test('property explanations and label statistics are distinct from predicate URIs', () => {
  assert.match(model.propertyTooltip(NS.skos + 'broader'), /directly broader/)
  assert.match(model.propertyTooltip(NS.sosa + 'hasProcedure'), /observable property/)
  assert.equal(model.stats.preferredLabels, model.store.countQuads(null, namedNode(NS.skos + 'prefLabel'), null, null))
  assert.equal(model.stats.alternativeLabels, model.store.countQuads(null, namedNode(NS.skos + 'altLabel'), null, null))
})

const fixture = `
@prefix ex: <https://example.org/> .
@prefix skos: <${NS.skos}> .
@prefix rdf: <${NS.rdf}> .
@prefix rdfs: <${NS.rdfs}> .
@prefix sosa: <${NS.sosa}> .
@prefix dcterms: <${NS.dcterms}> .
ex:root a skos:Concept ; skos:prefLabel "Root"@en ; sosa:hasProcedure ex:p .
ex:p a skos:Concept, sosa:Procedure ; skos:prefLabel "Procedure"@en ; skos:narrower ex:q .
ex:q a skos:Concept, sosa:Procedure ; skos:prefLabel "Nested procedure"@en .
ex:customType a rdfs:Class ; rdfs:label "Advanced type"@en .
ex:affects a rdf:Property ; rdfs:label "Affects"@en .
ex:a a skos:Concept, ex:customType ; skos:prefLabel "Same label"@en ; skos:broader ex:root ;
  ex:affects ex:b ; skos:definition [ rdf:value "A & B <script>safe text</script>"@en ; dcterms:source ex:sourceA ],
  [ rdf:value "Another definition"@en ; dcterms:source ex:sourceB ] ;
  skos:notation "<img src=x onerror=alert(1)>" ; ex:metadata [ ex:count 7 ; ex:link ex:b ] .
ex:b a skos:Concept ; skos:prefLabel "Same label"@en ; skos:broader ex:root .
ex:cycleA a skos:Concept ; skos:prefLabel "Cycle A"@en ; skos:broader ex:cycleB .
ex:cycleB a skos:Concept ; skos:prefLabel "Cycle B"@en ; skos:broader ex:cycleA .
`
const custom = createVocabulary(fixture)
test('hidden labels and notations retain their match kind and label counts', () => {
  const extended = createVocabulary(fixture + '\nex:a skos:hiddenLabel "buried synonym"@en ; skos:altLabel "another alias"@en ; skos:notation "ABC-123" .')
  assert.equal(extended.searchMatches('buried*synonym')[0].match.kind, 'hiddenLabel')
  assert.equal(extended.searchMatches('ABC*123')[0].match.kind, 'notation')
  assert.equal(extended.stats.preferredLabels, 7)
  assert.equal(extended.stats.alternativeLabels, 1)
  assert.equal(extended.stats.hiddenLabels, 1)
})

test('generic advanced types, arbitrary relationships and nested RDF remain available', () => {
  assert.ok(custom.concepts.get('https://example.org/a').types.includes('https://example.org/customType'))
  const properties = custom.propertiesFor('https://example.org/a')
  const affects = properties.find(p => p.predicate === 'https://example.org/affects')
  assert.equal(affects.label, 'Affects')
  assert.equal(affects.values[0].uri, 'https://example.org/b')
  const metadata = properties.find(p => p.predicate === 'https://example.org/metadata').values[0]
  assert.equal(metadata.kind, 'blank')
  assert.equal(metadata.properties.length, 2)
  assert.equal(custom.search('Same label').length, 2)
  assert.equal(custom.describe(namedNode('https://external.example.org/id/123')).label, 'https://external.example.org/id/123')
  assert.deepEqual(custom.pathTo('https://example.org/q'), ['https://example.org/root', 'https://example.org/p', 'https://example.org/q'])
  assert.ok(!custom.propertiesFor(uri('BaseSaturation')).some(p => p.predicate === DISPLAY_PARENT))
})

test('cyclic input cannot loop forever and invalid external URLs are not linked', () => {
  assert.deepEqual(custom.pathTo('https://example.org/cycleA'), ['https://example.org/cycleA'])
  assert.deepEqual(custom.pathsTo('https://example.org/cycleA'), [])
  assert.equal(safeExternalUrl('javascript:alert(1)'), null)
  assert.equal(safeExternalUrl('data:text/html,hello'), null)
  assert.equal(safeExternalUrl('https://example.org/'), 'https://example.org/')
  assert.ok(custom.asJskos('https://example.org/a').notation[0].startsWith('&lt;img'))
})

test('all single-concept Turtle exports parse and include sourced blank nodes', async () => {
  for (const concept of model.sortedConcepts) {
    const text = await model.serialize(concept.uri, 'ttl')
    assert.equal(new Parser().parse(text).length, model.conceptQuads(concept.uri).length, concept.uri)
    const tokens = new Lexer().tokenize(text)
    const declared = new Set(tokens.filter(t => t.type === 'prefix').map(t => t.value))
    const used = new Set(tokens.filter(t => t.type === 'prefixed' || (t.type === 'type' && t.prefix)).map(t => t.prefix))
    assert.deepEqual(declared, used, concept.uri)
  }
  assert.equal(await model.serialize(null, 'ttl'), source)
})

test('concept Turtle nests definition blank nodes and keeps each definition paired with its sources', async () => {
  for (const current of [uri('BaseSaturation'), uri('hydraulicConductivityProcedure-KSat_calcul-ptf-saxton')]) {
    const text = await model.serialize(current, 'ttl')
    assert.match(text, /skos:definition \[/)
    assert.match(text, /^ {8}rdf:value /m)
    assert.match(text, /^ {4}\]/m)
    assert.ok(!new Lexer().tokenize(text).some(t => t.type === 'blank'))
    const restored = createVocabulary(text)
    const definitions = m => m.concepts.get(current).definitions.map(d => ({ text: d.text, language: d.language, sources: d.sources.map(s => s.value) }))
    assert.deepEqual(definitions(restored), definitions(model))
  }
})

test('Turtle prefixes follow actual prefixed terms and explicit datatypes, not literal text', async () => {
  const input = `@prefix eusoilvoc: <${NS.eusoilvoc}> . @prefix skos: <${NS.skos}> . @prefix xsd: <${NS.xsd}> .
    eusoilvoc:Example a skos:Concept ; skos:prefLabel "rdf:value and owl:Class [ ] are literal text"@en ;
      skos:notation 7, true, "plain", <${NS.sio}not/a/local/name> .`
  const simple = await createVocabulary(input).serialize(uri('Example'), 'ttl')
  assert.deepEqual(new Lexer().tokenize(simple).filter(t => t.type === 'prefix').map(t => t.value), ['skos', 'eusoilvoc'])
  const dated = await createVocabulary(input + '\neusoilvoc:Example skos:notation "2026-10-20"^^xsd:date .').serialize(uri('Example'), 'ttl')
  assert.match(dated, /@prefix xsd:/)
  const parsed = new Store(new Parser().parse(dated))
  assert.ok(parsed.getObjects(namedNode(uri('Example')), namedNode(NS.skos + 'notation'), null).some(t => t.datatype?.value === NS.xsd + 'date'))
})

test('Turtle nesting preserves shared and cyclic blank nodes, nested metadata, and distinct identical nodes', async () => {
  const input = `@prefix ex: <https://example.org/> . @prefix skos: <${NS.skos}> .
    @prefix rdf: <${NS.rdf}> . @prefix dcterms: <${NS.dcterms}> .
    ex:root a skos:Concept ; skos:prefLabel "Root"@en ; skos:definition _:shared ; ex:metadata _:shared ;
      ex:nested [ ex:child [ rdf:value "Nested"@en ; dcterms:source ex:source ] ] ;
      ex:distinct [ rdf:value "Same" ], [ rdf:value "Same" ] ; ex:empty [] ; ex:cycle _:a .
    _:shared rdf:value "Shared"@en ; dcterms:source ex:source .
    _:a ex:next _:b . _:b ex:next _:a .`
  const original = createVocabulary(input), root = 'https://example.org/root'
  const text = await original.serialize(root, 'ttl'), restored = new Store(new Parser().parse(text))
  assert.equal(restored.size, original.conceptQuads(root).length)
  const values = (subject, predicate) => restored.getObjects(subject, namedNode(predicate), null)
  const value = (subject, predicate) => values(subject, predicate)[0]
  const definition = value(namedNode(root), NS.skos + 'definition')
  assert.equal(definition.termType, 'BlankNode')
  assert.ok(definition.equals(value(namedNode(root), 'https://example.org/metadata')))
  assert.equal(value(definition, NS.rdf + 'value').value, 'Shared')
  assert.equal(value(definition, NS.dcterms + 'source').value, 'https://example.org/source')
  const nested = value(value(namedNode(root), 'https://example.org/nested'), 'https://example.org/child')
  assert.equal(value(nested, NS.rdf + 'value').value, 'Nested')
  assert.equal(value(nested, NS.dcterms + 'source').value, 'https://example.org/source')
  const distinct = values(namedNode(root), 'https://example.org/distinct')
  assert.equal(distinct.length, 2)
  assert.ok(!distinct[0].equals(distinct[1]))
  assert.equal(value(namedNode(root), 'https://example.org/empty').termType, 'BlankNode')
  const cycle = value(namedNode(root), 'https://example.org/cycle')
  assert.ok(cycle.equals(value(value(cycle, 'https://example.org/next'), 'https://example.org/next')))
})

test('JSON-LD preserves all outgoing statements and blank node references', async () => {
  for (const current of [uri('BaseSaturation'), uri('pHProcedure-pHCaCl2_ratio1-1'), ...custom.concepts.keys()]) {
    const m = current.startsWith('https://example.org/') ? custom : model
    const graph = JSON.parse(await m.serialize(current, 'jsonld'))['@graph']
    const statements = graph.reduce((n, node) => n + Object.entries(node).filter(([key]) => key !== '@id').reduce((sum, [, values]) => sum + values.length, 0), 0)
    assert.equal(statements, m.conceptQuads(current).length)
  }
})

test('RDF/XML escapes text, keeps blank node sources and valid node identifiers', async () => {
  const xml = await custom.serialize('https://example.org/a', 'rdf')
  assert.ok(xml.includes('A &amp; B &lt;script&gt;safe text&lt;/script&gt;'))
  assert.match(xml, /rdf:nodeID="b0"/)
  assert.ok(xml.includes('https://example.org/sourceA'))
  assert.ok(xml.includes('https://example.org/sourceB'))
  const full = await model.serialize(null, 'rdf')
  assert.ok(full.startsWith('<?xml'))
  assert.ok(full.includes('xml:lang="en"'))
})
