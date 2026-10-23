"""Restore and strictly compare SoilVoc using a self-contained CSV reader."""

import argparse
import csv
import re
from collections import Counter, defaultdict
from graphlib import CycleError, TopologicalSorter
from pathlib import Path
from urllib.parse import urlsplit

from rdflib import BNode, Graph, Literal, Namespace, URIRef
from rdflib.compare import graph_diff, to_isomorphic
from rdflib.namespace import DCTERMS, RDF, SKOS

SOSA = Namespace("http://www.w3.org/ns/sosa/")
SCHEME_URI = "https://w3id.org/eusoilvoc"
COLUMNS = (
    "id", "type", "prefLabel", "altLabel", "definition", "broader", "narrower",
    "property", "exactMatch", "closeMatch", "definitionSource", "conceptSource",
)
TYPE_NAMES = {
    SKOS.Concept: "skos:Concept",
    SOSA.ObservableProperty: "sosa:ObservableProperty",
    SOSA.Procedure: "sosa:Procedure",
}
URI_COLUMNS = {
    "broader": SKOS.broader,
    "narrower": SKOS.narrower,
    "property": SOSA.isProcedureFor,
    "exactMatch": SKOS.exactMatch,
    "closeMatch": SKOS.closeMatch,
    "conceptSource": DCTERMS.source,
}
SEPARATOR = " | "

REPO_ROOT = Path(__file__).resolve().parent.parent
EUSOILVOC_SCHEME_URI = SCHEME_URI


def graphs_isomorphic(left: Graph, right: Graph) -> bool:
    """Compare all RDF triples, canonicalizing disconnected blank-node components.

    URI/literal terms cannot be renamed by an isomorphism. Blank-node components
    can be compared independently with those fixed terms as anchors. This avoids
    globally canonicalizing hundreds of unrelated definition nodes; multiplicity
    still matters when several components have identical RDFLib fingerprints.
    """
    def partition(graph):
        named = set()
        incident = defaultdict(set)
        for triple in graph:
            nodes = {term for term in triple if isinstance(term, BNode)}
            if not nodes:
                named.add(triple)
            for node in nodes:
                incident[node].add(triple)
        remaining = set(incident)
        components = Counter()
        while remaining:
            pending = [remaining.pop()]
            component = Graph()
            while pending:
                node = pending.pop()
                for triple in incident[node]:
                    component.add(triple)
                    for term in triple:
                        if isinstance(term, BNode) and term in remaining:
                            remaining.remove(term)
                            pending.append(term)
            components[to_isomorphic(component).graph_digest()] += 1
        return named, components

    return len(left) == len(right) and partition(left) == partition(right)


def split_values(value: str, *, keep_empty: bool = False) -> list[str]:
    """Decode exactly ' | ', without stripping meaningful literal whitespace."""
    if value == "":
        return [""] if keep_empty else []
    parts, current = [], []
    index = 0
    while index < len(value):
        if value[index] == "\\":
            index += 1
            if index == len(value) or value[index] not in "\\|":
                raise ValueError("Invalid CSV escape; escape backslashes as \\\\ and pipes as \\|.")
            current.append(value[index])
            index += 1
        elif value.startswith(SEPARATOR, index):
            parts.append("".join(current))
            current = []
            index += len(SEPARATOR)
        elif value[index] == "|":
            raise ValueError("Separate values with ' | '; escape literal pipes as \\|.")
        else:
            current.append(value[index])
            index += 1
    parts.append("".join(current))
    if not keep_empty and any(part == "" for part in parts):
        raise ValueError("Empty list entries are only allowed in definitionSource.")
    return parts


def _uri(value: str) -> URIRef:
    if not value or re.search(r'[\s<>"{}|\\^`]', value):
        raise ValueError(f"Expected an absolute URI, got {value!r}")
    parsed = urlsplit(value)
    if not re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", value) or not (parsed.netloc or parsed.path):
        raise ValueError(f"Expected an absolute URI, got {value!r}")
    if parsed.scheme in ("http", "https") and not parsed.netloc:
        raise ValueError(f"Invalid HTTP URI: {value!r}")
    return URIRef(value)


def _types(value: str) -> set[URIRef]:
    names = {name: uri for uri, name in TYPE_NAMES.items()}
    names.update({str(uri): uri for uri in TYPE_NAMES})
    try:
        types = {names[name] for name in split_values(value)}
    except KeyError as error:
        raise ValueError(f"Unsupported RDF type: {error.args[0]}") from error
    if SKOS.Concept not in types:
        raise ValueError("Every row must explicitly include skos:Concept in type.")
    if {SOSA.Procedure, SOSA.ObservableProperty} <= types:
        raise ValueError("A concept cannot be both a procedure and an observable property.")
    return types


def _header_key(value: str) -> str:
    return re.sub(r"[\s_]", "", value).casefold()


def read_rows(csv_path: Path) -> list[dict[str, str]]:
    aliases = {_header_key(column): column for column in COLUMNS}
    aliases.update({
        "sourcelink": "definitionSource",
        "sourcelinks": "definitionSource",
        "isprocedurefor": "property",
    })
    with Path(csv_path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        headers = reader.fieldnames or []
        unknown = [name for name in headers if _header_key(name) not in aliases]
        if unknown:
            raise ValueError(f"Unsupported CSV columns: {unknown}")
        mapped = [aliases[_header_key(name)] for name in headers]
        if len(mapped) != len(set(mapped)):
            raise ValueError("Duplicate CSV columns or aliases for the same column.")
        missing = set(COLUMNS) - set(mapped)
        if missing:
            raise ValueError(f"Missing CSV columns: {sorted(missing)}; regenerate using the notebook exporter.")
        rows = []
        for number, raw in enumerate(reader, start=2):
            if None in raw or any(value is None for value in raw.values()):
                raise ValueError(f"CSV row {number} has a different field count from the header.")
            rows.append({aliases[_header_key(name)]: raw[name] for name in headers})
    return rows


def graph_from_rows(rows: list[dict[str, str]], scheme_uri: str = SCHEME_URI) -> Graph:
    scheme = _uri(scheme_uri)
    graph = Graph()
    for prefix, ns in (("skos", SKOS), ("sosa", SOSA), ("dcterms", DCTERMS),
                       ("eusoilvoc", Namespace(scheme_uri + "#"))):
        graph.bind(prefix, ns)
    graph.add((scheme, RDF.type, SKOS.ConceptScheme))
    concepts = {}
    for number, row in enumerate(rows, start=2):
        if set(row) != set(COLUMNS):
            raise ValueError(f"Row {number} does not have the complete CSV schema.")
        concept = _uri(row["id"])
        if not str(concept).startswith(scheme_uri + "#"):
            raise ValueError(f"Concept is outside the local namespace: {concept}")
        if concept in concepts:
            raise ValueError(f"Duplicate concept id: {concept}")
        concepts[concept] = _types(row["type"])
        for typ in concepts[concept]:
            graph.add((concept, RDF.type, typ))
        graph.add((concept, SKOS.inScheme, scheme))
        if not row["prefLabel"].strip():
            raise ValueError(f"Missing prefLabel: {concept}")
        graph.add((concept, SKOS.prefLabel, Literal(row["prefLabel"], lang="en")))
        for label in split_values(row["altLabel"]):
            graph.add((concept, SKOS.altLabel, Literal(label, lang="en")))

        definitions = split_values(row["definition"])
        sources = split_values(row["definitionSource"], keep_empty=bool(definitions))
        if len(definitions) != len(sources):
            raise ValueError(f"Definition/source count mismatch for {concept}: {len(definitions)} vs {len(sources)}")
        for definition, source in zip(definitions, sources):
            if source:
                node = BNode()
                graph.add((concept, SKOS.definition, node))
                graph.add((node, RDF.value, Literal(definition, lang="en")))
                graph.add((node, DCTERMS.source, _uri(source)))
            else:
                graph.add((concept, SKOS.definition, Literal(definition, lang="en")))
        for column, predicate in URI_COLUMNS.items():
            for value in split_values(row[column]):
                graph.add((concept, predicate, _uri(value)))

    for predicate in (SKOS.broader, SKOS.narrower, SOSA.isProcedureFor):
        for subject, target in graph.subject_objects(predicate):
            if target not in concepts:
                raise ValueError(f"Unknown local target: {subject} {predicate} {target}")
    broader = set(graph.subject_objects(SKOS.broader))
    narrower = {(child, parent) for parent, child in graph.subject_objects(SKOS.narrower)}
    if broader != narrower:
        example = sorted(broader ^ narrower, key=str)[0]
        raise ValueError(f"Inconsistent broader/narrower declarations: {example}")
    parents = {concept: set(graph.objects(concept, SKOS.broader)) for concept in concepts}
    try:
        tuple(TopologicalSorter(parents).static_order())
    except CycleError as error:
        raise ValueError("Cycle in the SKOS hierarchy.") from error
    for child, parent in broader:
        if (SOSA.Procedure in concepts[child] and SOSA.ObservableProperty in concepts[parent]
                or SOSA.ObservableProperty in concepts[child] and SOSA.Procedure in concepts[parent]):
            raise ValueError("Use property, not broader/narrower, to connect procedures with observable properties.")
    for procedure, prop in list(graph.subject_objects(SOSA.isProcedureFor)):
        if SOSA.Procedure not in concepts[procedure] or SOSA.ObservableProperty not in concepts[prop]:
            raise ValueError(f"property requires a Procedure and an ObservableProperty: {procedure}, {prop}")
        graph.add((prop, SOSA.hasProcedure, procedure))
    for concept, types in concepts.items():
        if SOSA.Procedure not in types and not parents[concept]:
            graph.add((scheme, SKOS.hasTopConcept, concept))
            graph.add((concept, SKOS.topConceptOf, scheme))
    return graph


def build_graph_from_csv(csv_path: Path, scheme_uri: str = SCHEME_URI) -> tuple[Graph, dict[str, str]]:
    return graph_from_rows(read_rows(csv_path), scheme_uri), {}


def diff_graphs(
    g_expected: Graph,
    g_actual: Graph,
    limit: int = 25,
    canonicalize_bnodes: bool = True,
) -> tuple[list[tuple], list[tuple]]:
    if canonicalize_bnodes:
        iso_expected = to_isomorphic(g_expected)
        iso_actual = to_isomorphic(g_actual)
        _, in_expected, in_actual = graph_diff(iso_expected, iso_actual)
        missing = sorted(in_expected, key=lambda t: (str(t[0]), str(t[1]), str(t[2])))
        extra = sorted(in_actual, key=lambda t: (str(t[0]), str(t[1]), str(t[2])))
    else:
        expected_triples = set(g_expected)
        actual_triples = set(g_actual)
        missing = sorted(expected_triples - actual_triples, key=lambda t: (str(t[0]), str(t[1]), str(t[2])))
        extra = sorted(actual_triples - expected_triples, key=lambda t: (str(t[0]), str(t[1]), str(t[2])))
    return missing[:limit], extra[:limit]


def find_literal_lexical_differences(
    g_expected: Graph,
    g_actual: Graph,
    predicates: set[URIRef],
    limit: int = 10,
) -> list[tuple[URIRef, URIRef, list[Literal], list[Literal]]]:
    """Return (s, p, expected_literals, actual_literals) where both graphs have literals for (s,p) but they differ."""
    def lit_map(g: Graph) -> dict[tuple[URIRef, URIRef], set[Literal]]:
        out: dict[tuple[URIRef, URIRef], set[Literal]] = {}
        for s, p, o in g:
            if p not in predicates or not isinstance(o, Literal):
                continue
            out.setdefault((s, p), set()).add(o)
        return out

    m_expected = lit_map(g_expected)
    m_actual = lit_map(g_actual)

    diffs: list[tuple[URIRef, URIRef, list[Literal], list[Literal]]] = []
    for key in sorted(set(m_expected.keys()) & set(m_actual.keys()), key=lambda k: (str(k[0]), str(k[1]))):
        expected_set = m_expected[key]
        actual_set = m_actual[key]
        if expected_set != actual_set:
            s, p = key
            diffs.append(
                (
                    s,
                    p,
                    sorted(expected_set, key=lambda l: l.n3(g_expected.namespace_manager)),
                    sorted(actual_set, key=lambda l: l.n3(g_actual.namespace_manager)),
                )
            )
            if len(diffs) >= limit:
                break

    return diffs


def top_concepts_in_scheme(g: Graph, scheme_uri: str) -> set[URIRef]:
    scheme = URIRef(scheme_uri)
    return set(o for _, _, o in g.triples((scheme, SKOS.hasTopConcept, None)))


def close_topconcept_inverses(g: Graph, scheme_uri: str) -> None:
    """Ensure both skos:hasTopConcept and skos:topConceptOf are present for the given scheme."""
    scheme = URIRef(scheme_uri)
    for tc in list(g.objects(scheme, SKOS.hasTopConcept)):
        g.add((tc, SKOS.topConceptOf, scheme))
    for tc in list(g.subjects(SKOS.topConceptOf, scheme)):
        g.add((scheme, SKOS.hasTopConcept, tc))


def main() -> int:
    parser = argparse.ArgumentParser(description="Restore SoilVoc.ttl from the lossless SoilVoc CSV profile")
    parser.add_argument("--csv", default=str(REPO_ROOT / "SoilVoc_concepts.csv"), help="Input CSV path")
    parser.add_argument("--out", default=str(REPO_ROOT / "SoilVoc_restored.ttl"), help="Output TTL path")
    parser.add_argument("--scheme", default=EUSOILVOC_SCHEME_URI, help="ConceptScheme URI")
    parser.add_argument("--compare", default=str(REPO_ROOT / "SoilVoc.ttl"), help="TTL reference for strict isomorphism")
    parser.add_argument("--literal-diff-limit", type=int, default=10)
    parser.add_argument("--raw-bnode-diff", action="store_true")
    # Retain old CLI spellings, but comparisons now always include every triple.
    for option in ("--include-related", "--include-topconceptof", "--include-equivalentto"):
        parser.add_argument(option, action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()

    csv_path = Path(args.csv)
    out_path = Path(args.out)
    compare_path = Path(args.compare)
    if out_path.resolve() == compare_path.resolve():
        parser.error("--out must differ from --compare; do not overwrite the reference vocabulary")
    try:
        expected = Graph().parse(compare_path, format="turtle")
        restored, _ = build_graph_from_csv(csv_path, args.scheme)
    except (ValueError, OSError) as error:
        parser.error(str(error))

    restored.serialize(destination=out_path, format="turtle")
    # Compare the serialized artifact, not only the graph held before writing.
    actual = Graph().parse(out_path, format="turtle")
    same = graphs_isomorphic(expected, actual)
    print(f"Wrote restored TTL: {out_path}")
    print(f"Triples: original={len(expected)}, restored={len(actual)}")
    for typ in (SKOS.Concept, SOSA.ObservableProperty, SOSA.Procedure):
        print(f"{typ}: {len(set(actual.subjects(RDF.type, typ)))}")
    print(f"Graph isomorphic to {compare_path} (all triples): {same}")

    if not same:
        missing, extra = diff_graphs(
            expected, actual, canonicalize_bnodes=not args.raw_bnode_diff,
        )
        for title, triples in (("Missing triples", missing), ("Extra triples", extra)):
            print(f"\n{title} (up to 25):")
            for s, p, o in triples:
                print(f"- {s.n3()} {p.n3()} {o.n3()}")
        differences = find_literal_lexical_differences(
            expected, actual, {SKOS.prefLabel, SKOS.altLabel, RDF.value, SKOS.definition},
            limit=max(0, args.literal_diff_limit),
        )
        for subject, predicate, before, after in differences:
            print(f"Literal difference: {subject} {predicate}: {before!r} -> {after!r}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
