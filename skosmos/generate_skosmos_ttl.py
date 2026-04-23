"""Generate the Skosmos display copy of SoilVoc.

The source vocabulary keeps definition provenance in blank nodes using
rdf:value. For legacy inputs, this script still rewrites definition blank-node
schema:text values to rdf:value for the local Skosmos deployment.

Skosmos hierarchy navigation is configured to use one display-only hierarchy
predicate. The generated copy preserves the semantic SKOS and SOSA links, then
adds eusoilvoc:skosmosHierarchyParent triples for Skosmos sidebar traversal.
It also embeds the local SoilVoc ontology labels and property/class declarations
so Fuseki only needs one generated Turtle file.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from rdflib import Graph, RDF, Namespace, URIRef


SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")
SOSA = Namespace("http://www.w3.org/ns/sosa/")
EUSOILVOC = Namespace("https://w3id.org/eusoilvoc#")
SCHEMA_TEXT = URIRef("https://schema.org/text")
SKOSMOS_HIERARCHY_PARENT = EUSOILVOC.skosmosHierarchyParent
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
DEFAULT_SOURCE = REPO_ROOT / "SoilVoc.ttl"
DEFAULT_OUTPUT = SCRIPT_DIR / "SoilVoc_skosmos.ttl"
DEFAULT_ONTOLOGY = SCRIPT_DIR / "soilvoc_ontology.ttl"


def rewrite_legacy_definition_text(graph: Graph) -> int:
    changed = 0
    for _, _, definition_node in list(graph.triples((None, SKOS.definition, None))):
        for text_value in list(graph.objects(definition_node, SCHEMA_TEXT)):
            graph.add((definition_node, RDF.value, text_value))
            graph.remove((definition_node, SCHEMA_TEXT, text_value))
            changed += 1
    return changed


def add_skosmos_hierarchy_projection(graph: Graph) -> int:
    added = 0
    hierarchy_sources = [
        list(graph.subject_objects(SKOS.broader)),
        list(graph.subject_objects(SOSA.isProcedureFor)),
    ]

    for child_parent_pairs in hierarchy_sources:
        for child, parent in child_parent_pairs:
            if not isinstance(child, URIRef) or not isinstance(parent, URIRef):
                continue

            triple = (child, SKOSMOS_HIERARCHY_PARENT, parent)
            if triple not in graph:
                graph.add(triple)
                added += 1

    return added


def add_hierarchy_closure(graph: Graph) -> int:
    parents_by_child: dict[URIRef, set[URIRef]] = {}
    for child, parent in graph.subject_objects(SKOS.broader):
        if isinstance(child, URIRef) and isinstance(parent, URIRef):
            parents_by_child.setdefault(child, set()).add(parent)

    added = 0
    for child in parents_by_child:
        pending = list(parents_by_child[child])
        seen: set[URIRef] = set()

        while pending:
            parent = pending.pop()
            if parent in seen:
                continue

            seen.add(parent)
            broader_triple = (child, SKOS.broaderTransitive, parent)
            narrower_triple = (parent, SKOS.narrowerTransitive, child)
            if broader_triple not in graph:
                graph.add(broader_triple)
                added += 1
            if narrower_triple not in graph:
                graph.add(narrower_triple)
                added += 1
            pending.extend(parents_by_child.get(parent, set()) - seen)

    return added


def merge_ontology(graph: Graph, ontology: Path) -> int:
    before = len(graph)
    graph.parse(ontology, format="turtle")
    return len(graph) - before


def generate_skosmos_ttl(
    source: Path,
    output: Path,
    ontology: Path | None = DEFAULT_ONTOLOGY,
) -> tuple[int, int, int, int]:
    graph = Graph()
    graph.parse(source, format="turtle")

    legacy_definition_rewrites = rewrite_legacy_definition_text(graph)
    skosmos_hierarchy_projection_triples = add_skosmos_hierarchy_projection(graph)
    hierarchy_closure_triples = add_hierarchy_closure(graph)
    ontology_triples = merge_ontology(graph, ontology) if ontology is not None else 0

    output.parent.mkdir(parents=True, exist_ok=True)
    graph.serialize(destination=output, format="turtle", encoding="utf-8")
    return (
        legacy_definition_rewrites,
        skosmos_hierarchy_projection_triples,
        hierarchy_closure_triples,
        ontology_triples,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate skosmos/SoilVoc_skosmos.ttl from SoilVoc.ttl."
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE,
        help="Source SoilVoc Turtle file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Generated Turtle file for the local Skosmos deployment.",
    )
    parser.add_argument(
        "--ontology",
        type=Path,
        default=DEFAULT_ONTOLOGY,
        help="SoilVoc ontology Turtle file to embed into the generated Skosmos Turtle file.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    (
        legacy_definition_rewrites,
        skosmos_hierarchy_projection_triples,
        hierarchy_closure_triples,
        ontology_triples,
    ) = generate_skosmos_ttl(args.source, args.output, args.ontology)
    print(
        f"Wrote {args.output} with {legacy_definition_rewrites} legacy definition text rewrites, "
        f"{skosmos_hierarchy_projection_triples} Skosmos hierarchy projection triples, "
        f"added {hierarchy_closure_triples} SKOS hierarchy closure triples, "
        f"and embedded {ontology_triples} ontology triples."
    )


if __name__ == "__main__":
    main()
