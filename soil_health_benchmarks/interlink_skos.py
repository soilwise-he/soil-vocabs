# interlink_skos.py
"""
Interlinks a local SKOS vocabulary with external thesauri.

This script loads a SKOS vocabulary from a Turtle file and links its concepts
to concepts in external thesauri. It generates skos:exactMatch and skos:closeMatch 
triples based on matching labels.

The script assumes all thesaurus CSV files are located in the '../ontovocabs/' directory.

Usage:
    python interlink_skos.py <input_ttl> <output_ttl> <thesaurus_name_1> [<thesaurus_name_2> ...]

Example:
    python interlink_skos.py soil_glossary.ttl soil_glossary_linked.ttl agrovoc gemet
"""

import pandas as pd
import argparse
import re
import os
from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import SKOS

# Import the UK to US spelling map from the separate file
from uk2us import uk_us

# Define the base path where all thesaurus CSV files are stored
THESAURUS_BASE_PATH = "../ontovocabs/"

# Dictionary mapping thesaurus prefixes to their official namespaces.
THESAURUS_NAMESPACES = {
    "agrovoc": Namespace("http://aims.fao.org/aos/agrovoc/"),
    "iso11074": Namespace("https://data.geoscience.earth/ncl/ISO11074v2025/"),
    "gemet": Namespace("http://www.eionet.europa.eu/gemet/concept/"),
    "inrae": Namespace("http://opendata.inrae.fr/thesaurusINRAE/"),
    "she": Namespace("https://soilwise-he.github.io/soil-health#")
}

def normalize_uk_to_us(label: str) -> str:
    """Normalizes a string from British to American English spelling."""
    for uk_spelling, us_spelling in uk_us:
        label = re.sub(rf'\b{uk_spelling}\b', us_spelling, label, flags=re.IGNORECASE)
    return label

def link_to_thesaurus(graph: Graph, thesaurus_csv_path: str):
    """
    Adds skos:exactMatch and skos:closeMatch links to the graph from a thesaurus CSV.

    Args:
        graph (Graph): The rdflib graph to modify.
        thesaurus_csv_path (str): Path to the thesaurus CSV file. The CSV must contain
                                  'concept' (URI), 'prefLabel', and 'altLabels' columns.
    """
    # Derive the thesaurus prefix from the filename (e.g., "agrovoc.csv" -> "agrovoc")
    base_name = os.path.basename(thesaurus_csv_path)
    prefix = os.path.splitext(base_name)[0].lower()
    
    if prefix in THESAURUS_NAMESPACES:
        print(f"\nProcessing thesaurus: {prefix}")
        namespace = THESAURUS_NAMESPACES[prefix]
        graph.bind(prefix, namespace)
    else:
        print(f"Warning: Namespace for '{prefix}' is not defined. Skipping linking for this file.")
        return

    # Load the thesaurus data
    try:
        df = pd.read_csv(thesaurus_csv_path, encoding="utf-8")
    except FileNotFoundError:
        print(f"Error: Thesaurus file not found at '{thesaurus_csv_path}'")
        return
        
    # Create lookup maps for prefLabels and altLabels from the thesaurus
    pref_label_map = {str(row['prefLabel']).lower(): row['concept'] for _, row in df.iterrows() if pd.notna(row.get('prefLabel'))}
    alt_label_map = {}
    for _, row in df.iterrows():
        if pd.notna(row.get('altLabels')):
            alt_labels = str(row['altLabels']).split(';')
            for alt_label in alt_labels:
                alt_label_clean = alt_label.strip().lower()
                if alt_label_clean:
                    alt_label_map[alt_label_clean] = row['concept']

    # Iterate over our local concepts and create links
    concepts_linked = 0
    for local_concept, p, local_label_literal in graph.triples((None, SKOS.prefLabel, None)):
        local_label = str(local_label_literal).lower()
        normalized_label = normalize_uk_to_us(local_label)
        
        # Check for exact matches on preferred labels
        if normalized_label in pref_label_map:
            match_uri = URIRef(pref_label_map[normalized_label])
            graph.add((local_concept, SKOS.exactMatch, match_uri))
            concepts_linked += 1
            
        # Check for close matches on alternative labels
        elif normalized_label in alt_label_map:
            match_uri = URIRef(alt_label_map[normalized_label])
            graph.add((local_concept, SKOS.closeMatch, match_uri))
            concepts_linked += 1
            
    print(f"Found and added {concepts_linked} links for {prefix}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Interlink a local SKOS vocabulary with external thesauri.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="Example:\n  python interlink_skos.py soil_glossary.ttl soil_linked.ttl agrovoc gemet"
    )
    parser.add_argument("input_ttl", help="Path to the input SKOS Turtle (.ttl) file.")
    parser.add_argument("output_ttl", help="Path for the output (linked) Turtle (.ttl) file.")
    parser.add_argument(
        "thesauri_names",
        nargs='+',
        help="One or more names of the thesauri to link against (e.g., agrovoc, gemet)."
    )
    
    args = parser.parse_args()
    
    g = Graph()
    try:
        print(f"Loading initial vocabulary from: {args.input_ttl}")
        g.parse(args.input_ttl, format="turtle")
    except FileNotFoundError:
        print(f"Error: Input file not found at '{args.input_ttl}'")
        exit()

    # Link against each provided thesaurus by name
    for name in args.thesauri_names:
        # Construct the full path to the CSV file from the name
        csv_path = os.path.join(THESAURUS_BASE_PATH, f"{name}.csv")
        link_to_thesaurus(g, csv_path)

    # Serialize the final, enriched graph to a new file
    try:
        g.serialize(destination=args.output_ttl, format='turtle')
        print(f"\nInterlinking complete.")
        print(f"Final linked vocabulary saved to: {args.output_ttl}")
    except Exception as e:
        print(f"Error saving final file: {e}")
