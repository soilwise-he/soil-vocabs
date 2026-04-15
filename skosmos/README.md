# Local Skosmos Deployment for SoilVoc

This folder contains a local Docker Compose deployment for browsing SoilVoc in Skosmos.

The stack follows the NatLibFi Skosmos Docker pattern:

- `skosmos`: Skosmos web UI from `quay.io/natlibfi/skosmos`
- `fuseki`: Apache Jena Fuseki with Jena Text indexing
- `fuseki-cache`: Varnish cache in front of Fuseki
- `plugins/soilvoc-definition-source`: a SoilVoc-only Skosmos plugin that displays definition text with its source and enriches the hierarchy sidebar with semantic SOSA procedure children

## Prerequisites

- Docker Desktop must be running and accessible from this shell.
- Internet access is required for the first run to pull/build Docker images.
- `SoilVoc.ttl` must exist at the repository root.

## Generate Skosmos Data

`../SoilVoc.ttl` remains the canonical source. Generate the Skosmos display copy before loading Fuseki:

```powershell
python .\generate_skosmos_ttl.py
```

This writes `SoilVoc_skosmos.ttl`. The generated copy preserves canonical definition blank-node `rdf:value` text, rewrites legacy `schema:text` values if present, keeps SKOS and SOSA links semantic, and adds display-only `eusoilvoc:skosmosHierarchyParent` triples for Skosmos sidebar traversal. This lets procedures appear in the sidebar without becoming false SKOS narrower concepts. The canonical `../SoilVoc.ttl` is not changed by this script.

## Start

```powershell
cd C:\Users\wang479\Downloads\soil-vocabs\skosmos
Copy-Item .env.example .env
docker compose up -d --build
```

Skosmos will be available at:

```text
http://localhost:9090/
```

Fuseki will be available at:

```text
http://localhost:9030/
```

## Load SoilVoc

Run this after the containers are up. It replaces the SoilVoc graph with `SoilVoc_skosmos.ttl`, then adds `soilvoc_ontology.ttl` to the same graph so advanced relationship labels are available to Skosmos.

```powershell
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

Equivalent manual command:

```powershell
Invoke-WebRequest `
  -Method Put `
  -ContentType "text/turtle" `
  -InFile .\SoilVoc_skosmos.ttl `
  -Uri "http://localhost:9030/skosmos/data?graph=https%3A%2F%2Fw3id.org%2Feusoilvoc" `
  -UseBasicParsing

Invoke-WebRequest `
  -Method Post `
  -ContentType "text/turtle" `
  -InFile .\soilvoc_ontology.ttl `
  -Uri "http://localhost:9030/skosmos/data?graph=https%3A%2F%2Fw3id.org%2Feusoilvoc" `
  -UseBasicParsing
```

## Smoke Tests

Check container status:

```powershell
docker compose ps
```

Check that triples were loaded:

```powershell
Invoke-WebRequest `
  -Method Post `
  -ContentType "application/x-www-form-urlencoded" `
  -Body "query=SELECT (COUNT(*) AS ?count) WHERE { GRAPH <https://w3id.org/eusoilvoc> { ?s ?p ?o } }" `
  -Uri "http://localhost:9030/skosmos/query" `
  -UseBasicParsing
```

Then open `http://localhost:9090/`, select SoilVoc, and search for `soil porosity`. Open a concept with a sourced definition such as `MineralConcVolume` and confirm the Definition row includes a Source line. Open `BaseSaturation` to confirm `Has procedure` is shown on the concept page and procedure children are available through the hierarchy navigation.

## Stop

```powershell
docker compose down
```

## Clean Reset

This removes the Fuseki data volume and reloads the Skosmos copy from scratch:

```powershell
docker compose down -v
python .\generate_skosmos_ttl.py
docker compose up -d --build
.\load-soilvoc.ps1
```

## Notes

- Skosmos vocabulary graph URI: `https://w3id.org/eusoilvoc`
- SoilVoc concept URI space: `https://w3id.org/eusoilvoc#`
- Skosmos UI port: `9090`
- Fuseki host port: `9030`
- Varnish cache host port: `9031`
- `SoilVoc_skosmos.ttl` is a generated Skosmos display copy; regenerate it from `../SoilVoc.ttl`.
- Override ports or image versions by copying `.env.example` to `.env` and editing the values.
