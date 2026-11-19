// GitHub Pages does not compress Turtle, so the build also publishes a gzip copy
// (about 1/8 of the size). The uncompressed snapshot remains the fallback.
export async function loadVocabularyText(base, fetcher = fetch) {
  if (typeof DecompressionStream === 'function') {
    try {
      const response = await fetcher(base + 'data/SoilVoc.ttl.gz')
      if (response.ok) {
        const bytes = new Uint8Array(await response.arrayBuffer())
        if (bytes[0] === 0x1f && bytes[1] === 0x8b) {
          const stream = new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'))
          return await new Response(stream).text()
        }
        // Servers that send the copy with Content-Encoding: gzip (such as `vite preview`)
        // let the browser decode it already. An HTML fallback page is not vocabulary data.
        if (!/html/i.test(response.headers.get('content-type') || '')) return new TextDecoder().decode(bytes)
      }
    } catch { /* Fall back to the uncompressed snapshot. */ }
  }
  const response = await fetcher(base + 'data/SoilVoc.ttl')
  if (!response.ok) throw new Error(`Vocabulary file could not be loaded (HTTP ${response.status}).`)
  return response.text()
}
