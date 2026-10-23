import { NS } from './vocabulary.js'

const mappings = new Set(['exactMatch', 'closeMatch', 'broadMatch', 'narrowMatch', 'relatedMatch', 'mappingRelation'].map(name => NS.skos + name))
const annotations = new Set(['altLabel', 'hiddenLabel', 'notation', 'note', 'scopeNote', 'historyNote', 'editorialNote', 'changeNote', 'example'].map(name => NS.skos + name))

export function displayValues(values) {
  // Only unordered concept links are sorted; literals and RDF list nodes retain their order.
  if (!values.every(value => value.kind === 'resource' && value.local)) return values
  return [...values].sort((a, b) => a.label.localeCompare(b.label, 'en', { numeric: true }) || a.uri.localeCompare(b.uri))
}

// Group for reading only; retain every predicate and its original values.
export function detailSections(groups) {
  const sections = [
    { id: 'relationships', label: 'Relationships', groups: [] },
    { id: 'annotations', label: 'Labels and notes', groups: [] },
    { id: 'other', label: 'Additional information', groups: [] },
    { id: 'mappings', label: 'External mappings', groups: [] },
  ]
  for (const group of groups) {
    const index = mappings.has(group.predicate) ? 3
      : annotations.has(group.predicate) ? 1
      : group.values.some(value => value.kind === 'resource' && value.local) ? 0 : 2
    sections[index].groups.push(group)
  }
  return sections.filter(section => section.groups.length)
}
