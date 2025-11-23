#!/usr/bin/env python3
"""
Add skos:altLabel (plural forms) to concepts in SoilVoc.ttl
"""

from rdflib import Graph, Namespace, RDF, SKOS, Literal

SHE = Namespace("https://soilwise-he.github.io/soil-health#")

def add_plural_alt_labels(ttl_file):
    """
    Add plural form altLabels to concepts based on their prefLabel.
    """
    print(f"Loading {ttl_file}...")
    g = Graph()
    g.parse(ttl_file, format='turtle')

    # Preserve namespace bindings
    for prefix, namespace in g.namespace_manager.namespaces():
        g.bind(prefix, namespace)

    # Rules for generating plurals
    def make_plural(label):
        """Generate plural form of a label."""
        label_lower = label.lower()
        words = label_lower.split()

        # Skip if already plural-ish
        if label_lower.endswith('s') or label_lower.endswith('properties') or label_lower.endswith('data'):
            return None

        # Handle special cases
        last_word = words[-1]

        if last_word.endswith('y') and not last_word.endswith('ay') and not last_word.endswith('ey') and not last_word.endswith('oy') and not last_word.endswith('uy'):
            # property -> properties
            plural_last = last_word[:-1] + 'ies'
        elif last_word.endswith('ch') or last_word.endswith('sh') or last_word.endswith('ss') or last_word.endswith('x') or last_word.endswith('z'):
            # process -> processes
            plural_last = last_word + 'es'
        elif last_word.endswith('fe'):
            # knife -> knives
            plural_last = last_word[:-2] + 'ves'
        elif last_word.endswith('f'):
            # leaf -> leaves
            plural_last = last_word[:-1] + 'ves'
        elif last_word.endswith('us'):
            # focus -> foci (but we'll just add es for simplicity)
            plural_last = last_word[:-2] + 'i'
        elif last_word.endswith('is'):
            # analysis -> analyses
            plural_last = last_word[:-2] + 'es'
        elif last_word.endswith('on'):
            # criterion -> criteria
            plural_last = last_word[:-2] + 'a'
        else:
            # Default: just add s
            plural_last = last_word + 's'

        # Reconstruct the full plural label
        words[-1] = plural_last
        return ' '.join(words)

    added_count = 0
    skipped_count = 0

    # Process all concepts
    for concept in g.subjects(RDF.type, SKOS.Concept):
        # Check if already has altLabel
        if (concept, SKOS.altLabel, None) in g:
            skipped_count += 1
            continue

        # Get prefLabel
        pref_label = g.value(concept, SKOS.prefLabel)
        if not pref_label:
            continue

        label_text = str(pref_label)

        # Generate plural
        plural = make_plural(label_text)

        if plural and plural != label_text:
            # Add altLabel
            g.add((concept, SKOS.altLabel, Literal(plural, lang='en')))
            added_count += 1
            concept_name = str(concept).replace(str(SHE), 'she:')
            print(f"  {concept_name}: '{label_text}' -> altLabel: '{plural}'")

    print(f"\nAdded {added_count} altLabels")
    print(f"Skipped {skipped_count} concepts (already have altLabel)")

    # Save updated file
    print(f"\nSaving updated {ttl_file}...")
    g.serialize(destination=ttl_file, format='turtle')
    print("Done!")

if __name__ == '__main__':
    ttl_file = 'SoilVoc.ttl'
    add_plural_alt_labels(ttl_file)
