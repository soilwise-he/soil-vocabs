import { NS, safeExternalUrl } from './vocabulary.js'

// Display metadata only: these namespace lookups never add scheme assertions to RDF.
// Scheme identifiers: https://agrovoc.fao.org/browse/agrovoc/en/
// and https://thesaurus.inrae.fr/thesaurus-inrae/en/.
const sources = [
  { prefix: '//aims.fao.org/aos/agrovoc/', uri: 'http://aims.fao.org/aos/agrovoc', label: 'AGROVOC' },
  { prefix: '//lod.nal.usda.gov/nalt/', uri: 'https://lod.nal.usda.gov/nalt', label: 'USDA NALT' },
  { prefix: '//opendata.inrae.fr/thesaurusINRAE/', uri: 'http://opendata.inrae.fr/thesaurusINRAE/thesaurusINRAE', label: 'INRAE Thesaurus' },
  { prefix: '//www.eionet.europa.eu/gemet/concept/', uri: 'http://www.eionet.europa.eu/gemet/gemetThesaurus', label: 'GEMET' },
  { prefix: '//soilwise-he.github.io/soil-health#', uri: 'https://soilwise-he.github.io/soil-health', label: 'Soil Health Knowledge Graph' },
  { prefix: '//imash.leeds.ac.uk/ontologies/atu/SoilPhysics.owl#', uri: 'http://imash.leeds.ac.uk/ontologies/atu/SoilPhysics.owl', label: 'Soil Property and Process Ontology' },
  { prefix: '//data.geoscience.earth/ncl/ISO11074v2025/', uri: 'https://data.geoscience.earth/ncl/ISO11074v2025', label: 'ISO 11074:2025' },
  ...['codelists', 'procedure', 'layerhorizon', 'siteplot', 'profile', 'common', 'surface'].map(module => ({
    prefix: `//w3id.org/glosis/model/${module}/`, uri: `http://w3id.org/glosis/model/${module}`, label: `GLOSIS ${module}`,
  })),
]

export function mappingSources(value, model) {
  if (value.kind !== 'resource' || !safeExternalUrl(value.uri)) return []
  for (const predicate of [NS.skos + 'inScheme', NS.rdfs + 'isDefinedBy']) {
    const declared = model.objects(value.uri, predicate).filter(term => term.termType === 'NamedNode' && safeExternalUrl(term.value))
    if (declared.length) return [...new Map(declared.map(term => [term.value, { uri: term.value, label: model.describe(term).label }])).values()]
  }
  const namespace = value.uri.replace(/^https?:/, '')
  const source = sources.find(candidate => namespace.startsWith(candidate.prefix))
  return source ? [{ uri: source.uri, label: source.label }] : []
}
