"""Cache external mapping-target descriptions for display, never for SoilVoc enrichment.

Close-match targets keep their original labels and definitions. Other SKOS mapping
targets, such as exact matches, keep only their original labels, when the source has one.
The written cache holds the English subset the viewer shows.
"""

import argparse
from collections import defaultdict
from datetime import datetime, timezone
from functools import lru_cache
from hashlib import sha256
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import DCTERMS, RDF, RDFS, SKOS

ROOT = Path(__file__).resolve().parents[2]
GEMET_SOURCE = URIRef("http://www.eionet.europa.eu/gemet/2004/06/gemet-schema.rdf#source")
TEXT_PREDICATES = (RDF.value, URIRef("https://schema.org/text"), URIRef("http://schema.org/text"))
MAPPING_PREDICATES = (SKOS.exactMatch, SKOS.closeMatch, SKOS.broadMatch, SKOS.narrowMatch, SKOS.relatedMatch)
GLOSIS_VERSION = "71aa9f7888675e4395182fda74499fd72866c893"
SOURCES = {
    "agrovoc": {"prefix": "http://aims.fao.org/aos/agrovoc/", "endpoint": "https://agrovoc.fao.org/sparql"},
    "nalt": {"prefix": "https://lod.nal.usda.gov/nalt/", "endpoint": "https://lod.nal.usda.gov/rest/v1/nalt/data"},
    "inrae": {"prefix": "http://opendata.inrae.fr/thesaurusINRAE/", "endpoint": "https://consultation.vocabulaires-ouverts.inrae.fr/rest/v1/thesaurus-inrae/data"},
    "iso11074": {"prefix": "https://data.geoscience.earth/ncl/ISO11074v2025/"},
    "gemet": {"prefix": "http://www.eionet.europa.eu/gemet/concept/", "endpoint": "https://sparql.agroportal.eu/sparql"},
    "unbis": {"prefix": "http://metadata.un.org/thesaurus/", "endpoint": "https://metadata.un.org/skosmos/rest/v1/thesaurus/data"},
    "stw": {"prefix": "http://zbw.eu/stw/descriptor/", "record_url": "https://zbw.eu/stw/version/latest/descriptor/{id}/about.ttl"},
    "gnd": {
        "prefix": "https://d-nb.info/gnd/", "record_url": "https://lobid.org/gnd/{id}.ttl",
        "label_predicates": (URIRef("https://d-nb.info/standards/elementset/gnd#preferredName"),),
        "definition_predicates": (SKOS.definition, URIRef("https://d-nb.info/standards/elementset/gnd#definition")),
    },
    "thesoz": {
        "prefix": "https://data.gesis.org/thesoz/concept_",
        "release": "https://zenodo.org/records/18773539/files/thesoz.ttl?download=1",
        "sha256": "43f17d959ae2df19ac9724aa7db636883d80c8498b9936eb89093f8601a97d22",
    },
    "shkg": {"prefix": "https://soilwise-he.github.io/soil-health#", "path": "ontovocabs/shkg/soil_health_KG.ttl"},
    "benchmarks": {
        "prefix": "https://soilhealthbenchmarks.eu/glossary/",
        "path": "ontovocabs/shb/soil_health_benchmarks.ttl",
        "definition_predicates": (
            SKOS.definition, URIRef("https://soilwise-he.github.io/soil-health#policyDefinition"),
            URIRef("https://soilwise-he.github.io/soil-health#scientificDefinition"),
        ),
    },
    # The original Soil Property and Process Ontology snapshot; its classes have no labels.
    "spp": {"prefix": "http://imash.leeds.ac.uk/ontologies/atu/SoilPhysics.owl#", "path": "ontovocabs/spp/soil_property_process.ttl"},
    # These mapped identifiers predate GLOSIS v2. Keep the exact original records.
    "glosis": {
        "prefix": "http://w3id.org/glosis/model/",
        "endpoint": f"https://raw.githubusercontent.com/glosis-ld/glosis/{GLOSIS_VERSION}/",
        "version": GLOSIS_VERSION,
        "modules": {
            "codelists": "glosis_cl.ttl", "common": "glosis_common.ttl", "procedure": "glosis_procedure.ttl",
            "profile": "glosis_profile.ttl", "siteplot": "glosis_siteplot.ttl", "surface": "glosis_surface.ttl",
            # The pinned layer/horizon file is not valid Turtle (an undeclared `cm:` prefix). The repository's
            # snapshot differs only in unit restrictions, so its labels and definitions are the same.
            "layerhorizon": {"path": "ontovocabs/glosis/glosis_ori/glosis_layer_horizon.ttl"},
        },
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


def original_labels(graph, uri, source):
    if not any(graph.triples((uri, None, None))):
        raise ValueError(f"Source record missing: {uri}")
    # OWL-based sources such as GLOSIS label some classes and properties only with rdfs:label.
    for predicate in (SKOS.prefLabel, RDFS.label, *SOURCES.get(source, {}).get("label_predicates", ())):
        labels = unique(literal(value) for value in graph.objects(uri, predicate) if isinstance(value, Literal))
        if labels:
            return labels
    raise ValueError(f"No original preferred label found: {uri}")


def extract_record(graph, uri, source, provenance):
    labels = original_labels(graph, uri, source)
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


def extract_labels(graph, uri, source, provenance):
    """Label-only record for exact and other mapping targets; their definitions are not shown."""
    return {"source": source, "prefLabels": original_labels(graph, uri, source), "provenance": provenance}


def keep(records, uri, build, skipped):
    """Close-match records must resolve. Label lookups note a missing record and continue."""
    try:
        records[str(uri)] = build()
    except (ValueError, HTTPError) as exc:
        if skipped is None or (isinstance(exc, HTTPError) and exc.code not in (404, 410)):
            raise
        skipped.append((str(uri), f"HTTP {exc.code}" if isinstance(exc, HTTPError) else str(exc).split(":")[0]))


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


def fetch_batch(source, targets, *, extract=extract_record, skipped=None):
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
            keep(records, uri, lambda uri=uri: extract(graph, uri, source, provenance), skipped)
    return records


def glosis_module(uri):
    return str(uri)[len(SOURCES["glosis"]["prefix"]):].split("/", 1)[0]


@lru_cache(maxsize=1)
def release_graph(url, digest):
    # Both the close-match and label-only passes use the same publisher snapshot.
    payload = request(url)
    if sha256(payload).hexdigest() != digest:
        raise ValueError(f"Unexpected checksum for vocabulary release: {url}")
    return Graph().parse(data=payload, format="turtle")


def fetch_source(source, targets, *, extract=extract_record, skipped=None):
    """Fetch records for one source. With `skipped`, missing records are noted instead of failing."""
    if source in ("agrovoc", "gemet"):
        return fetch_batch(source, targets, extract=extract, skipped=skipped)
    config = SOURCES[source]
    shared = {}
    if "path" in config:
        payload = (ROOT / config["path"]).read_bytes()
        shared[None] = Graph().parse(data=payload, format="turtle"), {"file": config["path"], "sha256": sha256(payload).hexdigest()}
    elif "release" in config:
        url, digest = config["release"], config["sha256"]
        shared[None] = release_graph(url, digest), {"endpoint": url, "sha256": digest}
    elif source == "glosis":
        for module in sorted({glosis_module(uri) for uri in targets}):
            entry = config["modules"][module]
            if isinstance(entry, dict):
                payload = (ROOT / entry["path"]).read_bytes()
                provenance = {"file": entry["path"], "sha256": sha256(payload).hexdigest()}
            else:
                url = config["endpoint"] + entry
                payload = request(url)
                provenance = {"endpoint": url, "version": config["version"], "sha256": sha256(payload).hexdigest()}
            shared[module] = Graph().parse(data=payload, format="turtle"), provenance

    def build(uri):
        if shared:
            graph, provenance = shared[glosis_module(uri) if source == "glosis" else None]
        elif "record_url" in config:
            url = config["record_url"].format(id=quote(str(uri)[len(config["prefix"]):], safe=""))
            graph, provenance = Graph().parse(data=request(url), format="turtle"), {"endpoint": url}
        else:
            url = str(uri) if source == "iso11074" else config["endpoint"]
            params = {"_format": "ttl", "status": "valid"} if source == "iso11074" else {"uri": str(uri), "format": "text/turtle"}
            graph, provenance = Graph().parse(data=request(url, params), format="turtle"), {"endpoint": url}
        return extract(graph, uri, source, provenance)

    records = {}
    for index, uri in enumerate(targets, 1):
        keep(records, uri, lambda uri=uri: build(uri), skipped)
        if index % 25 == 0:
            print(f"{source}: {index}/{len(targets)}", flush=True)
        if not shared:
            time.sleep(0.15)
    return records


def fetch_labels(source, targets):
    """Best-effort labels for exact and other mapping targets; the viewer shows the URI otherwise."""
    skipped = []
    return fetch_source(source, targets, extract=extract_labels, skipped=skipped), skipped


def source_for(uri):
    name = next((name for name, config in SOURCES.items() if str(uri).startswith(config["prefix"])), None)
    if name == "glosis" and glosis_module(uri) not in SOURCES["glosis"]["modules"]:
        return None
    return name


def mapping_targets(graph, predicates=MAPPING_PREDICATES):
    return sorted({target for predicate in predicates for concept, target in graph.subject_objects(predicate)
                   if isinstance(target, URIRef) and (concept, RDF.type, SKOS.Concept) in graph}, key=str)


def close_match_targets(graph):
    return mapping_targets(graph, (SKOS.closeMatch,))


def preferred(values, any_language=True):
    """English first, then untagged text; only labels may fall back to their original language."""
    for accept in (lambda tag: tag == "en", lambda tag: tag.split("-")[0] == "en", lambda tag: not tag):
        chosen = [value for value in values if accept(value["language"].lower())]
        if chosen:
            return chosen
    return values if any_language else []


def display_record(record):
    """The cache keeps what the English viewer shows: no definitions in other languages."""
    trimmed = {**record, "prefLabels": preferred(record["prefLabels"])}
    if "definitions" in record:
        trimmed["definitions"] = preferred(record["definitions"], any_language=False)
    return trimmed


def generate(input_path, output_path):
    # Never allow the add-on writer to replace a vocabulary/source file.
    if output_path.suffix.lower() != ".json" or output_path.resolve() == input_path.resolve():
        raise ValueError("Output must be a separate .json file")
    payload = input_path.read_bytes()
    graph = Graph().parse(data=payload, format="turtle")
    close = close_match_targets(graph)
    batches, label_batches, skipped = defaultdict(list), defaultdict(list), defaultdict(list)
    for uri in close:
        source = source_for(uri)
        if source is None:
            raise ValueError(f"Unsupported source: {uri}; existing cache was not changed")
        batches[source].append(uri)
    for uri in sorted(set(mapping_targets(graph)) - set(close), key=str):
        source = source_for(uri)
        if source is None:
            skipped["unsupported"].append((str(uri), "No configured source"))
        else:
            label_batches[source].append(uri)
    records = {}
    for source, uris in batches.items():
        records.update(fetch_source(source, uris))
        print(f"{source}: cached {len(uris)} original close-match records", flush=True)
    for source, uris in label_batches.items():
        found, missing = fetch_labels(source, uris)
        records.update(found)
        skipped[source].extend(missing)
        print(f"{source}: cached labels for {len(found)} of {len(uris)} other mapping targets", flush=True)
    for source, entries in sorted(skipped.items()):
        reasons = defaultdict(list)
        for uri, reason in entries:
            reasons[reason].append(uri)
        for reason, uris in sorted(reasons.items()):
            print(f"Shown as URIs: {source}, {reason}: {len(uris)} (e.g. {', '.join(uris[:3])})", flush=True)
    document = {
        "schemaVersion": 1,
        "retrievedAt": datetime.now(timezone.utc).isoformat(),
        "vocabularySha256": sha256(payload).hexdigest(),
        "records": {uri: display_record(record) for uri, record in sorted(records.items())},
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
