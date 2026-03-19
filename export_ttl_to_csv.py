"""
export_ttl_to_csv.py — Export SoilVoc.ttl to SoilVoc_concepts.csv

Usage:
    python export_ttl_to_csv.py
    python export_ttl_to_csv.py --ttl SoilVoc.ttl --out SoilVoc_concepts.csv
"""

import argparse
from collections import defaultdict
from pathlib import Path

import pandas as pd
from rdflib import Graph, URIRef, BNode
from rdflib.namespace import SKOS, DCTERMS, RDF, SDO, SOSA

HAS_PROCEDURE = URIRef(str(SOSA) + "hasProcedure")
IS_PROCEDURE_OF = URIRef(str(SOSA) + "isProcedureFor")

COL_ID = "ID"
COL_PREF = "prefLabel"
COL_ALT = "altLabel"
COL_DEF = "definition"
COL_BROADER = "broader"
COL_IS_PROCEDURE_FOR = "isProcedureFor"
COL_EXACT = "exactMatch"
COL_CLOSE = "closeMatch"
COL_SRC = "source link"


def export_ttl_to_csv(ttl_path: str, output_path: str) -> int:
    """
    Parse a SoilVoc TTL file and write all concepts to a CSV.
    Returns the number of concepts exported.
    """
    scheme_uri = URIRef("https://soilwise-he.github.io/soil-vocabs")

    g = Graph()
    g.parse(ttl_path, format="turtle")

    # Build broader hierarchy map
    broader_map = defaultdict(set)
    for s, _, o in g.triples((None, SKOS.broader, None)):
        broader_map[s].add(o)

    # Build procedure relationship map
    procedure_for_map = defaultdict(set)
    for s, _, o in g.triples((None, HAS_PROCEDURE, None)):
        procedure_for_map[o].add(s)
    for s, _, o in g.triples((None, IS_PROCEDURE_OF, None)):
        procedure_for_map[s].add(o)

    def get_pref_label(concept):
        for label in g.objects(concept, SKOS.prefLabel):
            if getattr(label, "language", None) == "en":
                return str(label)
        for label in g.objects(concept, SKOS.prefLabel):
            return str(label)
        uri = str(concept)
        return uri.split("#")[-1] if "#" in uri else uri.split("/")[-1]

    def get_alt_labels(concept):
        labels = list(g.objects(concept, SKOS.altLabel))
        if not labels:
            return ""
        en = [str(l) for l in labels if getattr(l, "language", None) == "en"]
        chosen = en if en else [str(l) for l in labels]
        seen, out = set(), []
        for l in chosen:
            if l not in seen:
                seen.add(l)
                out.append(l)
        return " | ".join(out)

    def _pick_text_literal(literals):
        if not literals:
            return None
        for lit in literals:
            if getattr(lit, "language", None) == "en":
                return lit
        return literals[0]

    def _pick_source_value(values):
        if not values:
            return None
        for v in values:
            if isinstance(v, URIRef):
                return v
        return values[0]

    def get_definitions_and_sources(concept):
        pairs = []
        for defn in g.objects(concept, SKOS.definition):
            if isinstance(defn, BNode):
                text_node = _pick_text_literal(list(g.objects(defn, SDO.text)))
                if text_node is None:
                    text_node = _pick_text_literal(list(g.objects(defn, RDF.value)))
                text = str(text_node) if text_node is not None else ""
                source_node = _pick_source_value(list(g.objects(defn, DCTERMS.source)))
                source = str(source_node) if source_node is not None else ""
                is_en = getattr(text_node, "language", None) == "en" if text_node is not None else False
                pairs.append((text, source, is_en))
            else:
                text = str(defn)
                is_en = getattr(defn, "language", None) == "en"
                pairs.append((text, "", is_en))
        if not pairs:
            return "", ""
        ordered = sorted(enumerate(pairs), key=lambda x: (0 if x[1][2] else 1, x[0]))
        return " | ".join(p[1][0] for p in ordered), " | ".join(p[1][1] for p in ordered)

    def get_match_uris(concept, predicate):
        seen, out = set(), []
        for o in g.objects(concept, predicate):
            if isinstance(o, URIRef) and str(o) not in seen:
                seen.add(str(o))
                out.append(str(o))
        return " | ".join(out)

    def get_immediate_broader_terms(concept):
        broaders = broader_map.get(concept, set())
        if not broaders:
            return ""
        labels = sorted(set(get_pref_label(b) for b in broaders), key=str.casefold)
        return " | ".join(labels)

    def get_is_procedure_for_terms(concept):
        related = procedure_for_map.get(concept, set())
        if not related:
            return ""
        labels = sorted(set(get_pref_label(c) for c in related), key=str.casefold)
        return " | ".join(labels)

    # Collect all concepts
    all_concepts = set()
    for s in g.subjects(RDF.type, SKOS.Concept):
        if (s, SKOS.inScheme, scheme_uri) in g:
            all_concepts.add(s)
    for proc in g.objects(None, HAS_PROCEDURE):
        if isinstance(proc, URIRef):
            all_concepts.add(proc)
    for proc in g.subjects(IS_PROCEDURE_OF, None):
        if isinstance(proc, URIRef):
            all_concepts.add(proc)

    csv_data = []
    for concept in all_concepts:
        def_text, src_text = get_definitions_and_sources(concept)
        csv_data.append({
            COL_ID: str(concept),
            COL_PREF: get_pref_label(concept),
            COL_ALT: get_alt_labels(concept),
            COL_DEF: def_text,
            COL_BROADER: get_immediate_broader_terms(concept),
            COL_IS_PROCEDURE_FOR: get_is_procedure_for_terms(concept),
            COL_EXACT: get_match_uris(concept, SKOS.exactMatch),
            COL_CLOSE: get_match_uris(concept, SKOS.closeMatch),
            COL_SRC: src_text,
        })

    df = pd.DataFrame(csv_data, columns=[
        COL_ID, COL_PREF, COL_ALT, COL_DEF, COL_BROADER,
        COL_IS_PROCEDURE_FOR, COL_EXACT, COL_CLOSE, COL_SRC,
    ])
    df = df.sort_values(COL_PREF, key=lambda x: x.str.lower()).reset_index(drop=True)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")

    procedure_count = sum(1 for c in all_concepts if c in procedure_for_map)
    print(f"CSV saved to: {output_path}")
    print(f"Total concepts exported: {len(df)}")
    print(f"Concepts referenced as procedures: {procedure_count}")
    return len(df)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export SoilVoc TTL to CSV")
    parser.add_argument("--ttl", default="SoilVoc.ttl", help="Input TTL file (default: SoilVoc.ttl)")
    parser.add_argument("--out", default="SoilVoc_concepts.csv", help="Output CSV file (default: SoilVoc_concepts.csv)")
    args = parser.parse_args()

    if not Path(args.ttl).exists():
        raise FileNotFoundError(f"TTL file not found: {args.ttl}")

    export_ttl_to_csv(args.ttl, args.out)
