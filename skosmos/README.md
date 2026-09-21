# Local Skosmos Deployment for SoilVoc

This folder contains a Docker Compose deployment for browsing SoilVoc in Skosmos. By default, it runs the complete stack locally with Apache Jena Fuseki as the triplestore.

Default stack:

- `skosmos`: official AMD64 Skosmos v3.2 image from `quay.io/natlibfi/skosmos`
- `fuseki`: Apache Jena Fuseki with Jena Text indexing and its bundled browser query UI
- `fuseki-cache`: Varnish cache in front of Fuseki
- `plugins/soilvoc-definition-source`: a SoilVoc-only Skosmos plugin that displays definition text with its source and enriches the hierarchy sidebar with semantic SOSA procedure children
- `plugins/soilvoc-contains-search`: searches anywhere within labels in both autocomplete and submitted searches, using the native Skosmos search components

The local Skosmos instance can also use an existing Virtuoso endpoint through `.env.virtuoso.example` and `config/skosmos-config.ttl`.

## Prerequisites

- Docker Desktop (Windows/macOS), or Docker Engine with the Docker Compose plugin (Linux), must be running and accessible from your shell.
- Internet access is required for the first run to pull the official Skosmos image and build the Fuseki image.
- The official Skosmos image is AMD64. On ARM64 machines, select a compatible image with `SKOSMOS_IMAGE`.
- The optional Virtuoso backend requires access to its endpoint and an updated graph at `https://w3id.org/eusoilvoc`.

## Generate Skosmos Data

`../SoilVoc.ttl` remains the canonical vocabulary. The generator uses `../SoilVoc_augmented.ttl` by default and embeds `soilvoc_ontology.ttl` in the Skosmos display copy. After updating the augmented vocabulary, regenerate this display copy from the `skosmos/` directory before reloading Fuseki:

```powershell
python .\generate_skosmos_ttl.py
```

This writes `SoilVoc_skosmos.ttl`. The generated copy preserves source definition blank-node `rdf:value` text, rewrites legacy `schema:text` values if present, keeps SKOS and SOSA links semantic, adds display-only `eusoilvoc:skosmosHierarchyParent` triples for Skosmos sidebar traversal, and embeds `soilvoc_ontology.ttl` so property/class labels are available from the same RDF file. This lets procedures appear in the sidebar without becoming false SKOS narrower concepts. The input files are not changed by this script. Use `--source` to select another vocabulary file.

## Start With Local Fuseki

```powershell
cd path\to\soil-vocabs\skosmos
Copy-Item .env.example .env
docker compose up -d --build
docker compose ps
.\load-soilvoc.ps1
docker compose restart fuseki-cache skosmos
```

`COMPOSE_PROFILES=local-fuseki` in `.env.example` activates Fuseki and Varnish automatically. The build step builds Fuseki locally and pulls the official Skosmos v3.2 image; it does not build Skosmos.

The Fuseki build downloads the official Apache server JAR, extracts its bundled UI, and includes `fuseki/shiro.ini`. It builds entirely from the files in this repository; no existing SoilVoc Docker image or private Compose override is required. The `load-soilvoc.ps1` command loads the included `SoilVoc_skosmos.ttl` into the named graph `https://w3id.org/eusoilvoc`.

Once the stack is running and the data is loaded:

| Service | URL |
| --- | --- |
| Skosmos | [http://localhost:9090/](http://localhost:9090/) |
| Fuseki query UI | [http://localhost:9030/#/dataset/skosmos/query](http://localhost:9030/#/dataset/skosmos/query) |
| SPARQL endpoint | `http://localhost:9030/skosmos/sparql` |
| Cached SPARQL endpoint | `http://localhost:9031/skosmos/sparql` |

The `/skosmos/sparql` URL is an HTTP query endpoint. Use the query UI URL above to open the editor. For example, run this query to list ten SoilVoc concepts:

```sparql
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

SELECT ?concept ?label
WHERE {
  GRAPH <https://w3id.org/eusoilvoc> {
    ?concept a skos:Concept ;
             skos:prefLabel ?label .
    FILTER (lang(?label) = "en")
  }
}
ORDER BY ?label
LIMIT 10
```

Fuseki and Varnish bind their host ports to `127.0.0.1` by default. The query UI and Skosmos share the same database and data volume. The Shiro configuration permits the read-only statistics requests needed by the query page; administrative `/$/` operations such as dataset creation and deletion remain restricted to requests from inside the Fuseki container. Dataset query, update, upload, and Graph Store endpoints keep their existing behavior.

For an existing local deployment, enable the UI without reloading the vocabulary:

```powershell
docker compose up -d --build --no-deps --timeout 30 fuseki fuseki-cache
```

Existing `.env` files should use `FUSEKI_PORT=127.0.0.1:9030` and `CACHE_PORT=127.0.0.1:9031` to keep the same host bindings as `.env.example`.

## Local Smoke Tests

Check container status:

```powershell
docker compose ps
```

Check that the local graph is loaded:

```powershell
Invoke-RestMethod `
  -Method Post `
  -ContentType "application/sparql-query" `
  -Headers @{ Accept = "application/sparql-results+json" } `
  -Body "SELECT (COUNT(*) AS ?triples) WHERE { GRAPH <https://w3id.org/eusoilvoc> { ?s ?p ?o } }" `
  -Uri "http://localhost:9030/skosmos/query"
```

Check a known concept and the custom hierarchy projection:

```powershell
Invoke-RestMethod `
  -Method Post `
  -ContentType "application/sparql-query" `
  -Headers @{ Accept = "application/sparql-results+json" } `
  -Body "PREFIX skos: <http://www.w3.org/2004/02/skos/core#> SELECT ?label WHERE { GRAPH <https://w3id.org/eusoilvoc> { <https://w3id.org/eusoilvoc#SoilpH> skos:prefLabel ?label } } LIMIT 1" `
  -Uri "http://localhost:9030/skosmos/query"

Invoke-RestMethod `
  -Method Post `
  -ContentType "application/sparql-query" `
  -Headers @{ Accept = "application/sparql-results+json" } `
  -Body "PREFIX eusoilvoc: <https://w3id.org/eusoilvoc#> SELECT ?parent WHERE { GRAPH <https://w3id.org/eusoilvoc> { eusoilvoc:pHProcedure-pHCaCl2 eusoilvoc:skosmosHierarchyParent ?parent } } LIMIT 1" `
  -Uri "http://localhost:9030/skosmos/query"
```

Check Skosmos search through the local UI service:

```powershell
Invoke-RestMethod `
  -Uri "http://localhost:9090/rest/v1/soilvoc/search?query=soil%20porosity&lang=en"
```

Then open `http://localhost:9090/soilvoc/en/` and search for `soil porosity`. Open a concept with a sourced definition such as `MineralConcVolume` and confirm the Definition row includes a Source line. Open `BaseSaturation` to confirm `Has procedure` is shown on the concept page and procedure children are available through the hierarchy navigation.

## Search Matching

The contains-search plugin converts `Hydraulic conductivity` (or `Hydraulic conductivity*`) into `*Hydraulic conductivity*`. Autocomplete and the results page then include soil, saturated, and unsaturated hydraulic conductivity. Existing boundary wildcards are not duplicated; internal wildcards are retained. Empty input does not trigger a search.

The same behavior applies to the global search and vocabulary search. Language/vocabulary filters and the native autocomplete delay are preserved. Bookmarked search pages with an unwrapped `q` parameter are normalized once in the browser. Direct REST API callers retain native Skosmos semantics and must supply their own wildcards.

Autocomplete uses the readable SOSA type labels `Observable Property` and `Procedure` when Skosmos omits them from its type dictionary. Native labels and translations take precedence over these English fallbacks.

This is a JavaScript plugin for the official Skosmos 3.2 image; it does not change the RDF data or require rebuilding the Fuseki index. After adding the plugin mount to an existing installation, recreate only Skosmos:

```powershell
docker compose up -d --no-deps skosmos
```

Reload the browser afterward. To disable the plugin, remove `soilvoc-contains-search` from both plugin lists in the selected Skosmos configuration. Its query matching is backend-independent; the same plugin is enabled in the optional Virtuoso configuration.

From the repository root, run its regression tests with:

```powershell
node --test skosmos/plugins/soilvoc-contains-search/contains-search.test.mjs
```

Set `SKOSMOS_TEST_URL=http://localhost:9090/` to also run compatibility tests against the native search JavaScript in the running image. These tests check both search components and should be rerun when upgrading Skosmos; the plugin relies on their synchronous URL construction.

## Optional Virtuoso Backend

To run Skosmos locally against the existing Virtuoso endpoint at `https://sparql.soilwise.wetransform.eu/sparql/`, use the alternative configuration:

```powershell
docker compose --profile local-fuseki down
Copy-Item .env.virtuoso.example .env -Force
docker compose up -d
```

No local RDF load is needed in this mode. To return to local Fuseki, copy `.env.example` back to `.env`, start the stack, and run `load-soilvoc.ps1` again.

## Local Fuseki Maintenance

The default `.env.example` uses `config/skosmos-config.local-fuseki.ttl`, starts Fuseki and Varnish through the `local-fuseki` profile, and loads `SoilVoc_skosmos.ttl` into the local graph.

```powershell
cd path\to\soil-vocabs\skosmos
docker compose up -d --build
.\load-soilvoc.ps1
```

If your PowerShell execution policy blocks local scripts, run:

```powershell
powershell -ExecutionPolicy Bypass -File .\load-soilvoc.ps1
```

If the stack was already running before a reload, restart the cache and frontend so old responses do not mask the updated graph:

```powershell
docker compose restart fuseki-cache skosmos
```

Equivalent manual load command:

```powershell
Invoke-WebRequest `
  -Method Put `
  -ContentType "text/turtle" `
  -InFile .\SoilVoc_skosmos.ttl `
  -Uri "http://localhost:9030/skosmos/data?graph=https%3A%2F%2Fw3id.org%2Feusoilvoc" `
  -UseBasicParsing
```

## Stop

```powershell
docker compose down
```

## Clean Local Fuseki Reset

This removes the local Fuseki data volume and reloads the Skosmos copy from scratch:

```powershell
docker compose down -v
python .\generate_skosmos_ttl.py
docker compose up -d --build
.\load-soilvoc.ps1
```

## Notes

- Optional Virtuoso endpoint: `https://sparql.soilwise.wetransform.eu/sparql/`
- Skosmos vocabulary graph URI: `https://w3id.org/eusoilvoc`
- SoilVoc concept URI space: `https://w3id.org/eusoilvoc#`
- Skosmos UI port: `9090`
- Local Fuseki host port: `9030`
- Local Varnish host port: `9031`
- Local Fuseki is the default backend and uses Skosmos' Jena Text dialect. The optional remote Virtuoso configuration uses the Generic SPARQL dialect.
- The feedback plugin posts to the same-origin path `/api/feedback`; the local Compose stack does not include email delivery.
- `SoilVoc_skosmos.ttl` is a generated Skosmos display copy; regenerate it from `../SoilVoc_augmented.ttl` and `soilvoc_ontology.ttl`.
- Override ports, `SKOSMOS_IMAGE`, or `SKOSMOS_CONFIG` by copying an environment example to `.env` and editing the values.
- Skosmos Docker notes: `https://github.com/NatLibFi/Skosmos/wiki/Install-Skosmos-with-Fuseki-in-Docker`
- Skosmos configuration reference: `https://github.com/NatLibFi/Skosmos/wiki/Configuration`
