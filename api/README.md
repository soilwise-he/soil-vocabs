# SoilVoc API

REST API for querying the [SoilVoc](https://soilwise-he.github.io/soil-vocabs/) SKOS vocabulary, built with FastAPI and rdflib.

The API loads `SoilVoc.ttl` into memory at startup and serves concept data directly from the RDF graph — no build step or intermediate JSON required.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running

From the repository root:

```bash
source .venv/bin/activate
uvicorn api.main:app --reload
```

The server starts at `http://localhost:8000`. Interactive API docs are available at:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

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

A docker image is available on ghcr.io.

```
docker run -p8000:8000 ghcr.io/soilwise-he/soil-vocabs:latest
```

You can set an env variable 'ROOTPATH' to /example to run the api at a path, e.g. http://example.com/example/docs.