# SoilVoc Viewer

A static vocabulary viewer using Vue 3 and selected jskos-vue components. It reads the complete
`data/SoilVoc.ttl` directly in the browser. There is no triplestore,
SPARQL server, external vocabulary API, or dependency on Skosmos. Its pages follow
the layout of Skosmos 3: a vocabulary information page, a sidebar with hierarchy and
A-Z views, and concept pages as one property table.

The viewer is published at <https://soilwise-he.github.io/soil-vocabs/> and
<https://w3id.org/eusoilvoc>. Existing canonical concept links such as
<https://w3id.org/eusoilvoc#CulturalServices> open their concept details and
hierarchy path. Each concept has a short address named after its local name, such
as <https://soilwise-he.github.io/soil-vocabs/CulturalServices>. Older `?uri=`
links (with a local name or a complete URI) and `#` fragments still work and switch
to that address.

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
`public/data/` directory without changing it, and write an identical gzip copy
(`SoilVoc.ttl.gz`) beside it. `npm run preview` serves the existing
build and does not refresh its data. Restart development or rebuild after updating
the original Turtle. Do not edit `public/` copies or `dist/` as source files.
The About page reports the source SHA-256 checksum.

Dependency versions and their transitive dependencies are locked. `.npmrc`
disables dependency lifecycle scripts: jskos-tools distributes its compiled
files, but its POSIX-only postinstall check fails on Windows. No build or startup
script from this project is disabled by that setting.

The interface uses self-hosted Public Sans and EB Garamond fonts from
`assets/fonts/`. Their SIL Open Font Licenses are included in the build under
`font-licenses/`; no external font service is needed. Property layouts adapt to
the reading pane's width. Concept relationship lists are sorted by label for
display, without changing RDF statement order or ordered list values.

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
| `viewer/data/close-matches.json` | Separate display cache of external mapping targets, never merged into SoilVoc RDF |

After updating `SoilVoc_augmented.ttl`, regenerate the display snapshot from
the repository root. This step requires Python and RDFLib; install RDFLib first
with `python -m pip install rdflib` if it is not already available:

```powershell
python viewer/scripts/generate_data.py
```

To regenerate the viewer RDF **and** refresh its separate mapping previews
in one command, use:

```powershell
python viewer/scripts/generate_data.py --with-close-matches
```

This option requires network access and prepares both files before replacing
either. If RDF parsing or external retrieval fails, both previous outputs remain
unchanged. The cache checksum refers to the newly generated RDF. With `--output`,
`close-matches.json` is written beside that custom RDF output.
Without the flag, generation remains offline and leaves the preview cache alone.
Refresh previews when mapping targets change or when you want newer source
descriptions; changing only SoilVoc's own labels or definitions does not require it.

The generator embeds `viewer/data/ontology.ttl`, preserves sourced definitions,
and retains the existing display hierarchy projection and SKOS closure. It does
not change the input vocabulary or require a Skosmos installation. The historic
`eusoilvoc:skosmosHierarchyParent` predicate remains for RDF compatibility only.
Use `--source`, `--ontology`, or `--output` to select different files.

RDFLib is also listed in the root `requirements.txt`. The generator does not
run the curation notebook, regenerate the canonical vocabulary or CSV, or
reload any reference deployment.

Review and commit the updated snapshot and refreshed `close-matches.json` (when
using the combined command), along with any intended ontology or
image changes. A push to `main` publishes the new viewer data. Changing only
`SoilVoc_augmented.ttl` can trigger a build but does not regenerate the browser
snapshot. Never edit generated `public/data/` copies instead of the committed
input.

The ignored `skosmos/` folder is only a local reference deployment; changes there
no longer update the public viewer. It is absent from fresh clones, as are the
local-only `cloudflare/` bundle and `viewer/test/` files.

### Mapping Previews

As in Skosmos, each mapping row shows the external concept's original label and the
name of its vocabulary; the complete URI is the link target and appears on hover.
A target without a cached label is shown by its URI, for example the Soil Property
and Process Ontology classes, which have no labels in their source. Close matches
also offer expandable source definitions, in English only. These describe the
**external concepts**, not the SoilVoc concept. They never enter SoilVoc's
definitions, search, hierarchy, statistics, or RDF exports.

`data/close-matches.json` is a committed, display-only cache keyed by the exact
external URI. Despite its name, it covers every SKOS mapping target: close-match
records include definitions, while exact-match and other mapping targets are
label-only records without a definitions list. The browser lazily loads this
same-site file once when a concept has mappings; it does not contact external APIs.
A failed load leaves the mapping links usable and offers Retry. An uncached new
close match is distinguished from a retrieved source record with no English definition.

The combined command above updates both files after vocabulary edits. To refresh
only the cache against the existing viewer RDF, without regenerating that RDF:

```powershell
python viewer/scripts/generate_close_matches.py
npm --prefix viewer run build
```

The refresh reads `viewer/data/SoilVoc.ttl` and queries AGROVOC SPARQL, NALT and
INRAE Skosmos APIs, ISO 11074 RDF records, and the latest GEMET submission in
AgroPortal SPARQL. SHKG, BENCHMARKS and the Soil Property and Process Ontology use
local source snapshots: `ontovocabs/shkg/soil_health_KG.ttl`,
`ontovocabs/shb/soil_health_benchmarks.ttl` and `ontovocabs/spp/soil_property_process.ttl`.
For matching, the notebook reads concept URIs and preferred/alternative labels from
`ontovocabs/shb/soil_health_benchmarks.csv`, just like the other sources.
Its exact-match enrichment cell adds English definitions to `SoilVoc_augmented.ttl`;
close matches only supply viewer previews. Both definition paths read the Turtle file,
including standard SKOS definitions
and the glossary's policy and scientific definitions, citing the BENCHMARKS concept URI.
The mapped legacy GLOSIS URIs (codelists, common, layer/horizon, procedure, profile,
site/plot and surface modules) use the official historical revision pinned in the
script; they are not substituted with GLOSIS v2 identifiers. The pinned layer/horizon
file is not valid Turtle (an undeclared `cm:` prefix), so that module is read from
`ontovocabs/glosis/glosis_ori/glosis_layer_horizon.ttl`, which differs from it only in
unit restrictions. Labels come from
`skos:prefLabel`, or from `rdfs:label` where a source labels only that way (some GLOSIS
classes and properties). Requests are bounded and retried; a retrieval/parsing failure
or unsupported source for a close-match target stops the refresh without replacing the
previous cache. Labels for other mapping targets are best effort: missing or unlabelled
records and unsupported sources are reported as `Shown as URIs` and left out of the cache.
Only the small extracted records are saved, not complete external vocabularies.

The cache retains literal text, language tags, definition-specific citations, and
retrieval provenance (including GEMET submission and local snapshot checksum), but
only for what the English interface shows. Labels are English, otherwise untagged,
otherwise in their original language (shown with its language tag, never translated).
Definitions are English, otherwise untagged text, which is marked as such; definitions
in other languages are neither cached nor shown, and the viewer applies the same rule
to older caches. Missing definitions are not invented. Concept-level SHKG
bibliographies are not attributed to individual definitions without evidence.

Regeneration is explicit, not part of ordinary builds or GitHub Actions. Review
and commit the JSON alongside intended viewer changes to publish previews. The
cache is optional at runtime: later RDF updates still work before refreshing it,
but newly mapped targets show their URIs, and new close matches show that a preview
has not yet been cached.

## Implemented Features

- Complete hierarchy combining direct SKOS broader/narrower, SOSA
  hasProcedure/isProcedureFor, and the existing display-parent projection.
- Independent expansion per full tree path, preserving concepts with multiple
  parents. Direct links reveal a complete path, including nested procedures.
  A hierarchy-path chooser exposes every root-to-concept path without replacing
  the current branch until another path is selected.
- Procedure badges from explicit RDF types; labels from the bundled ontology.
- A-Z browsing of preferred labels with a fixed letter bar; the hierarchy and A-Z
  tabs keep their own scroll positions, and the tree reveals a concept opened from
  A-Z when its tab is shown again.
- Substring search across preferred/alternative/hidden labels and
  notations, internal `*` wildcards, autocomplete with highlighted matching
  synonyms, type filters, and URL-backed paginated results.
- Concept pages laid out as one label/value table, as in Skosmos: preferred label,
  type, definitions, relationships, labels and notes, URI and download links,
  followed by the mapping rows. A breadcrumb ends with the current concept, and
  lists of more than 12 values start with 10 and a "Show all" button.
- Each blank-node definition is paired with its own sources.
  Embedded HTML in source definitions (such as ISO 11074 term-reference markup)
  is displayed as readable plain text, preserving reference wording and numbers.
  This also applies to search snippets and close-match previews. Source markup
  is never inserted into the page; original literals, citations, and RDF exports
  remain unchanged.
- Mapping rows showing each matched concept's original label, or its URI when no
  label is cached, with the name of its vocabulary from explicit RDF metadata or
  known-namespace display lookups.
- Expandable English source definitions for close matches from a separate static
  cache, clearly distinguished from SoilVoc definitions.
- Semantic relationships, mappings, labels, notes, arbitrary RDF properties,
  nested blank nodes, and an ontology browser limited to declared classes,
  properties and units actually used in the loaded vocabulary. Usage includes concepts,
  schemes, and their linked metadata, not standalone ontology descriptions.
  Unused declarations remain available in the RDF and downloads.
- Ontology entries retain local detail pages and offer direct links to their
  original URIs. Defined-by references open their source resources externally.
- Readable advanced type labels, preferred-label and URI copying, explanatory
  property tooltips, browser back/forward with results-page/scroll restoration,
  native modifier-click links, and a raw Turtle view. Concept addresses are short
  (`/soil-vocabs/Soil`); a branch other than the concept's default one adds its
  ancestors, such as `?path=Soil/SoilProperties`. Search, About and Ontology use
  query parameters on the home page, as do resources outside SoilVoc (`?uri=`).
- Concept or full-vocabulary downloads as Turtle, JSON-LD and RDF/XML, offered as
  direct links. Concept downloads include outgoing blank-node closure, not all linked concepts.
  Concept Turtle uses only necessary prefixes and readable inline blank nodes,
  preserving shared/cyclic nodes where identifiers are needed.
- A vocabulary information page (the home page) with the concept scheme's own
  metadata, the vocabulary URI, label languages, downloads (including the canonical
  `SoilVoc.ttl` and `SoilVoc_concepts.csv`), resource and term counts, and top
  concepts. Label counts count RDF label statements on concepts, not distinct strings.
- An About page with the source file, statement count, checksum, ontology summary
  and workflow image; mobile navigation; and a header Feedback link to GitHub issues.
- The page frame appears while the vocabulary loads. The browser reads a gzip copy
  of the snapshot (about one eighth of its size), because GitHub Pages serves Turtle
  uncompressed, and falls back to the plain file.

The navigation projection never rewrites the underlying RDF. Technical
transitive-closure and display-parent predicates are hidden from ordinary detail
rows but remain in the RDF view and downloads. Existing semantic relationships
remain distinct from procedure-based sidebar edges.

## Publishing

### Concept Comments

Individual SKOS concept pages include a lazy-loaded [giscus](https://giscus.app/)
comments section. Home, search, About, ontology lists, and ontology resource pages
do not load it. Comments are stored in GitHub Discussions, not in the RDF or on
the hosting server. GitHub sign-in is required to post; reading is public.

The target is `soilwise-he/soil-vocabs`, using its existing `Announcements`
category (giscus recommends an announcement category to restrict discussion
creation to maintainers and the app). Enable Discussions and install the
[giscus GitHub App](https://github.com/apps/giscus) for this repository only.
No access token or deployment secret is needed. Verified public repository and
category IDs are stored in `src/comments.js`; update the category ID there if the
category is deleted and recreated. The widget loads near the comments section
and allows retry after failures. There is no browser-side configuration API call.
Installation can be completed after deploying the viewer, without a rebuild.
Until then, the section reports that comments are not enabled and links to GitHub.

Each discussion is keyed by the full concept URI, using `mapping="specific"`
and strict matching. Labels, hierarchy paths, viewer origins, and query-string
ordering do not create separate threads. Changing a concept URI requires a
discussion migration; changing its label does not. The discussion backlink uses
the canonical concept URI. Before giscus loads, the address is normalized to the
concept's page address, so GitHub sign-in returns to that concept even from
hash-only routes, whose fragments it drops.
The widget is recreated on concept changes, preventing an old thread from staying
visible under a new concept. No discussions are created simply by browsing:
giscus creates one on the first submitted comment or reaction.

Configuration and lifecycle live in `src/comments.js` and
`src/components/ConceptComments.vue`. Comments use third-party requests to
`giscus.app` only near the comments section; a failure never blocks vocabulary
browsing. End-to-end posting must be verified after the app is installed. Do not
create test discussions or comments without explicit authorization.

### GitHub Pages

`.github/workflows/deploy-pages.yml` builds this directory on relevant pull
requests without deploying them. Relevant pushes to `main` build and deploy
through GitHub Actions to GitHub Pages, with Vite's base set to `/soil-vocabs/`.
The workflow also supports manual runs from GitHub Actions.

The build also copies the unchanged canonical `SoilVoc.ttl` to the published
root, preserving W3ID's Turtle content negotiation. `SoilVoc_augmented.ttl`,
`SoilVoc_concepts.csv`, `CITATION.cff`, and `LICENSE` remain available there.
The viewer itself reads the separate display copy at `data/SoilVoc.ttl`; this
is not the canonical `SoilVoc.ttl` served at the site root. The build also publishes
`data/SoilVoc.ttl.gz`, an identical gzip copy that the viewer reads first.

For short concept addresses, the build (`scripts/concept-pages.mjs`, a Vite plugin)
writes an identical copy of the viewer page as `<LocalName>.html` for every concept
in `data/SoilVoc.ttl`. GitHub Pages serves these at `/soil-vocabs/<LocalName>` with
HTTP 200, and the viewer reads the concept from the address. Names that are unsafe
as file names, or `index`, keep `?uri=` links instead. A `404.html` copy opens the
viewer for any other address, which reports an unknown concept itself (HTTP 404).
Servers that do not map `/name` to `name.html`, such as the API image's static
files, reach concept addresses through that `404.html` with HTTP status 404.

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

The vocabulary information page calculates current concept, procedure, property,
definition and label counts from the loaded RDF. It shows the concept scheme's own
metadata (for example `dcterms:title`, `description`, `publisher`, `creator`,
`license` and `modified`) only as stated in the vocabulary; the viewer does not
hard-code it. The display ontology declares advanced
relationships, but the viewer shows them only when asserted in the source; it
does not invent relationships. Local synthetic tests cover generic display data.
Language switching, dedicated collection/change-history views, a feedback form or
email (the Feedback link opens GitHub issues), editing, REST compatibility and a
public SPARQL endpoint are not part of this viewer. The optional REST API is
documented separately in `api/README.md`.

All RDF is downloaded and indexed in memory on initial load. Later navigation
and search are local. This is appropriate for this snapshot but not yet a
benchmark or architecture decision for very large vocabularies.

## Structure

- `src/vocabulary.js`: RDF parsing, labels, navigation, search and exports.
- `src/navigation.js`: URL routes and short concept links.
- `src/load-vocabulary.js`: reads the gzip snapshot, with the plain file as fallback.
- `src/download.js`: concept and vocabulary RDF downloads.
- `src/components/HierarchyNode.vue`: recursive, occurrence-keyed navigation.
- `src/components/TermValue.vue`: generic RDF term and blank-node display.
- `src/components/ValueList.vue`: property values, shortening long lists.
- `src/components/MappingSection.vue`: mapping rows with cached external labels.
- `src/App.vue`: routes, browsing and details using jskos-vue components.
- `scripts/prepare.mjs`: copy the source/image, write its gzip copy and calculate its checksum.
- `scripts/concept-pages.mjs`: write a page per concept and `404.html` for short addresses.
- `scripts/generate_data.py`: regenerate the display snapshot from the augmented vocabulary.
- `scripts/generate_close_matches.py`: refresh the separate mapping preview cache.
- `src/close-matches.js`: isolated preview loader and language selection.
- `data/`: committed viewer snapshot, display ontology, workflow image, and external previews.
- `test/` (optional, untracked): local source-consistency and viewer regression tests.

The viewer does not change RDF source files or the Skosmos deployment. The
existing REST API remains separate from browser-side vocabulary loading.
