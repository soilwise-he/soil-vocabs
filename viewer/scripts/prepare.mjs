import { copyFile, mkdir, readFile, writeFile } from 'node:fs/promises'
import { createHash } from 'node:crypto'
import { fileURLToPath } from 'node:url'

const source = new URL('../data/SoilVoc.ttl', import.meta.url)
const publicDir = new URL('../public/', import.meta.url)
await mkdir(new URL('data/', publicDir), { recursive: true })
const bytes = await readFile(source)
await copyFile(source, new URL('data/SoilVoc.ttl', publicDir))
await copyFile(new URL('../data/workflow.png', import.meta.url), new URL('workflow.png', publicDir))
await mkdir(new URL('font-licenses/', publicDir), { recursive: true })
for (const file of ['PublicSans-OFL.txt', 'EBGaramond-OFL.txt']) {
  await copyFile(new URL('../assets/fonts/' + file, import.meta.url), new URL('font-licenses/' + file, publicDir))
}
// W3ID's Turtle content negotiation points to the canonical root-level file.
for (const file of ['SoilVoc.ttl', 'SoilVoc_augmented.ttl', 'SoilVoc_concepts.csv', 'CITATION.cff', 'LICENSE']) {
  await copyFile(new URL('../../' + file, import.meta.url), new URL(file, publicDir))
}
await writeFile(new URL('data/manifest.json', publicDir), JSON.stringify({
  source: 'viewer/data/SoilVoc.ttl',
  sha256: createHash('sha256').update(bytes).digest('hex'),
  bytes: bytes.length,
}, null, 2) + '\n')
console.log(`Prepared ${fileURLToPath(source)} (${bytes.length.toLocaleString()} bytes)`)
