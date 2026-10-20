import test from 'node:test'
import assert from 'node:assert/strict'
import { detailSections } from '../src/presentation.js'
import { NS } from '../src/vocabulary.js'

test('reading sections preserve all predicates and source values without rewriting the graph', () => {
  const groups = [
    { predicate: NS.sosa + 'hasProcedure', values: [{ kind: 'resource', local: true }] },
    { predicate: NS.skos + 'exactMatch', values: [{ kind: 'resource', local: true }] },
    { predicate: NS.skos + 'altLabel', values: [{ kind: 'literal', text: 'synonym' }] },
    { predicate: 'https://example.org/custom', values: [{ kind: 'blank', properties: [] }] },
  ]
  const sections = detailSections(groups)
  assert.deepEqual(sections.map(section => section.id), ['relationships', 'annotations', 'other', 'mappings'])
  const ordered = [groups[0], groups[2], groups[3], groups[1]]
  assert.deepEqual(sections.flatMap(section => section.groups), ordered)
  sections.forEach((section, index) => assert.equal(section.groups[0], ordered[index]))
})

test('all SKOS mapping kinds stay together and empty sections are omitted', () => {
  const groups = ['exactMatch', 'closeMatch', 'broadMatch', 'narrowMatch', 'relatedMatch', 'mappingRelation'].map(name => ({ predicate: NS.skos + name, values: [] }))
  assert.deepEqual(detailSections(groups).map(section => section.id), ['mappings'])
  assert.deepEqual(detailSections([]), [])
})
