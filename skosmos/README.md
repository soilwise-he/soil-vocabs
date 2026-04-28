# Local Skosmos Deployment for SoilVoc

This folder contains a Docker Compose deployment for browsing SoilVoc in Skosmos. By default, Skosmos reads the SoilVoc graph from the online Virtuoso SPARQL endpoint.

Default stack:

- `skosmos`: Skosmos web UI from `quay.io/natlibfi/skosmos`
- `plugins/soilvoc-definition-source`: a SoilVoc-only Skosmos plugin that displays definition text with its source and enriches the hierarchy sidebar with semantic SOSA procedure children

Optional local fallback:

- `fuseki`: Apache Jena Fuseki with Jena Text indexing
- `fuseki-cache`: Varnish cache in front of Fuseki

## Prerequisites

- Docker Desktop must be running and accessible from this shell.
- Internet access is required for the first run to pull the Skosmos image and for runtime access to the Virtuoso endpoint.
- The remote Virtuoso graph must contain the generated Skosmos Turtle file in graph `https://w3id.org/eusoilvoc`.

## Generate Skosmos Data

`../SoilVoc.ttl` remains the canonical source. Generate the Skosmos display copy before uploading it to Virtuoso:

```powershell
python .\generate_skosmos_ttl.py
```

This writes `SoilVoc_skosmos.ttl`. The generated copy preserves canonical definition blank-node `rdf:value` text, rewrites legacy `schema:text` values if present, keeps SKOS and SOSA links semantic, adds display-only `eusoilvoc:skosmosHierarchyParent` triples for Skosmos sidebar traversal, and embeds `soilvoc_ontology.ttl` so property/class labels are available from the same RDF file. This lets procedures appear in the sidebar without becoming false SKOS narrower concepts. The canonical `../SoilVoc.ttl` is not changed by this script.

## Start With Remote Virtuoso

```powershell
cd C:\Users\wang479\Downloads\soil-vocabs\skosmos
Copy-Item .env.example .env
docker compose up -d
```

Skosmos will be available at:

```text
http://localhost:9090/
```

No local RDF load step is needed in this mode. Skosmos queries the remote endpoint directly:

```text
https://sparql.soilwise.wetransform.eu/sparql/
```

## Remote Smoke Tests

Check container status:

```powershell
docker compose ps
```

Check that the remote graph is reachable:

```powershell
Invoke-RestMethod `
  -Method Post `
  -ContentType "application/sparql-query" `
  -Headers @{ Accept = "application/sparql-results+json" } `
  -Body "SELECT (COUNT(*) AS ?triples) WHERE { GRAPH <https://w3id.org/eusoilvoc> { ?s ?p ?o } }" `
  -Uri "https://sparql.soilwise.wetransform.eu/sparql/"
```

Check a known concept and the custom hierarchy projection:

```powershell
Invoke-RestMethod `
  -Method Post `
  -ContentType "application/sparql-query" `
  -Headers @{ Accept = "application/sparql-results+json" } `
  -Body "PREFIX skos: <http://www.w3.org/2004/02/skos/core#> SELECT ?label WHERE { GRAPH <https://w3id.org/eusoilvoc> { <https://w3id.org/eusoilvoc#SoilpH> skos:prefLabel ?label } } LIMIT 1" `
  -Uri "https://sparql.soilwise.wetransform.eu/sparql/"

Invoke-RestMethod `
  -Method Post `
  -ContentType "application/sparql-query" `
  -Headers @{ Accept = "application/sparql-results+json" } `
  -Body "PREFIX eusoilvoc: <https://w3id.org/eusoilvoc#> SELECT ?parent WHERE { GRAPH <https://w3id.org/eusoilvoc> { eusoilvoc:pHProcedure-pHCaCl2 eusoilvoc:skosmosHierarchyParent ?parent } } LIMIT 1" `
  -Uri "https://sparql.soilwise.wetransform.eu/sparql/"
```

Check Skosmos search through the local UI service:

```powershell
Invoke-RestMethod `
  -Uri "http://localhost:9090/rest/v1/soilvoc/search?query=soil%20porosity&lang=en"
```

Then open `http://localhost:9090/soilvoc/en/` and search for `soil porosity`. Open a concept with a sourced definition such as `MineralConcVolume` and confirm the Definition row includes a Source line. Open `BaseSaturation` to confirm `Has procedure` is shown on the concept page and procedure children are available through the hierarchy navigation.

## Optional Local Fuseki Fallback

Use this only when you want an offline/local triplestore. It uses `config/skosmos-config.local-fuseki.ttl`, starts Fuseki and Varnish through the `local-fuseki` profile, and loads `SoilVoc_skosmos.ttl` into the local graph.

```powershell
cd C:\Users\wang479\Downloads\soil-vocabs\skosmos
$env:SKOSMOS_CONFIG = "./config/skosmos-config.local-fuseki.ttl"
docker compose --profile local-fuseki up -d --build
.\load-soilvoc.ps1
```

If your PowerShell execution policy blocks local scripts, run:

```powershell
powershell -ExecutionPolicy Bypass -File .\load-soilvoc.ps1
```

If the fallback stack was already running before a reload, restart the cache and frontend so old responses do not mask the updated graph:

```powershell
docker compose --profile local-fuseki restart fuseki-cache skosmos
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

For the local Fuseki fallback, include the profile when you want to stop profiled services explicitly:

```powershell
docker compose --profile local-fuseki down
```

## Clean Local Fuseki Reset

This removes the local Fuseki data volume and reloads the Skosmos copy from scratch:

```powershell
docker compose --profile local-fuseki down -v
python .\generate_skosmos_ttl.py
$env:SKOSMOS_CONFIG = "./config/skosmos-config.local-fuseki.ttl"
docker compose --profile local-fuseki up -d --build
.\load-soilvoc.ps1
```

## Notes

- Remote SPARQL endpoint: `https://sparql.soilwise.wetransform.eu/sparql/`
- Skosmos vocabulary graph URI: `https://w3id.org/eusoilvoc`
- SoilVoc concept URI space: `https://w3id.org/eusoilvoc#`
- Skosmos UI port: `9090`
- Local Fuseki fallback host port: `9030`
- Local Varnish fallback host port: `9031`
- The remote default uses Skosmos' Generic SPARQL dialect. Exact label searches such as `soil porosity` work directly; use wildcard terms such as `*porosity*` for partial single-word search checks.
- `SoilVoc_skosmos.ttl` is a generated Skosmos display copy; regenerate it from `../SoilVoc.ttl` and `soilvoc_ontology.ttl`.
- Override ports, image versions, or `SKOSMOS_CONFIG` by copying `.env.example` to `.env` and editing the values.
