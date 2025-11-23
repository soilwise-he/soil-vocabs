#!/usr/bin/env python3
"""
Convert American English to British English in SoilVoc.ttl
- Changes URIs from American to British spellings
- Changes prefLabels to British English
- Sets American English as altLabel
"""

from rdflib import Graph, Namespace, RDF, SKOS, URIRef, Literal
import re

# Import the UK-US mapping
import sys
sys.path.append('soil_health_benchmarks')
from uk2us import uk_us

SHE = Namespace("https://soilwise-he.github.io/soil-health#")
SCHEME_URI = URIRef("https://soilwise-he.github.io/soil-health")

def build_us_to_uk_mapping():
    """Build dictionary mapping American English to British English."""
    us_to_uk = {}
    for uk, us in uk_us:
        # Store both lowercase and title case versions
        us_to_uk[us.strip()] = uk.strip()
    return us_to_uk

def convert_camelcase_to_british(text, us_to_uk):
    """
    Convert CamelCase text from American to British spellings.
    Returns (converted_text, changed) tuple.
    """
    changed = False
    result = text

    # Sort by length (longest first) to match longer patterns first
    sorted_mappings = sorted(us_to_uk.items(), key=lambda x: len(x[0]), reverse=True)

    # Try to match American spellings in the text
    for us, uk in sorted_mappings:
        # Skip entries with special characters (spaces, punctuation)
        if ' ' in us or not us.strip().replace('-', '').isalpha():
            continue

        us = us.strip()
        uk = uk.strip()

        if not us or not uk:
            continue

        # For CamelCase, we need to match capitalized versions
        # E.g., "Color" in "SoilColor", "Sulfur" in "SulfurTotal"

        # Try to match capitalized American word in CamelCase
        us_capitalized = us[0].upper() + us[1:] if len(us) > 1 else us.upper()
        uk_capitalized = uk[0].upper() + uk[1:] if len(uk) > 1 else uk.upper()

        # Match the capitalized form (case-sensitive for CamelCase)
        if us_capitalized in result:
            result = result.replace(us_capitalized, uk_capitalized)
            changed = True

        # Also try all-lowercase match for parts that might be lowercase
        if us.lower() in result.lower() and us.lower() in result:
            result = result.replace(us.lower(), uk.lower())
            changed = True

    return result, changed

def convert_lowercase_to_british(text, us_to_uk):
    """
    Convert lowercase text from American to British spellings.
    Returns (converted_text, changed) tuple.
    """
    changed = False
    result = text

    # Try to match American spellings (lowercase)
    for us, uk in us_to_uk.items():
        # Skip entries with special characters or whitespace at ends
        us_clean = us.strip()
        uk_clean = uk.strip()

        if not us_clean or not uk_clean:
            continue

        # For prefLabels, we work with whole phrases
        # Match whole words only
        pattern = r'\b' + re.escape(us_clean) + r'\b'

        if re.search(pattern, result, re.IGNORECASE):
            result = re.sub(pattern, uk_clean, result, flags=re.IGNORECASE)
            changed = True

    return result, changed

def convert_soilvoc_to_british(soilvoc_path):
    """Convert SoilVoc from American to British English."""
    print("=" * 80)
    print("Converting SoilVoc from American to British English")
    print("=" * 80 + "\n")

    # Build mapping
    print("Building US->UK mapping...")
    us_to_uk = build_us_to_uk_mapping()
    print(f"Loaded {len(us_to_uk)} mappings\n")

    # Load SoilVoc
    print(f"Loading {soilvoc_path}...")
    g = Graph()
    g.parse(soilvoc_path, format='turtle')

    # Preserve namespace bindings
    for prefix, namespace in g.namespace_manager.namespaces():
        g.bind(prefix, namespace)

    total_concepts = len(list(g.subjects(RDF.type, SKOS.Concept)))
    print(f"Loaded {total_concepts} concepts\n")

    # Track changes
    conversions = []

    # Create new graph for converted concepts
    new_graph = Graph()
    for prefix, namespace in g.namespace_manager.namespaces():
        new_graph.bind(prefix, namespace)

    # Map old URIs to new URIs
    uri_mapping = {}

    # First pass: identify concepts to convert and create URI mappings
    print("Identifying concepts with American English spellings...")
    for old_concept_uri in g.subjects(RDF.type, SKOS.Concept):
        # Extract local name
        local_name = str(old_concept_uri).replace(str(SHE), '')

        # Try to convert local name to British
        new_local_name, uri_changed = convert_camelcase_to_british(local_name, us_to_uk)

        # Get prefLabel
        pref_label = g.value(old_concept_uri, SKOS.prefLabel)
        pref_label_text = str(pref_label) if pref_label else None

        # Try to convert prefLabel to British
        label_changed = False
        new_pref_label_text = pref_label_text
        if pref_label_text:
            new_pref_label_text, label_changed = convert_lowercase_to_british(pref_label_text, us_to_uk)

        if uri_changed or label_changed:
            # Create new URI
            new_concept_uri = URIRef(str(SHE) + new_local_name)
            uri_mapping[old_concept_uri] = new_concept_uri

            conversions.append({
                'old_uri': str(old_concept_uri),
                'new_uri': str(new_concept_uri),
                'old_label': pref_label_text,
                'new_label': new_pref_label_text,
                'uri_changed': uri_changed,
                'label_changed': label_changed
            })
        else:
            # No change, keep the same URI
            uri_mapping[old_concept_uri] = old_concept_uri

    print(f"Found {len(conversions)} concepts to convert\n")

    # Second pass: rebuild the graph with new URIs and labels
    print("Rebuilding graph with British English...")
    for old_concept_uri in g.subjects(RDF.type, SKOS.Concept):
        new_concept_uri = uri_mapping[old_concept_uri]

        # Add concept type
        new_graph.add((new_concept_uri, RDF.type, SKOS.Concept))

        # Process all properties
        for pred, obj in g.predicate_objects(old_concept_uri):
            if pred == RDF.type:
                continue  # Already added

            elif pred == SKOS.prefLabel:
                # Convert prefLabel
                old_label = str(obj)
                new_label, _ = convert_lowercase_to_british(old_label, us_to_uk)
                new_graph.add((new_concept_uri, SKOS.prefLabel, Literal(new_label, lang='en')))

                # If changed, add old American label as altLabel
                if new_label != old_label:
                    new_graph.add((new_concept_uri, SKOS.altLabel, Literal(old_label, lang='en')))

            elif pred == SKOS.altLabel:
                # Keep existing altLabels
                new_graph.add((new_concept_uri, pred, obj))

            elif pred in [SKOS.broader, SKOS.narrower]:
                # Update references to other concepts
                if obj in uri_mapping:
                    new_obj = uri_mapping[obj]
                    new_graph.add((new_concept_uri, pred, new_obj))
                else:
                    new_graph.add((new_concept_uri, pred, obj))

            else:
                # Copy other properties as-is
                new_graph.add((new_concept_uri, pred, obj))

    # Copy all ConceptScheme and hasTopConcept triples
    print("Copying concept scheme and top concepts...")
    for s, p, o in g:
        if s == SCHEME_URI or p == SKOS.hasTopConcept:
            # Update object if it's a concept that was converted
            new_o = uri_mapping.get(o, o) if isinstance(o, URIRef) else o
            new_graph.add((s, p, new_o))

    # Save updated graph
    print(f"\nSaving updated {soilvoc_path}...")
    new_graph.serialize(destination=soilvoc_path, format='turtle')
    print("Done!\n")

    return conversions

def main():
    soilvoc_path = 'SoilVoc.ttl'
    conversions = convert_soilvoc_to_british(soilvoc_path)

    # Print summary
    print("=" * 80)
    print("CONVERSION SUMMARY")
    print("=" * 80)
    print(f"Total concepts converted: {len(conversions)}\n")

    if conversions:
        print("Converted concepts:")
        print("-" * 80)
        for i, conv in enumerate(conversions, 1):
            print(f"{i}. {conv['old_uri'].replace(str(SHE), 'she:')}")
            print(f"   -> {conv['new_uri'].replace(str(SHE), 'she:')}")
            if conv['label_changed']:
                print(f"   prefLabel: '{conv['old_label']}' -> '{conv['new_label']}'")
                print(f"   altLabel: '{conv['old_label']}' (American English)")
            print()
    else:
        print("No American English spellings found in SoilVoc.")

    print("=" * 80)

    # Return conversions for further processing
    return conversions

if __name__ == '__main__':
    conversions = main()
