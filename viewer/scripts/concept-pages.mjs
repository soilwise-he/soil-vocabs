import { readFile, writeFile } from 'node:fs/promises'
import { join, resolve } from 'node:path'
import { Parser } from 'n3'
import { NS } from '../src/vocabulary.js'
import { isPageName } from '../src/navigation.js'

const TYPE = NS.rdf + 'type', CONCEPT = NS.skos + 'Concept'

// Local names of the SoilVoc concepts that get their own page.
export function conceptPageNames(turtle) {
  const names = new Set()
  for (const { subject, predicate, object } of new Parser({ format: 'text/turtle' }).parse(turtle)) {
    if (predicate.value !== TYPE || object.value !== CONCEPT || !subject.value.startsWith(NS.eusoilvoc)) continue
    const name = subject.value.slice(NS.eusoilvoc.length)
    if (isPageName(name)) names.add(name)
  }
  return [...names].sort()
}

// GitHub Pages serves name.html at /name, so a copy of the viewer page per concept gives
// each one a short address such as /soil-vocabs/Soil. The copies are identical: the viewer
// reads the concept from the address. 404.html opens the viewer for any other address,
// which then reports an unknown concept itself.
export function conceptPages() {
  let root, outDir
  return {
    name: 'soilvoc-concept-pages',
    apply: 'build',
    configResolved(config) {
      root = config.root
      outDir = resolve(config.root, config.build.outDir)
    },
    async closeBundle() {
      const html = await readFile(join(outDir, 'index.html'), 'utf8')
      const names = conceptPageNames(await readFile(join(root, 'data/SoilVoc.ttl'), 'utf8'))
      for (const name of names) await writeFile(join(outDir, `${name}.html`), html)
      await writeFile(join(outDir, '404.html'), html)
      console.log(`Wrote ${names.length} concept pages and 404.html`)
    },
  }
}
