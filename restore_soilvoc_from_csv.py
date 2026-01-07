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


def build_graph_from_csv(csv_path: Path, scheme_uri: str) -> tuple[Graph, dict[str, str]]:
    rows = read_rows(csv_path)

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

        g.add((concept, RDF.type, SKOS.Concept))
        g.add((concept, SKOS.inScheme, SCHEME_URI))

        pref = str(row[COL_PREF]).strip()
        if pref:
            # CSV doesn't preserve language tags; use plain literals for best round-trip tolerance
            g.add((concept, SKOS.prefLabel, Literal(pref)))

        for alt in split_semicolon(str(row[COL_ALT])):
            g.add((concept, SKOS.altLabel, Literal(alt)))

        definition = str(row[COL_DEF]).strip()
        if definition:
            g.add((concept, SKOS.definition, Literal(definition)))

        for uri in split_semicolon(str(row[COL_EXACT])):
            g.add((concept, SKOS.exactMatch, URIRef(uri)))

        for uri in split_semicolon(str(row[COL_CLOSE])):
            g.add((concept, SKOS.closeMatch, URIRef(uri)))

    # Add broader links using prefLabel -> URI mapping.
    # If the current concept looks like a procedure concept (URI contains 'procedure'),
    # interpret its 'broader' entries as she:isProcedureOf and also add inverse she:hasProcedure.
    for row in rows:
        concept_uri = str(row[COL_ID]).strip()
        if not concept_uri:
            continue
        concept = URIRef(concept_uri)

        is_procedure_concept = "procedure" in concept_uri.casefold()

        for broader_label in split_semicolon(str(row[COL_BROADER])):
            broader_uri = resolve_pref_to_uri(broader_label)
            if broader_uri:
                broader_concept = URIRef(broader_uri)
                if is_procedure_concept:
                    SHE = Namespace("https://soilwise-he.github.io/soil-health#")
                    g.add((concept, SHE.isProcedureOf, broader_concept))
                    g.add((broader_concept, SHE.hasProcedure, concept))
                else:
                    g.add((concept, SKOS.broader, broader_concept))

    # Add inferred skos:narrower (original TTL contains these)
    for child, _, parent in g.triples((None, SKOS.broader, None)):
        g.add((parent, SKOS.narrower, child))

    # Infer top concepts: concepts with no broader but at least one narrower
    has_broader = set(s for s, _, _ in g.triples((None, SKOS.broader, None)))
    has_narrower = set(o for _, _, o in g.triples((None, SKOS.narrower, None)))
    top_concepts = [c for c in concepts if c not in has_broader and c in has_narrower]

    for tc in sorted(set(top_concepts), key=lambda u: str(u)):
        g.add((SCHEME_URI, SKOS.hasTopConcept, tc))
        g.add((tc, SKOS.topConceptOf, SCHEME_URI))

    return g, warnings


def diff_graphs(g_expected: Graph, g_actual: Graph, limit: int = 25) -> tuple[list[tuple], list[tuple]]:
    expected_triples = set(g_expected)
    actual_triples = set(g_actual)
    missing = sorted(expected_triples - actual_triples, key=lambda t: (str(t[0]), str(t[1]), str(t[2])))
    extra = sorted(actual_triples - expected_triples, key=lambda t: (str(t[0]), str(t[1]), str(t[2])))
    return missing[:limit], extra[:limit]


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

        same = isomorphic(restored, g_existing)
        print(f"\nGraph isomorphic to {compare_path}: {same}")

        if not same:
            missing, extra = diff_graphs(g_existing, restored, limit=25)
            print(f"\nTriples missing from restored (showing up to {len(missing)}):")
            for s, p, o in missing:
                print(f"- {s.n3(restored.namespace_manager)} {p.n3(restored.namespace_manager)} {o.n3(restored.namespace_manager)}")

            print(f"\nTriples extra in restored (showing up to {len(extra)}):")
            for s, p, o in extra:
                print(f"- {s.n3(restored.namespace_manager)} {p.n3(restored.namespace_manager)} {o.n3(restored.namespace_manager)}")


if __name__ == "__main__":
    main()
