"""Cache external close-match descriptions for display, never for SoilVoc enrichment."""

import argparse
from collections import defaultdict
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import DCTERMS, RDF, SKOS

ROOT = Path(__file__).resolve().parents[2]
GEMET_SOURCE = URIRef("http://www.eionet.europa.eu/gemet/2004/06/gemet-schema.rdf#source")
TEXT_PREDICATES = (RDF.value, URIRef("https://schema.org/text"), URIRef("http://schema.org/text"))
SOURCES = {
    "agrovoc": {"prefix": "http://aims.fao.org/aos/agrovoc/", "endpoint": "https://agrovoc.fao.org/sparql"},
    "nalt": {"prefix": "https://lod.nal.usda.gov/nalt/", "endpoint": "https://lod.nal.usda.gov/rest/v1/nalt/data"},
    "inrae": {"prefix": "http://opendata.inrae.fr/thesaurusINRAE/", "endpoint": "https://consultation.vocabulaires-ouverts.inrae.fr/rest/v1/thesaurus-inrae/data"},
    "iso11074": {"prefix": "https://data.geoscience.earth/ncl/ISO11074v2025/"},
    "gemet": {"prefix": "http://www.eionet.europa.eu/gemet/concept/", "endpoint": "https://sparql.agroportal.eu/sparql"},
    "shkg": {"prefix": "https://soilwise-he.github.io/soil-health#", "path": "ontovocabs/shkg/soil_health_KG.ttl"},
    "benchmarks": {
        "prefix": "https://soilhealthbenchmarks.eu/glossary/",
        "path": "ontovocabs/shb/soil_health_benchmarks.ttl",
        "definition_predicates": (
            SKOS.definition, URIRef("https://soilwise-he.github.io/soil-health#policyDefinition"),
            URIRef("https://soilwise-he.github.io/soil-health#scientificDefinition"),
        ),
    },
    # These mapped identifiers predate GLOSIS v2. Keep the exact original records.
    "glosis": {
        "prefix": "http://w3id.org/glosis/model/codelists/",
        "endpoint": "https://raw.githubusercontent.com/glosis-ld/glosis/71aa9f7888675e4395182fda74499fd72866c893/glosis_cl.ttl",
        "version": "71aa9f7888675e4395182fda74499fd72866c893",
    },
}


def request(url, params=None, *, post=False, accept="text/turtle"):
    encoded = urlencode(params or {})
    req = Request(
        url + ("?" + encoded if encoded and not post else ""),
        data=encoded.encode() if post else None,
        headers={"Accept": accept, "User-Agent": "SoilVoc-close-match-preview/1.0"},
    )
    for attempt in range(3):
        try:
            with urlopen(req, timeout=30) as response:
                return response.read()
        except (HTTPError, URLError, TimeoutError) as exc:
            transient = not isinstance(exc, HTTPError) or exc.code in (408, 429) or exc.code >= 500
            if not transient or attempt == 2:
                raise
            time.sleep(2 ** (attempt + 1))


def literal(value):
    return {"text": str(value), "language": value.language or ""}


def citation(value):
    if isinstance(value, URIRef):
        return {"uri": str(value)}
    if isinstance(value, Literal):
        return literal(value)
    raise ValueError("Structured citation needs review; refusing to discard it")


def unique(values):
    return [json.loads(key) for key in sorted({json.dumps(value, ensure_ascii=False, sort_keys=True) for value in values})]


def extract_record(graph, uri, source, provenance):
    if not any(graph.triples((uri, None, None))):
        raise ValueError(f"Source record missing: {uri}")
    labels = unique(literal(value) for value in graph.objects(uri, SKOS.prefLabel) if isinstance(value, Literal))
    if not labels:
        raise ValueError(f"No original preferred label found: {uri}")
    definitions = []
    predicates = SOURCES.get(source, {}).get("definition_predicates", (SKOS.definition,))
    for node in {node for predicate in predicates for node in graph.objects(uri, predicate)}:
        citations = {uri}
        if isinstance(node, Literal):
            texts = [node]
        else:
            texts = [value for predicate in TEXT_PREDICATES for value in graph.objects(node, predicate)]
            citations.update(graph.objects(node, DCTERMS.source))
            if not texts:
                raise ValueError(f"Unresolved definition node for {uri}: {node}")
        if source == "gemet":
            citations.update(graph.objects(uri, GEMET_SOURCE))
        for value in texts:
            if isinstance(value, Literal) and str(value).strip():
                definitions.append({**literal(value), "sources": unique(citation(c) for c in citations)})
    return {"source": source, "prefLabels": labels, "definitions": unique(definitions), "provenance": provenance}


def gemet_graph(endpoint):
    prefix = "http://data.bioontology.org/ontologies/GEMET/submissions/"
    query = f"""
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
SELECT ?graph ?version WHERE {{
  GRAPH ?graph {{ <http://www.eionet.europa.eu/gemet/gemetThesaurus>
    <http://www.w3.org/2000/01/rdf-schema#label> ?version . }}
  FILTER(STRSTARTS(STR(?graph), {Literal(prefix).n3()}))
  BIND(xsd:integer(STRAFTER(STR(?graph), {Literal(prefix).n3()})) AS ?submission)
  FILTER(BOUND(?submission))
}} ORDER BY DESC(?submission) LIMIT 1
"""
    result = json.loads(request(endpoint, {"query": query, "format": "application/sparql-results+json"},
                                post=True, accept="application/sparql-results+json"))["results"]["bindings"]
    if len(result) != 1:
        raise ValueError("No GEMET submission found")
    uri = result[0]["graph"]["value"]
    if not uri.startswith(prefix) or not uri[len(prefix):].isdigit():
        raise ValueError("Unexpected GEMET submission graph")
    return uri, result[0]["version"]["value"]


def fetch_batch(source, targets):
    config = SOURCES[source]
    provenance = {"endpoint": config["endpoint"]}
    selected_graph = None
    if source == "gemet":
        selected_graph, version = gemet_graph(config["endpoint"])
        provenance.update(graph=selected_graph, version=version)
    records = {}
    for start in range(0, len(targets), 50):
        batch = targets[start:start + 50]
        values = " ".join(uri.n3() for uri in batch)
        predicates = " ".join(p.n3() for p in (*TEXT_PREDICATES, DCTERMS.source))
        body = f"""
  ?concept a skos:Concept .
  OPTIONAL {{ ?concept skos:prefLabel ?label . }}
  OPTIONAL {{ ?concept {GEMET_SOURCE.n3()} ?source . }}
  OPTIONAL {{ ?concept skos:definition ?definition .
    OPTIONAL {{ VALUES ?predicate {{ {predicates} }} ?definition ?predicate ?value . }}
  }}
"""
        if selected_graph:
            body = f"GRAPH {URIRef(selected_graph).n3()} {{ {body} }}"
        query = f"""
PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
CONSTRUCT {{
  ?concept a skos:Concept ; skos:prefLabel ?label ; skos:definition ?definition ; {GEMET_SOURCE.n3()} ?source .
  ?definition ?predicate ?value .
}} WHERE {{ VALUES ?concept {{ {values} }} {body} }}
"""
        payload = request(config["endpoint"], {"query": query, "format": "text/turtle"}, post=source == "gemet")
        graph = Graph().parse(data=payload, format="turtle")
        for uri in batch:
            records[str(uri)] = extract_record(graph, uri, source, provenance)
    return records


def fetch_source(source, targets):
    if source in ("agrovoc", "gemet"):
        return fetch_batch(source, targets)
    config = SOURCES[source]
    shared_graph = None
    if "path" in config:
        payload = (ROOT / config["path"]).read_bytes()
        shared_graph = Graph().parse(data=payload, format="turtle")
        provenance = {"file": config["path"], "sha256": sha256(payload).hexdigest()}
    elif source == "glosis":
        payload = request(config["endpoint"])
        shared_graph = Graph().parse(data=payload, format="turtle")
        provenance = {"endpoint": config["endpoint"], "version": config["version"], "sha256": sha256(payload).hexdigest()}
    records = {}
    for index, uri in enumerate(targets, 1):
        if shared_graph is not None:
            graph = shared_graph
        else:
            url = str(uri) if source == "iso11074" else config["endpoint"]
            params = {"_format": "ttl", "status": "valid"} if source == "iso11074" else {"uri": str(uri), "format": "text/turtle"}
            graph = Graph().parse(data=request(url, params), format="turtle")
            provenance = {"endpoint": url}
        records[str(uri)] = extract_record(graph, uri, source, provenance)
        if index % 25 == 0:
            print(f"{source}: {index}/{len(targets)}", flush=True)
        if shared_graph is None:
            time.sleep(0.15)
    return records


def close_match_targets(graph):
    return sorted({target for concept, target in graph.subject_objects(SKOS.closeMatch)
                   if isinstance(target, URIRef) and (concept, RDF.type, SKOS.Concept) in graph}, key=str)


def generate(input_path, output_path):
    # Never allow the add-on writer to replace a vocabulary/source file.
    if output_path.suffix.lower() != ".json" or output_path.resolve() == input_path.resolve():
        raise ValueError("Output must be a separate .json file")
    payload = input_path.read_bytes()
    targets = close_match_targets(Graph().parse(data=payload, format="turtle"))
    batches = defaultdict(list)
    for uri in targets:
        source = next((name for name, config in SOURCES.items() if str(uri).startswith(config["prefix"])), None)
        if source is None:
            raise ValueError(f"Unsupported source: {uri}; existing cache was not changed")
        batches[source].append(uri)
    records = {}
    for source, uris in batches.items():
        records.update(fetch_source(source, uris))
        print(f"{source}: cached {len(uris)} original records", flush=True)
    document = {
        "schemaVersion": 1,
        "retrievedAt": datetime.now(timezone.utc).isoformat(),
        "vocabularySha256": sha256(payload).hexdigest(),
        "records": dict(sorted(records.items())),
    }
    temporary = None
    try:
        with NamedTemporaryFile(mode="w", encoding="utf-8", dir=output_path.parent, delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(document, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temporary, output_path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    print(f"Wrote {len(records)} external previews to {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "viewer/data/SoilVoc.ttl")
    parser.add_argument("--output", type=Path, default=ROOT / "viewer/data/close-matches.json")
    args = parser.parse_args()
    generate(args.input, args.output)
