import argparse
import csv
import re
from collections import defaultdict
from pathlib import Path

from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import RDF, SKOS
from rdflib.compare import isomorphic


COL_ID = "ID"
COL_PREF = "prefLabel"
COL_ALT = "altLabel"
COL_DEF = "definition"
COL_BROADER = "broader"
COL_EXACT = "exactMatch"
COL_CLOSE = "closeMatch"


COLUMN_ALIASES: dict[str, list[str]] = {
    COL_ID: [
        "ID",
        "ID (concepts' URIs)",
        "concept_uri",
        "concept uri",
        "uri",
    ],
    COL_PREF: ["prefLabel", "preflabel", "pref label", "pref_label"],
    COL_ALT: ["altLabel", "altlabel", "alt label", "alt_label"],
    COL_DEF: ["definition", "Definition"],
    COL_BROADER: [
        "broader",
        "broader term",
        "broader term (immediate, semicolon-separated, use prefLabel)",
    ],
    COL_EXACT: [
        "exactMatch",
        "exact match",
        "exact match (skos:exactMatch, semicolon-separated, use full URIs)",
    ],
    COL_CLOSE: [
        "closeMatch",
        "close match",
        "close match (skos:closeMatch, semicolon-separated, use full URIs)",
    ],
}


def _norm_col(name: str) -> str:
    return re.sub(r"\s+", "", str(name)).casefold()


def canonicalize_fieldnames(fieldnames: list[str] | None) -> dict[str, str]:
    """Return a mapping from actual CSV header -> canonical header."""
    if not fieldnames:
        raise ValueError("CSV has no header row")

    norm_to_actual: dict[str, str] = {_norm_col(c): c for c in fieldnames}
    rename_map: dict[str, str] = {}

    missing: list[str] = []
    for canonical, aliases in COLUMN_ALIASES.items():
        found_actual = None
        for candidate in aliases:
            actual = norm_to_actual.get(_norm_col(candidate))
            if actual is not None:
                found_actual = actual
                break
        if found_actual is None:
            missing.append(canonical)
        else:
            rename_map[found_actual] = canonical

    if missing:
        raise ValueError(
            "CSV missing required columns (after alias matching): "
            f"{missing}. Existing columns: {fieldnames}"
        )

    return rename_map


def read_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rename_map = canonicalize_fieldnames(reader.fieldnames)

        rows: list[dict[str, str]] = []
        for raw in reader:
            row: dict[str, str] = {k: "" for k in COLUMN_ALIASES.keys()}
            for actual_key, canonical_key in rename_map.items():
                row[canonical_key] = str(raw.get(actual_key, "") or "").strip()
            rows.append(row)
        return rows


def split_semicolon(value: str) -> list[str]:
    if value is None:
        return []
    value = str(value).strip()
    if not value or value.lower() == "nan":
        return []
    parts = [p.strip() for p in value.split(";")]
    return [p for p in parts if p]


def _graph_without_predicates(g: Graph, predicates: set[URIRef]) -> Graph:
    if not predicates:
        return g
    g2 = Graph()
    g2.namespace_manager = g.namespace_manager
    for s, p, o in g:
        if p in predicates:
            continue
        g2.add((s, p, o))
    return g2


def build_graph_from_csv(csv_path: Path, scheme_uri: str) -> tuple[Graph, dict[str, str]]:
    rows = read_rows(csv_path)

    PROCEDURE_EXACTMATCH_PREFIXES = (
        "http://w3id.org/glosis/model/procedure/",
        "http://w3id.org/glosis/model/procedure",
    )

    # Determine which concepts are procedures.
    # Rule: if any skos:exactMatch URI starts with the GLOSIS procedure namespace, it's a procedure.
    procedure_concept_uris: set[str] = set()
    for row in rows:
        concept_uri = str(row[COL_ID]).strip()
        if not concept_uri:
            continue
        exacts = split_semicolon(str(row[COL_EXACT]))
        if any(u.startswith(PROCEDURE_EXACTMATCH_PREFIXES) for u in exacts):
            procedure_concept_uris.add(concept_uri)

    # Build lookups for mapping broader prefLabels -> URIs
    uri_to_pref: dict[str, str] = {}
    pref_to_uris: defaultdict[str, list[str]] = defaultdict(list)
    for row in rows:
        uri = str(row[COL_ID]).strip()
        pref = str(row[COL_PREF]).strip()
        if not uri:
            continue
        uri_to_pref[uri] = pref
        if pref:
            pref_to_uris[pref.casefold()].append(uri)

    warnings: dict[str, str] = {}

    def resolve_pref_to_uri(pref_label: str) -> str | None:
        key = pref_label.casefold()
        uris = pref_to_uris.get(key, [])
        if not uris:
            warnings.setdefault("unresolved_broader_labels", "")
            warnings["unresolved_broader_labels"] += f"- {pref_label}\n"
            return None
        if len(uris) > 1:
            warnings.setdefault("ambiguous_broader_labels", "")
            warnings["ambiguous_broader_labels"] += (
                f"- {pref_label} -> {len(uris)} URIs; using lexicographically smallest\n"
            )
            return sorted(uris)[0]
        return uris[0]

    g = Graph()

    SHE = Namespace("https://soilwise-he.github.io/soil-health#")
    SCHEME_URI = URIRef(scheme_uri)

    g.bind("skos", SKOS)
    g.bind("she", SHE)

    # Create concept scheme (CSV doesn't carry scheme metadata beyond URI)
    g.add((SCHEME_URI, RDF.type, SKOS.ConceptScheme))

    # Create concepts + literals + match links
    concepts: list[URIRef] = []
    for row in rows:
        concept_uri = str(row[COL_ID]).strip()
        if not concept_uri:
            continue
        concept = URIRef(concept_uri)
        concepts.append(concept)

        is_procedure_concept = concept_uri in procedure_concept_uris

        g.add((concept, RDF.type, SKOS.Concept))
        g.add((concept, SKOS.inScheme, SCHEME_URI))

        pref = str(row[COL_PREF]).strip()
        if pref:
            g.add((concept, SKOS.prefLabel, Literal(pref, lang="en")))

        for alt in split_semicolon(str(row[COL_ALT])):
            g.add((concept, SKOS.altLabel, Literal(alt, lang="en")))

        definition = str(row[COL_DEF]).strip()
        if definition:
            # In the current SoilVoc.ttl, procedure definitions are typically untagged, while
            # non-procedure concept definitions are typically @en.
            if is_procedure_concept:
                g.add((concept, SKOS.definition, Literal(definition)))
            else:
                g.add((concept, SKOS.definition, Literal(definition, lang="en")))

        for uri in split_semicolon(str(row[COL_EXACT])):
            g.add((concept, SKOS.exactMatch, URIRef(uri)))

        for uri in split_semicolon(str(row[COL_CLOSE])):
            g.add((concept, SKOS.closeMatch, URIRef(uri)))

    # Add broader links using prefLabel -> URI mapping.
    # For procedures:
    # - broader == another procedure => skos:broader/skos:narrower
    # - broader == non-procedure concept => she:isProcedureOf + inverse she:hasProcedure
    for row in rows:
        concept_uri = str(row[COL_ID]).strip()
        if not concept_uri:
            continue
        concept = URIRef(concept_uri)

        is_procedure_concept = concept_uri in procedure_concept_uris

        for broader_label in split_semicolon(str(row[COL_BROADER])):
            broader_uri = resolve_pref_to_uri(broader_label)
            if broader_uri:
                broader_concept = URIRef(broader_uri)
                if is_procedure_concept:
                    broader_is_procedure = broader_uri in procedure_concept_uris
                    if broader_is_procedure:
                        g.add((concept, SKOS.broader, broader_concept))
                    else:
                        g.add((concept, SHE.isProcedureOf, broader_concept))
                        g.add((broader_concept, SHE.hasProcedure, concept))
                else:
                    g.add((concept, SKOS.broader, broader_concept))

    # Add inferred skos:narrower (original TTL contains these)
    for child, _, parent in g.triples((None, SKOS.broader, None)):
        g.add((parent, SKOS.narrower, child))

    # Infer top concepts: all non-procedure concepts with no skos:broader.
    # For this project we treat: blank CSV "broader" => top concept.
    # (We only record skos:broader in CSV; procedures are excluded.)
    top_concept_uris_from_csv: set[str] = set()
    for row in rows:
        concept_uri = str(row[COL_ID]).strip()
        if not concept_uri or concept_uri in procedure_concept_uris:
            continue
        broader_raw = str(row[COL_BROADER]).strip()
        if not broader_raw:
            top_concept_uris_from_csv.add(concept_uri)

    for tc_uri in sorted(top_concept_uris_from_csv):
        tc = URIRef(tc_uri)
        g.add((SCHEME_URI, SKOS.hasTopConcept, tc))
        g.add((tc, SKOS.topConceptOf, SCHEME_URI))

    return g, warnings


def diff_graphs(g_expected: Graph, g_actual: Graph, limit: int = 25) -> tuple[list[tuple], list[tuple]]:
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Restore SoilVoc.ttl from SoilVoc_concepts.csv")
    parser.add_argument("--csv", default="SoilVoc_concepts.csv", help="Input CSV path")
    parser.add_argument("--out", default="SoilVoc_restored.ttl", help="Output TTL path")
    parser.add_argument(
        "--scheme",
        default="https://soilwise-he.github.io/soil-health",
        help="ConceptScheme URI",
    )
    parser.add_argument(
        "--compare",
        default="SoilVoc.ttl",
        help="Existing TTL to compare against",
    )
    parser.add_argument(
        "--include-related",
        action="store_true",
        help="Include skos:related in comparison (default: ignore skos:related)",
    )
    parser.add_argument(
        "--include-topconceptof",
        action="store_true",
        help="Include skos:topConceptOf in comparison (default: ignore skos:topConceptOf)",
    )
    parser.add_argument(
        "--include-equivalentto",
        action="store_true",
        help="Include semscience:equivalentTo in comparison (default: ignore it)",
    )
    parser.add_argument(
        "--literal-diff-limit",
        type=int,
        default=10,
        help="How many literal lexical-form mismatches to print",
    )
    args = parser.parse_args()

    csv_path = Path(args.csv)
    out_path = Path(args.out)
    compare_path = Path(args.compare)

    restored, warnings = build_graph_from_csv(csv_path, args.scheme)
    restored.serialize(destination=str(out_path), format="turtle")
    print(f"Wrote restored TTL: {out_path}")

    if warnings.get("ambiguous_broader_labels"):
        print("\nWARNING: Ambiguous broader labels detected:")
        print(warnings["ambiguous_broader_labels"].rstrip())
    if warnings.get("unresolved_broader_labels"):
        print("\nWARNING: Unresolved broader labels (no matching prefLabel in CSV):")
        print(warnings["unresolved_broader_labels"].rstrip())

    # Compare with existing TTL if present
    if compare_path.exists():
        g_existing = Graph()
        g_existing.parse(str(compare_path), format="turtle")

        SEMSCIENCE_EQUIVALENT_TO = URIRef("http://semanticscience.org/resource/equivalentTo")

        ignored_predicates: set[URIRef] = set()
        if not args.include_related:
            ignored_predicates.add(SKOS.related)
        if not args.include_equivalentto:
            ignored_predicates.add(SEMSCIENCE_EQUIVALENT_TO)

        g_existing_cmp = _graph_without_predicates(g_existing, ignored_predicates)
        restored_cmp = _graph_without_predicates(restored, ignored_predicates)

        # If requested, compare including skos:topConceptOf, but normalize both graphs so
        # they are closed under the inverse relationship hasTopConcept <-> topConceptOf.
        if args.include_topconceptof:
            close_topconcept_inverses(g_existing_cmp, args.scheme)
            close_topconcept_inverses(restored_cmp, args.scheme)

        same_raw = isomorphic(restored, g_existing)
        same_cmp = isomorphic(restored_cmp, g_existing_cmp)
        if ignored_predicates:
            print(f"\nGraph isomorphic to {compare_path} (raw): {same_raw}")
            print(f"Graph isomorphic to {compare_path} (ignoring {', '.join(sorted(str(p) for p in ignored_predicates))}): {same_cmp}")
        else:
            print(f"\nGraph isomorphic to {compare_path}: {same_raw}")

        existing_top = top_concepts_in_scheme(g_existing, args.scheme)
        restored_top = top_concepts_in_scheme(restored, args.scheme)
        print(f"\nTop concepts in existing TTL: {len(existing_top)}")
        print(f"Top concepts in restored TTL: {len(restored_top)}")

        if not same_cmp:
            missing, extra = diff_graphs(g_existing_cmp, restored_cmp, limit=25)
            print(f"\nTriples missing from restored (showing up to {len(missing)}):")
            for s, p, o in missing:
                print(f"- {s.n3(restored.namespace_manager)} {p.n3(restored.namespace_manager)} {o.n3(restored.namespace_manager)}")

            print(f"\nTriples extra in restored (showing up to {len(extra)}):")
            for s, p, o in extra:
                print(f"- {s.n3(restored.namespace_manager)} {p.n3(restored.namespace_manager)} {o.n3(restored.namespace_manager)}")

            # Targeted literal lexical-form differences (what the user can fix in CSV)
            lit_preds = {SKOS.prefLabel, SKOS.altLabel, SKOS.definition}
            literal_diffs = find_literal_lexical_differences(
                g_existing_cmp,
                restored_cmp,
                predicates=lit_preds,
                limit=max(0, int(args.literal_diff_limit)),
            )
            if literal_diffs:
                print(f"\nExamples of literal lexical-form differences (up to {len(literal_diffs)}):")
                for s, p, expected_lits, actual_lits in literal_diffs:
                    print(f"- Subject: {s}")
                    print(f"  Predicate: {p}")
                    print("  Existing literals:")
                    for lit in expected_lits:
                        print(f"    - {lit.n3(g_existing.namespace_manager)}")
                    print("  Restored literals:")
                    for lit in actual_lits:
                        print(f"    - {lit.n3(restored.namespace_manager)}")


if __name__ == "__main__":
    main()
