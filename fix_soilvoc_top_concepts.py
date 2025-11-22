#!/usr/bin/env python3
"""
Fix top concepts in SoilVoc.ttl:
1. Include concepts with narrower but no broader (hierarchy roots)
2. Include orphan concepts (no broader, no narrower)
3. Exclude any concepts with exactMatch to glosis_proc
"""

from rdflib import Graph, Namespace, RDF, SKOS, URIRef

# Namespaces
SHE = Namespace("https://soilwise-he.github.io/soil-health#")
GLOSIS_PROC = Namespace("http://w3id.org/glosis/model/procedure/")
SCHEME_URI = URIRef("https://soilwise-he.github.io/soil-health")

def identify_correct_top_concepts(graph):
    """
    Identify top concepts:
    1. Concepts with narrower but no broader (hierarchy roots)
    2. Orphan concepts (no broader, no narrower)
    3. Exclude concepts with exactMatch to glosis_proc
    """
    print("Identifying correct top concepts...")

    top_concepts = []

    for concept in graph.subjects(RDF.type, SKOS.Concept):
        # Check if concept has exact match to glosis_proc - if so, skip
        exact_matches = list(graph.objects(concept, SKOS.exactMatch))
        is_procedure = any('glosis/model/procedure/' in str(match) for match in exact_matches)

        if is_procedure:
            continue

        # Check if concept has narrower concepts
        has_narrower = (concept, SKOS.narrower, None) in graph
        # Check if concept has broader concepts
        has_broader = (concept, SKOS.broader, None) in graph

        # Top concept conditions:
        # 1. Has narrower but no broader (hierarchy root)
        # 2. No narrower and no broader (orphan)
        if (has_narrower and not has_broader) or (not has_narrower and not has_broader):
            top_concepts.append(concept)
            concept_name = str(concept).replace(str(SHE), 'she:')
            category = "hierarchy root" if has_narrower else "orphan"
            print(f"  {concept_name} ({category})")

    print(f"\nTotal: {len(top_concepts)} top concepts\n")
    return top_concepts

def update_soilvoc_top_concepts(soilvoc_path):
    """Update top concepts in SoilVoc.ttl"""
    print(f"Loading {soilvoc_path}...")

    # Load SoilVoc
    soilvoc = Graph()
    soilvoc.parse(soilvoc_path, format='turtle')

    # Preserve namespace bindings
    for prefix, namespace in soilvoc.namespace_manager.namespaces():
        soilvoc.bind(prefix, namespace)

    print(f"Loaded {len(list(soilvoc.subjects(RDF.type, SKOS.Concept)))} concepts\n")

    # Identify correct top concepts
    correct_top_concepts = identify_correct_top_concepts(soilvoc)

    # Remove existing hasTopConcept triples
    print("Removing existing top concept declarations...")
    existing_top_concepts = list(soilvoc.objects(SCHEME_URI, SKOS.hasTopConcept))
    print(f"  Removing {len(existing_top_concepts)} existing top concepts")

    for top_concept in existing_top_concepts:
        soilvoc.remove((SCHEME_URI, SKOS.hasTopConcept, top_concept))

    # Add new top concepts
    print(f"\nAdding {len(correct_top_concepts)} new top concepts...")
    for concept in sorted(correct_top_concepts, key=lambda c: str(c)):
        soilvoc.add((SCHEME_URI, SKOS.hasTopConcept, concept))

    # Save updated SoilVoc
    print(f"\nSaving updated {soilvoc_path}...")
    soilvoc.serialize(destination=soilvoc_path, format='turtle')
    print("Done!\n")

    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total concepts: {len(list(soilvoc.subjects(RDF.type, SKOS.Concept)))}")
    print(f"Top concepts: {len(correct_top_concepts)}")

    # Count hierarchy roots vs orphans
    hierarchy_roots = 0
    orphans = 0
    for concept in correct_top_concepts:
        has_narrower = (concept, SKOS.narrower, None) in soilvoc
        if has_narrower:
            hierarchy_roots += 1
        else:
            orphans += 1

    print(f"  - Hierarchy roots: {hierarchy_roots}")
    print(f"  - Orphan concepts: {orphans}")
    print("=" * 80)

def main():
    print("=" * 80)
    print("Fixing top concepts in SoilVoc.ttl")
    print("=" * 80 + "\n")

    soilvoc_path = 'SoilVoc.ttl'
    update_soilvoc_top_concepts(soilvoc_path)

if __name__ == '__main__':
    main()
