# SoilVoc jskos-vue Prototype

A local, static vocabulary viewer using Vue 3 and jskos-vue. It reads the complete
`../skosmos/SoilVoc_skosmos.ttl` directly in the browser. There is no triplestore,
SPARQL server, external vocabulary API, or change to either Skosmos deployment.

## Run Locally

Requires Node.js 22.12+ (or 20.19+) and npm.

```powershell
cd jskos-viewer
npm ci
npm run dev
```

Open <http://127.0.0.1:5174/>. For the production build:

```powershell
npm test
npm run build
npm run preview
```

Open <http://127.0.0.1:4174/>. Keep the server running while using the viewer;
opening `dist/index.html` with `file://` will not load its RDF file correctly.
These commands copy the source into the ignored `public/data/` directory without
changing it. Restart development or rebuild after updating the original Turtle.
The About page reports the source SHA-256 checksum.

Dependency versions and their transitive dependencies are locked. `.npmrc`
disables dependency lifecycle scripts: jskos-tools distributes its compiled
files, but its POSIX-only postinstall check fails on Windows. No build or startup
script from this project is disabled by that setting.

## Implemented Features

- Complete hierarchy combining direct SKOS broader/narrower, SOSA
  hasProcedure/isProcedureFor, and the existing display-parent projection.
- Independent expansion per full tree path, preserving concepts with multiple
  parents. Direct links reveal a complete path, including nested procedures.
  A hierarchy-path chooser exposes every root-to-concept path without replacing
  the current branch until another path is selected.
- Procedure badges from explicit RDF types; labels from the bundled ontology.
- A-Z browsing, substring search across preferred/alternative/hidden labels and
  notations, internal `*` wildcards, autocomplete with highlighted matching
  synonyms, type filters, and URL-backed paginated results.
- Concept pages with each blank-node definition paired with its own sources.
- Semantic relationships, mappings, labels, notes, arbitrary RDF properties,
  nested blank nodes, and an ontology browser for declared classes/properties.
- Readable advanced type labels, preferred-label and URI copying, explanatory
  property tooltips, browser back/forward with results-page/scroll restoration,
  native modifier-click links, shareable query-string links, and a raw Turtle view.
- Concept or full-vocabulary downloads as Turtle, JSON-LD and RDF/XML. Concept
  downloads include outgoing blank-node closure, not all linked concepts.
- Vocabulary and preferred/alternative/hidden-label statistics, source checksum,
  workflow image, and mobile navigation. Label counts count RDF label statements
  on concepts, not distinct strings.

The navigation projection never rewrites the underlying RDF. Technical
transitive-closure and display-parent predicates are hidden from ordinary detail
rows but remain in the RDF view and downloads. Existing semantic relationships
remain distinct from procedure-based sidebar edges.

## Prototype Boundaries

This is a SoilVoc prototype, not a drop-in Skosmos replacement or a generic
plugin framework. jskos-vue supplies `ItemName`, `ItemList` and `ItemDetails`;
the RDF adapter, hierarchy, sourced definitions, search and additional property
rows are local Vue components. The stock jskos-vue tree is not used because
expansion must distinguish occurrences of the same URI under different parents.

The source currently has English labels, 1,464 concepts, 249 procedures,
192 observable properties and 1,110 definitions. It declares advanced
agrontology relationships but currently has no concept assertions using them;
synthetic tests cover their generic display data. No such assertions are
invented by this viewer. There are no SKOS collections or dated concept changes
in this snapshot, so Groups/New views are not provided. Language switching,
feedback/email, editing, REST compatibility and a public SPARQL endpoint are not
part of this prototype.

All RDF is downloaded and indexed in memory on initial load. Later navigation
and search are local. This is appropriate for this snapshot but not yet a
benchmark or architecture decision for very large vocabularies.

## Structure

- `src/vocabulary.js`: RDF parsing, labels, navigation, search and exports.
- `src/components/HierarchyNode.vue`: recursive, occurrence-keyed navigation.
- `src/components/TermValue.vue`: generic RDF term and blank-node display.
- `src/App.vue`: routes, browsing and details using jskos-vue components.
- `scripts/prepare.mjs`: copy the source/image and calculate its checksum.
- `test/vocabulary.test.js`: source-wide data and regression tests.
- `test/navigation.test.js`: URL state, branch links and native-click regression tests.

No deployment is required or configured. Existing `api/`, Skosmos files and the
primary checkout are left unchanged.
