import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { createVocabulary, NS } from '../src/vocabulary.js'
import { detailSections } from '../src/presentation.js'
import { mappingSources } from '../src/mapping-sources.js'

const model = createVocabulary(readFileSync(new URL('../../skosmos/SoilVoc_skosmos.ttl', import.meta.url), 'utf8'))

test('all current mappings stay last, retain their full concept URIs, and have a known source vocabulary', () => {
  const original = model.sourceText
  let count = 0
  for (const concept of model.concepts.values()) {
    const sections = detailSections(model.propertiesFor(concept.uri))
    const mappings = sections.find(section => section.id === 'mappings')
    if (!mappings) continue
    assert.equal(sections.at(-1), mappings)
    for (const group of mappings.groups) for (const value of group.values) {
      const source = mappingSources(value, model)
      assert.equal(source.length, 1, value.uri)
      assert.ok(source[0].uri.startsWith('http'), value.uri)
      assert.notEqual(source[0].uri, value.uri)
      count++
    }
  }
  assert.equal(count, 2372)
  assert.equal(model.sourceText, original)
})

test('soil water constants pairs AGROVOC and NALT concepts with the correct vocabulary roots', () => {
  const values = model.propertiesFor(NS.eusoilvoc + 'SoilWaterConstants').find(group => group.predicate === NS.skos + 'exactMatch').values
  assert.deepEqual(values.map(value => ({ concept: value.uri, sources: mappingSources(value, model) })), [
    { concept: 'http://aims.fao.org/aos/agrovoc/c_32444', sources: [{ uri: 'http://aims.fao.org/aos/agrovoc', label: 'AGROVOC' }] },
    { concept: 'https://lod.nal.usda.gov/nalt/304816', sources: [{ uri: 'https://lod.nal.usda.gov/nalt', label: 'USDA NALT' }] },
  ])
})

test('explicit RDF scheme metadata takes precedence and multiple memberships are retained', () => {
  const explicit = createVocabulary(`@prefix skos: <${NS.skos}> . @prefix rdfs: <${NS.rdfs}> .
    <http://aims.fao.org/aos/agrovoc/c_32444> skos:inScheme <https://example.org/scheme>, <https://example.org/other> .
    <https://example.org/scheme> rdfs:label "Explicit source"@en .
    <https://example.org/term> rdfs:isDefinedBy <https://example.org/ontology> .`)
  assert.deepEqual(mappingSources({ kind: 'resource', uri: 'http://aims.fao.org/aos/agrovoc/c_32444' }, explicit), [
    { uri: 'https://example.org/scheme', label: 'Explicit source' },
    { uri: 'https://example.org/other', label: 'https://example.org/other' },
  ])
  assert.deepEqual(mappingSources({ kind: 'resource', uri: 'https://example.org/term' }, explicit), [{ uri: 'https://example.org/ontology', label: 'https://example.org/ontology' }])
})

test('source lookup accepts HTTP/HTTPS variants but does not invent sources for unknown or unsafe URIs', () => {
  for (const uri of ['http://aims.fao.org/aos/agrovoc/c_1', 'https://aims.fao.org/aos/agrovoc/c_1']) {
    assert.equal(mappingSources({ kind: 'resource', uri }, model)[0].label, 'AGROVOC')
  }
  for (const uri of ['https://example.org/term', 'https://aims.fao.org.evil.example/aos/agrovoc/c_1', 'javascript:alert(1)']) {
    assert.deepEqual(mappingSources({ kind: 'resource', uri }, model), [])
  }
  assert.deepEqual(mappingSources({ kind: 'literal', text: 'not a resource' }, model), [])
})
