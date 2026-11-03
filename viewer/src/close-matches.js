// This display-only cache never enters the vocabulary's RDF store.
export function preferredLanguage(values, language = 'en') {
  const exact = values.filter(value => value.language.toLowerCase() === language)
  if (exact.length) return exact
  const preferred = values.filter(value => value.language.toLowerCase().split('-')[0] === language)
  if (preferred.length) return preferred
  const untagged = values.filter(value => !value.language)
  return untagged.length ? untagged : values
}

function isLiteral(value) {
  return value && typeof value.text === 'string' && typeof value.language === 'string'
}

export function parseCloseMatches(data) {
  if (data?.schemaVersion !== 1 || !data.records || Array.isArray(data.records) || typeof data.records !== 'object') {
    throw new Error('Invalid close-match preview data')
  }
  const records = new Map()
  for (const [uri, record] of Object.entries(data.records)) {
    if (!Array.isArray(record?.prefLabels) || !record.prefLabels.every(isLiteral) ||
        !Array.isArray(record.definitions) || !record.definitions.every(value => isLiteral(value) &&
          Array.isArray(value.sources) && value.sources.every(source => source &&
            (typeof source.uri === 'string' || isLiteral(source))))) {
      throw new Error(`Invalid close-match preview: ${uri}`)
    }
    records.set(uri, { ...record, prefLabels: preferredLanguage(record.prefLabels), definitions: preferredLanguage(record.definitions) })
  }
  return records
}

export function createCloseMatchLoader(url, fetcher = fetch) {
  let pending
  return () => {
    if (!pending) {
      pending = Promise.resolve().then(() => fetcher(url)).then(async response => {
        if (!response.ok) throw new Error(`Preview request failed (HTTP ${response.status})`)
        return parseCloseMatches(await response.json())
      }).catch(error => { pending = undefined; throw error })
    }
    return pending
  }
}
