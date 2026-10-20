# SoilVoc Viewer

A static vocabulary viewer using Vue 3 and selected jskos-vue components. It reads the complete
`data/SoilVoc.ttl` directly in the browser. There is no triplestore,
SPARQL server, external vocabulary API, or dependency on Skosmos.

The viewer is published at <https://soilwise-he.github.io/soil-vocabs/> and
<https://w3id.org/eusoilvoc>. Existing canonical concept links such as
<https://w3id.org/eusoilvoc#CulturalServices> open their concept details and
hierarchy path. Query-string links remain supported too.

## Run Locally

Use Node.js 24 and npm to match the GitHub Actions build. Python is needed only
when regenerating the RDF snapshot, not when building or running the viewer.
Run these commands from the repository root:

```powershell
cd viewer
npm ci
npm run dev
```

Open <http://127.0.0.1:5174/>. For the production build:

```powershell
npm run build
npm run preview
```

Open <http://127.0.0.1:4174/>. Keep the server running while using the viewer;
opening `dist/index.html` with `file://` will not load its RDF file correctly.
`npm run dev` and `npm run build` copy the committed snapshot into the ignored
`public/data/` directory without changing it. `npm run preview` serves the existing
build and does not refresh its data. Restart development or rebuild after updating
the original Turtle. Do not edit `public/` copies or `dist/` as source files.
The About page reports the source SHA-256 checksum.

Dependency versions and their transitive dependencies are locked. `.npmrc`
disables dependency lifecycle scripts: jskos-tools distributes its compiled
files, but its POSIX-only postinstall check fails on Windows. No build or startup
script from this project is disabled by that setting.

The optional regression tests in `test/` are local-only and Git-ignored. They
are not included in fresh clones or Docker build contexts. On a machine that
has these files, run `npm test` to check the viewer against the current RDF.

## Update Viewer Data

The files have separate roles; paths below are relative to the repository root:

| File | Role |
|------|------|
| `SoilVoc.ttl` | Canonical vocabulary, W3ID RDF download, and REST API input |
| `SoilVoc_augmented.ttl` | Input to the viewer snapshot generator |
| `viewer/data/ontology.ttl` | Display ontology labels and class/property declarations embedded by the generator |
| `viewer/data/SoilVoc.ttl` | Committed display snapshot read by the browser |
| `viewer/data/workflow.png` | Shared workflow image for the viewer and repository documentation |

After updating `SoilVoc_augmented.ttl`, regenerate the display snapshot from
the repository root. This step requires Python and RDFLib; install RDFLib first
with `python -m pip install rdflib` if it is not already available:

```powershell
python viewer/scripts/generate_data.py
```

The generator embeds `viewer/data/ontology.ttl`, preserves sourced definitions,
and retains the existing display hierarchy projection and SKOS closure. It does
not change the input vocabulary or require a Skosmos installation. The historic
`eusoilvoc:skosmosHierarchyParent` predicate remains for RDF compatibility only.
Use `--source`, `--ontology`, or `--output` to select different files.

RDFLib is also listed in the root `requirements.txt`. The generator does not
run the curation notebook, regenerate the canonical vocabulary or CSV, or
reload any reference deployment.

Review and commit the updated snapshot, along with any intended ontology or
image changes. A push to `main` publishes the new viewer data. Changing only
`SoilVoc_augmented.ttl` can trigger a build but does not regenerate the browser
snapshot. Never edit generated `public/data/` copies instead of the committed
input.

The ignored `skosmos/` folder is only a local reference deployment; changes there
no longer update the public viewer. It is absent from fresh clones, as are the
local-only `cloudflare/` bundle and `viewer/test/` files.

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
- Bottom-of-page mapping sections pairing complete concept URIs with source
  vocabulary URIs, using explicit RDF metadata or known-namespace display lookups.
- Semantic relationships, mappings, labels, notes, arbitrary RDF properties,
  nested blank nodes, and an ontology browser for declared classes/properties.
- Readable advanced type labels, preferred-label and URI copying, explanatory
  property tooltips, browser back/forward with results-page/scroll restoration,
  native modifier-click links, shareable query-string links, and a raw Turtle view.
- Concept or full-vocabulary downloads as Turtle, JSON-LD and RDF/XML. Concept
  downloads include outgoing blank-node closure, not all linked concepts.
  Concept Turtle uses only necessary prefixes and readable inline blank nodes,
  preserving shared/cyclic nodes where identifiers are needed.
- Vocabulary and preferred/alternative/hidden-label statistics, source checksum,
  workflow image, and mobile navigation. Label counts count RDF label statements
  on concepts, not distinct strings.

The navigation projection never rewrites the underlying RDF. Technical
transitive-closure and display-parent predicates are hidden from ordinary detail
rows but remain in the RDF view and downloads. Existing semantic relationships
remain distinct from procedure-based sidebar edges.

## Publishing

`.github/workflows/deploy-pages.yml` builds this directory on relevant pull
requests without deploying them. Relevant pushes to `main` build and deploy
through GitHub Actions to GitHub Pages, with Vite's base set to `/soil-vocabs/`.
The workflow also supports manual runs from GitHub Actions.

The build also copies the unchanged canonical `SoilVoc.ttl` to the published
root, preserving W3ID's Turtle content negotiation. `SoilVoc_augmented.ttl`,
`SoilVoc_concepts.csv`, `CITATION.cff`, and `LICENSE` remain available there.
The viewer itself reads the separate display copy at `data/SoilVoc.ttl`; this
is not the canonical `SoilVoc.ttl` served at the site root.
Push an updated `viewer/data/SoilVoc.ttl` to `main` (or merge a pull request)
to rebuild and publish changed viewer data automatically. No manual HTML or JSON
regeneration is needed. This workflow does not regenerate the source Turtle.
The publishing workflow does not run the local regression suite or validate
the vocabulary's RDF and hierarchy. Run the local tests before pushing when
those checks are needed.

The previous HTML/JSON viewer is no longer part of the current source tree or
publishing workflow. The API Docker image builds the same Vue viewer with
relative asset paths for root or reverse-proxy hosting. That image is separate
from Pages hosting and does not include Skosmos or Fuseki.

## Boundaries

This is a SoilVoc-focused viewer, not a drop-in Skosmos replacement or a generic
plugin framework. jskos-vue supplies `ItemName`, `ItemList` and `ItemDetails`;
the RDF adapter, hierarchy, sourced definitions, search and additional property
rows are local Vue components. The stock jskos-vue tree is not used because
expansion must distinguish occurrences of the same URI under different parents.

The About page calculates current concept, procedure, property, definition and
label counts from the loaded RDF. The display ontology declares advanced
relationships, but the viewer shows them only when asserted in the source; it
does not invent relationships. Local synthetic tests cover generic display data.
Language switching, dedicated collection/change-history views, feedback/email,
editing, REST compatibility and a public SPARQL endpoint are not part of this
viewer. The optional REST API is documented separately in `api/README.md`.

All RDF is downloaded and indexed in memory on initial load. Later navigation
and search are local. This is appropriate for this snapshot but not yet a
benchmark or architecture decision for very large vocabularies.

## Structure

- `src/vocabulary.js`: RDF parsing, labels, navigation, search and exports.
- `src/components/HierarchyNode.vue`: recursive, occurrence-keyed navigation.
- `src/components/TermValue.vue`: generic RDF term and blank-node display.
- `src/App.vue`: routes, browsing and details using jskos-vue components.
- `scripts/prepare.mjs`: copy the source/image and calculate its checksum.
- `scripts/generate_data.py`: regenerate the display snapshot from the augmented vocabulary.
- `data/`: committed viewer snapshot, display ontology, and workflow image.
- `test/` (optional, untracked): local source-consistency and viewer regression tests.

The viewer does not change RDF source files or the Skosmos deployment. The
existing REST API remains separate from browser-side vocabulary loading.
