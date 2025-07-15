# glossary_to_skos.py
"""
Converts a glossary from a CSV file to a SKOS vocabulary in RDF Turtle format.

This script reads a CSV file with columns for 'term', 'definition', 'url', and 'related'
terms, and transforms it into a SKOS-compliant RDF graph, which is then saved as a
.ttl file.

Usage:
    python glossary_to_skos.py <input_csv_path> <output_ttl_path>

Example:
    python glossary_to_skos.py soil_glossary.csv soil_glossary.ttl
"""

import pandas as pd
import argparse
from rdflib import Graph, URIRef, Literal, Namespace
from rdflib.namespace import SKOS, RDF

def term_to_uri_fragment(term: str) -> str:
    """
    Converts a term string into a URI-friendly fragment.
    It lowercases the term and replaces spaces and underscores with hyphens.
    """
    return term.lower().replace(' ', '-').replace('_', '-')

def extract_uri_fragment_from_url(url: str) -> str:
    """
    Extracts the last path segment from a URL to use as a URI fragment.
    Returns None if the URL is invalid.
    """
    if pd.isna(url) or not url:
        return None
    # Remove trailing slash and get the last part of the path
    return url.rstrip('/').split('/')[-1]

def csv_to_skos_rdf(csv_file_path: str, output_file_path: str):
    """
    Reads a CSV file, converts it to a SKOS RDF graph, and saves it as a Turtle file.

    Args:
        csv_file_path (str): The path to the input CSV file.
        output_file_path (str): The path where the output .ttl file will be saved.
    """
    print("Starting conversion from CSV to SKOS RDF...")

    # Create an RDF graph
    g = Graph()

    # Define and bind the namespace for the glossary
    BENCHMARKS = Namespace("https://soilhealthbenchmarks.eu/glossary/")
    g.bind("benchmarks", BENCHMARKS)
    g.bind("skos", SKOS)

    # Read the CSV file using pandas
    try:
        df = pd.read_csv(csv_file_path)
    except FileNotFoundError:
        print(f"Error: Input file not found at '{csv_file_path}'")
        return

    # --- First Pass: Map all terms to their URI fragments ---
    # This ensures that skos:related links can be created correctly even if terms
    # are defined out of order in the CSV.
    term_to_fragment_map = {}
    for _, row in df.iterrows():
        term = row['term']
        url = row.get('url') # Use .get() for safety if column is missing
        
        # Prefer fragment from the URL if available, otherwise generate from the term
        fragment = extract_uri_fragment_from_url(url)
        if not fragment:
            fragment = term_to_uri_fragment(term)
        
        term_to_fragment_map[term.lower()] = fragment

    # --- Second Pass: Build the RDF graph ---
    for _, row in df.iterrows():
        term = row['term']
        definition = row.get('definition')
        related = row.get('related')
        
        # Get the pre-determined URI fragment for the concept
        fragment = term_to_fragment_map[term.lower()]
        concept_uri = BENCHMARKS[fragment]
        
        # Add the core triples for the concept
        g.add((concept_uri, RDF.type, SKOS.Concept))
        g.add((concept_uri, SKOS.prefLabel, Literal(term.lower(), lang="en")))
        
        # Add definition(s). Handles multiple definitions separated by '|'
        if pd.notna(definition) and definition:
            definitions = [d.strip() for d in str(definition).split('|') if d.strip()]
            for def_text in definitions:
                g.add((concept_uri, SKOS.definition, Literal(def_text, lang="en")))
        
        # Add related terms. Handles multiple related terms separated by ';'
        if pd.notna(related) and related:
            related_terms = [t.strip() for t in str(related).split(';') if t.strip()]
            for related_term in related_terms:
                related_term_lower = related_term.lower()
                if related_term_lower in term_to_fragment_map:
                    related_fragment = term_to_fragment_map[related_term_lower]
                    related_uri = BENCHMARKS[related_fragment]
                    g.add((concept_uri, SKOS.related, related_uri))
                else:
                    print(f"Warning: Related term '{related_term}' for concept '{term}' not found in glossary. Skipping.")

    # Serialize the graph to Turtle format and save to file
    try:
        g.serialize(destination=output_file_path, format='turtle')
        print(f"Conversion successful!")
        print(f"Total concepts created: {len(list(g.subjects(RDF.type, SKOS.Concept)))}")
        print(f"Total triples generated: {len(g)}")
        print(f"RDF Turtle file saved to: {output_file_path}")
    except Exception as e:
        print(f"Error saving file: {e}")


if __name__ == "__main__":
    # Set up command-line argument parsing
    parser = argparse.ArgumentParser(
        description="Convert a glossary CSV file to a SKOS vocabulary in Turtle format.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "input_csv",
        help="Path to the input glossary CSV file."
    )
    parser.add_argument(
        "output_ttl",
        help="Path for the output SKOS Turtle (.ttl) file."
    )
    
    args = parser.parse_args()
    
    # Run the conversion function
    csv_to_skos_rdf(args.input_csv, args.output_ttl)
