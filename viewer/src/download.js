import { localName } from './vocabulary.js'

export const RDF_FORMATS = [
  { format: 'ttl', name: 'Turtle', type: 'text/turtle' },
  { format: 'jsonld', name: 'JSON-LD', type: 'application/ld+json' },
  { format: 'rdf', name: 'RDF/XML', type: 'application/rdf+xml' },
]

// Serializes one resource (or the whole vocabulary without a URI) and saves it as a file.
export async function downloadRdf(model, uri, format) {
  const text = await model.serialize(uri, format)
  const { type } = RDF_FORMATS.find(entry => entry.format === format)
  const url = URL.createObjectURL(new Blob([text], { type: type + ';charset=utf-8' }))
  const link = document.createElement('a')
  link.href = url
  link.download = (uri ? localName(uri) : 'SoilVoc') + '.' + format
  link.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
