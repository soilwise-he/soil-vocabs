from pathlib import Path

from rdflib import BNode, Graph, Namespace, URIRef
from rdflib.namespace import DCTERMS, RDF, SDO, SKOS

SOSA = Namespace("http://www.w3.org/ns/sosa/")

from api.models import (
    ConceptDetail,
    ConceptSummary,
    Definition,
    MatchRef,
)

_graph: Graph | None = None
_scheme_uri: str | None = None
_property_uris: set[str] = set()
_procedure_uris: set[str] = set()

DEFAULT_TTL_PATH = Path(__file__).resolve().parent.parent / "SoilVoc.ttl"

_MATCH_SOURCE_RULES: list[tuple[str, str]] = [
    ("http://aims.fao.org/aos/agrovoc/", "AGROVOC"),
    ("thesaurusINRAE", "INRAE"),
    ("eionet.europa.eu/gemet", "GEMET"),
    ("w3id.org/glosis/model", "GloSIS"),
    ("ISO11074", "ISO11074"),
    ("SoilPhysics.owl", "Soil Property Process ontology"),
    ("soil-health", "SHKG"),
]


def load_graph(path: str | Path | None = None) -> Graph:
    global _graph, _scheme_uri, _property_uris, _procedure_uris
    if _graph is None:
        _graph = Graph()
        _graph.parse(str(path or DEFAULT_TTL_PATH), format="turtle")
        schemes = list(_graph.subjects(RDF.type, SKOS.ConceptScheme))
        _scheme_uri = str(schemes[0]) if schemes else None
        # Properties are concepts that have procedures (subjects of sosa:hasProcedure)
        _property_uris = {str(subj) for subj in _graph.subjects(SOSA.hasProcedure, None)}
        # Procedures are concepts that are objects of sosa:hasProcedure
        _procedure_uris = {str(obj) for obj in _graph.objects(None, SOSA.hasProcedure)}
    return _graph


def get_graph() -> Graph:
    if _graph is None:
        raise RuntimeError("Graph not loaded — call load_graph() first")
    return _graph


def get_scheme_uri() -> str:
    if _scheme_uri is None:
        raise RuntimeError("Graph not loaded")
    return _scheme_uri


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _concept_type(uri_str: str) -> str | None:
    if uri_str in _property_uris:
        return "property"
    if uri_str in _procedure_uris:
        return "procedure"
    return None


def _match_source_label(uri: str) -> str | None:
    for pattern, label in _MATCH_SOURCE_RULES:
        if pattern in uri:
            return label
    return None


def _match_local_id(uri: str) -> str:
    if "#" in uri:
        return uri.split("#")[-1]
    return uri.rstrip("/").split("/")[-1]


def _pick_text_literal(g: Graph, node: URIRef | BNode) -> str | None:
    texts = list(g.objects(node, SDO.text))
    if not texts:
        texts = list(g.objects(node, RDF.value))
    if not texts:
        return None
    for t in texts:
        if getattr(t, "language", None) == "en":
            return str(t)
    return str(texts[0])


def _concept_summary(g: Graph, uri: URIRef) -> ConceptSummary:
    label = g.value(uri, SKOS.prefLabel)
    alt_label = g.value(uri, SKOS.altLabel)
    return ConceptSummary(
        uri=str(uri),
        label=str(label or str(uri).split("#")[-1].split("/")[-1]),
        alt_label=str(alt_label) if alt_label else None,
        type=_concept_type(str(uri)),
        definitions=_concept_definitions(g, uri),
    )


def _concept_definitions(g: Graph, uri: URIRef) -> list[Definition]:
    definitions: list[Definition] = []
    for defn in g.objects(uri, SKOS.definition):
        if isinstance(defn, BNode):
            text = _pick_text_literal(g, defn)
            source_val = g.value(defn, DCTERMS.source)
            if text:
                definitions.append(
                    Definition(text=text, source=str(source_val) if source_val else None)
                )
        else:
            definitions.append(Definition(text=str(defn)))
    return definitions


def _match_refs(g: Graph, uri: URIRef, predicate) -> list[MatchRef]:
    refs: list[MatchRef] = []
    for match_uri in g.objects(uri, predicate):
        match_str = str(match_uri)
        source = _match_source_label(match_str)
        local_id = _match_local_id(match_str)
        label = f"{source} ({local_id})" if source else local_id
        refs.append(MatchRef(uri=match_str, label=label, source=source))
    return refs


# ---------------------------------------------------------------------------
# Public query functions
# ---------------------------------------------------------------------------

def search_concepts(
    query: str,
    limit: int = 20,
    offset: int = 0,
    concept_type: str | None = None,
) -> tuple[list[ConceptSummary], int]:
    g = get_graph()
    q_lower = query.lower()
    matches: list[ConceptSummary] = []

    for concept_uri in g.subjects(RDF.type, SKOS.Concept):
        uri_str = str(concept_uri)
        ctype = _concept_type(uri_str)

        # Filter by type if requested
        if concept_type is not None and ctype != concept_type:
            continue

        pref_label = g.value(concept_uri, SKOS.prefLabel)
        alt_label = g.value(concept_uri, SKOS.altLabel)

        fields = [
            str(pref_label).lower() if pref_label else "",
            str(alt_label).lower() if alt_label else "",
        ]

        if any(q_lower in f for f in fields):
            matches.append(_concept_summary(g, concept_uri))

    matches.sort(key=lambda c: c.label.lower())
    total = len(matches)
    return matches[offset : offset + limit], total


def _resolve_concept_uri(fragment: str) -> URIRef | None:
    """Resolve a fragment ID to a concept URI, with case-insensitive fallback."""
    g = get_graph()
    uri = URIRef(f"{get_scheme_uri()}#{fragment}")
    if (uri, RDF.type, SKOS.Concept) in g:
        return uri
    for concept_uri in g.subjects(RDF.type, SKOS.Concept):
        concept_str = str(concept_uri)
        if "#" in concept_str and concept_str.split("#")[-1].lower() == fragment.lower():
            return concept_uri
    return None


def get_concept_detail(fragment: str) -> ConceptDetail | None:
    g = get_graph()
    uri = _resolve_concept_uri(fragment)
    if uri is None:
        return None

    summary = _concept_summary(g, uri)
    exact_match = _match_refs(g, uri, SKOS.exactMatch)
    close_match = _match_refs(g, uri, SKOS.closeMatch)

    # Broader
    broader = [_concept_summary(g, b) for b in g.objects(uri, SKOS.broader)]

    # Narrower (explicit + inverse broader)
    narrower_uris: set[URIRef] = set()
    for n in g.objects(uri, SKOS.narrower):
        narrower_uris.add(n)
    for s in g.subjects(SKOS.broader, uri):
        narrower_uris.add(s)
    narrower = sorted(
        [_concept_summary(g, n) for n in narrower_uris],
        key=lambda c: c.label.lower(),
    )

    # Procedures
    procedures = [_concept_summary(g, p) for p in g.objects(uri, SOSA.hasProcedure)]

    return ConceptDetail(
        **summary.model_dump(),
        exact_match=exact_match,
        close_match=close_match,
        broader=broader,
        narrower=narrower,
        procedures=procedures,
    )


def get_property_procedures(fragment: str, q: str | None = None) -> list[ConceptSummary] | None:
    """Return procedures for a property, optionally filtered by search term. Returns None if not found or not a property."""
    g = get_graph()
    uri = _resolve_concept_uri(fragment)
    if uri is None:
        return None
    if str(uri) not in _property_uris:
        return None
    procedures = [_concept_summary(g, p) for p in g.objects(uri, SOSA.hasProcedure)]
    if q:
        q_lower = q.lower()
        procedures = [
            p for p in procedures
            if q_lower in p.label.lower()
            or (p.alt_label and q_lower in p.alt_label.lower())
        ]
    procedures.sort(key=lambda c: c.label.lower())
    return procedures
