"""Generate the Skosmos display copy of SoilVoc.

The source vocabulary keeps definition provenance in blank nodes using
schema:text. Skosmos can display resource-valued definitions when the text is
available as rdf:value, so this script rewrites only those definition nodes for
the local Skosmos deployment.

Skosmos hierarchy navigation is SKOS-oriented. The generated copy projects SOSA
procedure links into SKOS broader/narrower view triples and adds closure triples
without changing the canonical SoilVoc.ttl source.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from rdflib import Graph, RDF, Namespace, URIRef


SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")
SOSA = Namespace("http://www.w3.org/ns/sosa/")
SCHEMA_TEXT = URIRef("https://schema.org/text")


def rewrite_definition_text(graph: Graph) -> int:
    changed = 0
    for _, _, definition_node in list(graph.triples((None, SKOS.definition, None))):
        for text_value in list(graph.objects(definition_node, SCHEMA_TEXT)):
            graph.add((definition_node, RDF.value, text_value))
            graph.remove((definition_node, SCHEMA_TEXT, text_value))
            changed += 1
    return changed


def project_procedure_hierarchy(graph: Graph) -> int:
    added = 0
    for procedure, observable_property in graph.subject_objects(SOSA.isProcedureFor):
        if not isinstance(procedure, URIRef) or not isinstance(observable_property, URIRef):
            continue

        broader_triple = (procedure, SKOS.broader, observable_property)
        narrower_triple = (observable_property, SKOS.narrower, procedure)
        if broader_triple not in graph:
            graph.add(broader_triple)
            added += 1
        if narrower_triple not in graph:
            graph.add(narrower_triple)
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


def generate_skosmos_ttl(source: Path, output: Path) -> tuple[int, int, int]:
    graph = Graph()
    graph.parse(source, format="turtle")

    definition_rewrites = rewrite_definition_text(graph)
    procedure_hierarchy_triples = project_procedure_hierarchy(graph)
    hierarchy_closure_triples = add_hierarchy_closure(graph)

    output.parent.mkdir(parents=True, exist_ok=True)
    graph.serialize(destination=output, format="turtle", encoding="utf-8")
    return definition_rewrites, procedure_hierarchy_triples, hierarchy_closure_triples


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate skosmos/SoilVoc_skosmos.ttl from SoilVoc.ttl."
    )
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    parser.add_argument(
        "--source",
        type=Path,
        default=repo_root / "SoilVoc.ttl",
        help="Source SoilVoc Turtle file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=script_dir / "SoilVoc_skosmos.ttl",
        help="Generated Turtle file for the local Skosmos deployment.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    (
        definition_rewrites,
        procedure_hierarchy_triples,
        hierarchy_closure_triples,
    ) = generate_skosmos_ttl(args.source, args.output)
    print(
        f"Wrote {args.output} with {definition_rewrites} definition text rewrites, "
        f"{procedure_hierarchy_triples} procedure hierarchy projection triples, "
        f"and {hierarchy_closure_triples} hierarchy closure triples."
    )


if __name__ == "__main__":
    main()
