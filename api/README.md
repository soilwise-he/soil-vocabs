# SoilVoc API

REST API for querying the [SoilVoc](https://soilwise-he.github.io/soil-vocabs/) SKOS vocabulary, built with FastAPI and rdflib.

The API loads `SoilVoc.ttl` into memory at startup and serves concept data
directly from the RDF graph. No RDF-to-JSON preprocessing is required; building
the frontend served by the app is a separate step described below.

This service is optional. The GitHub Pages viewer reads its own committed RDF
snapshot in the browser and does not call the API. API requests use canonical
`SoilVoc.ttl`, while the viewer uses `viewer/data/SoilVoc.ttl`; update the relevant
input for each surface. Restart the API after changing its canonical RDF input.

## Setup

Run from the repository root. On PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

On Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Running

The FastAPI app also mounts the static frontend at startup, so the configured
`SITEPATH` directory must exist even when only testing API endpoints. From the
repository root, build the viewer with Node.js 24 and npm first:

```bash
npm --prefix viewer ci
npm --prefix viewer run build
```

With the Python environment activated, start the app on PowerShell:

```powershell
$env:SITEPATH = "viewer/dist"
python -m uvicorn api.main:app --reload
```

On Linux/macOS:

```bash
SITEPATH=viewer/dist python -m uvicorn api.main:app --reload
```

The server starts at `http://localhost:8000`. Interactive API docs are available at:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

The same server hosts the built viewer at `http://localhost:8000/`. For a
viewer-only setup without Python or this server, follow [viewer/README.md](../viewer/README.md).

## Concept types

Concepts in SoilVoc can have a `type`:

- `"property"` — observable soil properties (concepts that have procedures via `sosa:hasProcedure`)
- `"procedure"` — measurement procedures linked to properties
- `null` — general concepts that are neither a property nor a procedure

## Endpoints

### Search concepts

```
GET /api/v1/concepts/search?q={term}&type={type}&limit={n}&offset={n}
```

Searches across `prefLabel` and `altLabel` (case-insensitive substring match). Results are sorted alphabetically by label.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `q` | string | required | Search term (min 1 character) |
| `type` | string | none | Filter by type: `property` or `procedure`. Omit for all |
| `limit` | int | 20 | Max results (1–100) |
| `offset` | int | 0 | Number of results to skip |

Example:

```bash
curl "http://localhost:8000/api/v1/concepts/search?q=bulk&type=property"
```

```json
{
  "query": "bulk",
  "total": 2,
  "results": [
    {
      "uri": "https://w3id.org/eusoilvoc#BulkDensityFineEarth",
      "label": "bulk density fine earth",
      "alt_label": null,
      "type": "property",
      "definitions": [
        {
          "text": "...",
          "source": "http://w3id.org/glosis/model/layerhorizon/bulkDensityFineEarthProperty"
        }
      ]
    },
    {
      "uri": "https://w3id.org/eusoilvoc#BulkDensityWholeSoil",
      "label": "bulk density whole soil",
      "alt_label": null,
      "type": "property",
      "definitions": []
    }
  ]
}
```

### Get vocabulary tree

```
GET /api/v1/concepts/tree
```

Returns the full vocabulary hierarchy as nested objects keyed by `prefLabel`. Roots are the scheme's top concepts (`skos:hasTopConcept`); children come from `skos:narrower` and inverse `skos:broader`. Leaves are empty objects. Takes no parameters.

Example:

```bash
curl "http://localhost:8000/api/v1/concepts/tree"
```

```json
{
  "soil": {
    "soil properties": {
      "soil chemical properties": {
        "soil nutrients": {
          "micronutrients": {
            "boron": {},
            "copper": {},
            "iron": {}
          }
        },
        "soil pH": {}
      }
    }
  }
}
```

Notes:

- Concepts with multiple broader parents appear under each parent.
- Procedures are not part of the tree (they are linked via `sosa:hasProcedure`, not `skos:broader`).
- The tree is computed once and cached for the lifetime of the process.

### Get concept detail

```
GET /api/v1/concepts/{fragment}
```

Returns full concept information by fragment ID (the part after `#` in the URI). Fragment matching is case-insensitive.

Example:

```bash
curl "http://localhost:8000/api/v1/concepts/BiologicalAbundance"
```

```json
{
  "uri": "https://w3id.org/eusoilvoc#BiologicalAbundance",
  "label": "biological abundance",
  "alt_label": null,
  "type": null,
  "definitions": [
    {
      "text": "The Biological Abundance evaluates the presence and quantity of soil organisms...",
      "source": "http://w3id.org/glosis/model/layerhorizon/biologicalAbundanceProperty"
    }
  ],
  "exact_match": [
    {
      "uri": "http://w3id.org/glosis/model/layerhorizon/biologicalAbundanceProperty",
      "label": "GloSIS (biologicalAbundanceProperty)",
      "source": "GloSIS"
    }
  ],
  "close_match": [],
  "broader": [
    {
      "uri": "https://w3id.org/eusoilvoc#SoilBiologicalProperties",
      "label": "soil biological properties",
      "alt_label": "soil biological property",
      "type": null,
      "definitions": []
    }
  ],
  "narrower": [],
  "procedures": []
}
```

Returns `404` if the concept is not found.

### Get procedures for a property

```
GET /api/v1/concepts/{fragment}/procedures?q={term}
```

Returns all procedures linked to a property. Optionally filter by search term.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `q` | string | none | Optional search term to filter procedures by label |

Example:

```bash
curl "http://localhost:8000/api/v1/concepts/BulkDensityFineEarth/procedures?q=cl"
```

```json
{
  "query": "cl",
  "total": 3,
  "results": [
    {
      "uri": "https://w3id.org/eusoilvoc#bulkDensityFineEarthProcedure-BlkDensF_fe-cl-fc",
      "label": "BlkDensF_fe-cl-fc",
      "alt_label": null,
      "type": "procedure",
      "definitions": [...]
    }
  ]
}
```

Returns `404` if the concept is not found or is not a property.

## Project structure

```
api/
├── main.py          # FastAPI app, lifespan (loads TTL at startup)
├── models.py        # Pydantic response schemas
├── vocab.py         # RDF graph loader and query functions
└── routers/
    └── concepts.py  # /concepts endpoints
```

## Docker

The optional container serves both the REST API and the static vocabulary
viewer. It does not run Skosmos, Fuseki, or a separate triplestore. Use the
published GHCR image:

```bash
docker run --rm -p 127.0.0.1:8000:8000 ghcr.io/soilwise-he/soil-vocabs:latest
```

Or build from the current checkout at the repository root:

```bash
docker build -f docker/Dockerfile -t soilvoc .
docker run --rm -p 127.0.0.1:8000:8000 soilvoc
```

- `/` — static vocabulary viewer
- `/api/v1/concepts/...` — REST API
- `/docs` — Swagger UI

### Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ROOTPATH` | (empty) | Set to e.g. `/example` to run behind a reverse proxy at a sub-path |
| `SITEPATH` | `site` | Existing built viewer directory. The image supplies `site`; for source-based development, use `viewer/dist` |

The Docker build compiles the same `viewer/` frontend used by GitHub Pages.
Static assets, bundled vocabulary data, and images are served below `/`, after
the API and documentation routes. The API still loads canonical `SoilVoc.ttl`;
the browser viewer reads its separate bundled `data/SoilVoc.ttl`, built from
`viewer/data/SoilVoc.ttl`. Neither the API image nor the Pages build requires
the local-only Skosmos deployment.

`.github/workflows/build-api-image.yml` builds and publishes the container image
on relevant pushes to `main`. It is separate from the Pages workflow and does
not deploy a server or update local reference containers. Local-only tests,
Skosmos and Cloudflare files are excluded from the image build context.
