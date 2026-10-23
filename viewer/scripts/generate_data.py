"""Prepare the static viewer's RDF snapshot from the augmented vocabulary.

Preserve sourced definitions, embed display ontology labels, and retain the
existing display hierarchy projection and SKOS closure for RDF compatibility.
No Skosmos configuration, plugins, containers or triplestore are required.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from rdflib import Graph, Namespace, RDF, URIRef


SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")
SOSA = Namespace("http://www.w3.org/ns/sosa/")
EUSOILVOC = Namespace("https://w3id.org/eusoilvoc#")
SCHEMA_TEXT = URIRef("https://schema.org/text")
# Keep the existing RDF predicate identity; it is not a deployment dependency.
DISPLAY_PARENT = EUSOILVOC.skosmosHierarchyParent
VIEWER_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = VIEWER_DIR.parent
DEFAULT_SOURCE = REPO_ROOT / "SoilVoc_augmented.ttl"
DEFAULT_OUTPUT = VIEWER_DIR / "data" / "SoilVoc.ttl"
DEFAULT_ONTOLOGY = VIEWER_DIR / "data" / "ontology.ttl"


def rewrite_legacy_definition_text(graph: Graph) -> int:
    changed = 0
    for _, _, definition_node in list(graph.triples((None, SKOS.definition, None))):
        for text_value in list(graph.objects(definition_node, SCHEMA_TEXT)):
            graph.add((definition_node, RDF.value, text_value))
            graph.remove((definition_node, SCHEMA_TEXT, text_value))
            changed += 1
    return changed


def add_display_hierarchy(graph: Graph) -> int:
    before = len(graph)
    for predicate in (SKOS.broader, SOSA.isProcedureFor):
        for child, parent in list(graph.subject_objects(predicate)):
            if isinstance(child, URIRef) and isinstance(parent, URIRef):
                graph.add((child, DISPLAY_PARENT, parent))
    return len(graph) - before


def add_hierarchy_closure(graph: Graph) -> int:
    parents_by_child: dict[URIRef, set[URIRef]] = {}
    for child, parent in graph.subject_objects(SKOS.broader):
        if isinstance(child, URIRef) and isinstance(parent, URIRef):
            parents_by_child.setdefault(child, set()).add(parent)

    before = len(graph)
    for child, parents in parents_by_child.items():
        pending, seen = list(parents), set()
        while pending:
            parent = pending.pop()
            if parent in seen:
                continue
            seen.add(parent)
            graph.add((child, SKOS.broaderTransitive, parent))
            graph.add((parent, SKOS.narrowerTransitive, child))
            pending.extend(parents_by_child.get(parent, set()) - seen)
    return len(graph) - before


def generate_data(source: Path, output: Path, ontology: Path) -> tuple[int, int, int, int]:
    graph = Graph().parse(source, format="turtle")
    rewritten = rewrite_legacy_definition_text(graph)
    hierarchy = add_display_hierarchy(graph)
    closure = add_hierarchy_closure(graph)
    before = len(graph)
    graph.parse(ontology, format="turtle")
    ontology_triples = len(graph) - before
    output.parent.mkdir(parents=True, exist_ok=True)
    graph.serialize(destination=output, format="turtle", encoding="utf-8")
    return rewritten, hierarchy, closure, ontology_triples


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate viewer/data/SoilVoc.ttl from SoilVoc_augmented.ttl."
    )
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE, help="Source vocabulary Turtle file.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Generated viewer Turtle file.")
    parser.add_argument("--ontology", type=Path, default=DEFAULT_ONTOLOGY, help="Display ontology Turtle file to embed.")
    args = parser.parse_args()
    rewritten, hierarchy, closure, ontology = generate_data(args.source, args.output, args.ontology)
    print(
        f"Wrote {args.output}: {rewritten} legacy definition text rewrites, "
        f"{hierarchy} display hierarchy triples, {closure} SKOS closure triples, "
        f"and {ontology} ontology triples."
    )


if __name__ == "__main__":
    main()
