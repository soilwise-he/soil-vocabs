#!/usr/bin/env python3
"""
Merge GloSIS SKOS hierarchical files into SoilVoc.ttl
- Add skos:inScheme to all concepts
- Add top concepts to ConceptScheme skos:hasTopConcept
"""

from rdflib import Graph, Namespace, RDF, RDFS, SKOS, URIRef
import os

# Namespaces
SHE = Namespace("https://soilwise-he.github.io/soil-health#")
GLOSIS_LH = Namespace("http://w3id.org/glosis/model/layerhorizon/")
GLOSIS_CL = Namespace("http://w3id.org/glosis/model/codelists/")
GLOSIS_PROC = Namespace("http://w3id.org/glosis/model/procedure/")

SCHEME_URI = URIRef("https://soilwise-he.github.io/soil-health")

def load_glosis_skos_files():
    """Load all five GloSIS SKOS hierarchical files"""
    print("Loading GloSIS SKOS files...")

    files = [
        'ontovocabs/glosis/glosis_skos_hier/glosis_common_skos_hierarchical.ttl',
        'ontovocabs/glosis/glosis_skos_hier/glosis_surface_skos_hierarchical.ttl',
        'ontovocabs/glosis/glosis_skos_hier/glosis_siteplot_skos_hierarchical.ttl',
        'ontovocabs/glosis/glosis_skos_hier/glosis_profile_skos_hierarchical.ttl',
        'ontovocabs/glosis/glosis_skos_hier/glosis_layer_horizon_skos_hierarchical_with_procedures.ttl'
    ]

    # Merge all files into one graph
    merged_graph = Graph()
    merged_graph.bind("she", SHE)
    merged_graph.bind("skos", SKOS)
    merged_graph.bind("glosis_lh", GLOSIS_LH)
    merged_graph.bind("glosis_cl", GLOSIS_CL)
    merged_graph.bind("glosis_proc", GLOSIS_PROC)

    total_concepts = 0
    for file_path in files:
        if not os.path.exists(file_path):
            print(f"  Warning: {file_path} not found, skipping")
            continue

        print(f"  Loading {os.path.basename(file_path)}...")
        g = Graph()
        g.parse(file_path, format='turtle')

        # Count concepts
        concept_count = len(list(g.subjects(RDF.type, SKOS.Concept)))
        total_concepts += concept_count
        print(f"    {concept_count} concepts")

        # Merge into main graph
        for s, p, o in g:
            merged_graph.add((s, p, o))

    print(f"\nTotal: {total_concepts} concepts loaded\n")
    return merged_graph

def add_in_scheme_to_concepts(graph):
    """Add skos:inScheme to all concepts"""
    print("Adding skos:inScheme to all concepts...")

    count = 0
    for concept in graph.subjects(RDF.type, SKOS.Concept):
        # Only add if not already present
        if (concept, SKOS.inScheme, None) not in graph:
            graph.add((concept, SKOS.inScheme, SCHEME_URI))
            count += 1

    print(f"  Added skos:inScheme to {count} concepts\n")
    return graph

def identify_top_concepts(graph):
    """Identify top concepts (have narrower but no broader)"""
    print("Identifying top concepts...")

    top_concepts = []

    for concept in graph.subjects(RDF.type, SKOS.Concept):
        # Check if concept has narrower concepts
        has_narrower = (concept, SKOS.narrower, None) in graph
        # Check if concept has broader concepts
        has_broader = (concept, SKOS.broader, None) in graph

        # Top concept: has narrower but no broader
        if has_narrower and not has_broader:
            top_concepts.append(concept)
            concept_name = str(concept).replace(str(SHE), 'she:')
            print(f"  Found top concept: {concept_name}")

    print(f"\nTotal: {len(top_concepts)} top concepts\n")
    return top_concepts

def merge_into_soilvoc(glosis_graph, top_concepts, soilvoc_path):
    """Merge GloSIS concepts into SoilVoc.ttl"""
    print(f"Merging into {soilvoc_path}...")

    # Load existing SoilVoc
    print("  Loading existing SoilVoc.ttl...")
    soilvoc = Graph()
    soilvoc.parse(soilvoc_path, format='turtle')

    # Preserve namespace bindings
    for prefix, namespace in soilvoc.namespace_manager.namespaces():
        soilvoc.bind(prefix, namespace)

    # Add GloSIS namespace bindings
    soilvoc.bind("glosis_lh", GLOSIS_LH)
    soilvoc.bind("glosis_cl", GLOSIS_CL)
    soilvoc.bind("glosis_proc", GLOSIS_PROC)

    # Count existing concepts in SoilVoc
    existing_concepts = set(soilvoc.subjects(RDF.type, SKOS.Concept))
    print(f"  Existing concepts in SoilVoc: {len(existing_concepts)}")

    # Check for duplicates and add new concepts
    print("  Checking for duplicates and adding GloSIS concepts...")
    added_count = 0
    duplicate_count = 0

    for concept in glosis_graph.subjects(RDF.type, SKOS.Concept):
        if concept in existing_concepts:
            duplicate_count += 1
            # Update: keep GloSIS data (which includes definitions and procedures)
            # Remove old triples
            for p, o in soilvoc.predicate_objects(concept):
                soilvoc.remove((concept, p, o))

        # Add all triples for this concept
        for p, o in glosis_graph.predicate_objects(concept):
            soilvoc.add((concept, p, o))

        added_count += 1

    print(f"    Added/updated: {added_count} concepts")
    if duplicate_count > 0:
        print(f"    Updated (already existed): {duplicate_count} concepts")

    # Add top concepts to ConceptScheme
    print("  Adding top concepts to ConceptScheme...")

    # Get existing top concepts
    existing_top_concepts = set(soilvoc.objects(SCHEME_URI, SKOS.hasTopConcept))
    print(f"    Existing top concepts: {len(existing_top_concepts)}")

    new_top_concepts = 0
    for concept in top_concepts:
        if concept not in existing_top_concepts:
            soilvoc.add((SCHEME_URI, SKOS.hasTopConcept, concept))
            new_top_concepts += 1

    print(f"    Added {new_top_concepts} new top concepts")

    # Count total concepts after merge
    total_concepts = len(list(soilvoc.subjects(RDF.type, SKOS.Concept)))
    print(f"\n  Total concepts in SoilVoc after merge: {total_concepts}")

    # Save updated SoilVoc
    print(f"\n  Saving updated SoilVoc.ttl...")
    soilvoc.serialize(destination=soilvoc_path, format='turtle')
    print(f"  Done!\n")

def main():
    print("=" * 80)
    print("Merging GloSIS SKOS vocabularies into SoilVoc.ttl")
    print("=" * 80 + "\n")

    # Load all GloSIS SKOS files
    glosis_graph = load_glosis_skos_files()

    # Add skos:inScheme to all concepts
    glosis_graph = add_in_scheme_to_concepts(glosis_graph)

    # Identify top concepts
    top_concepts = identify_top_concepts(glosis_graph)

    # Merge into SoilVoc.ttl
    soilvoc_path = 'SoilVoc.ttl'
    merge_into_soilvoc(glosis_graph, top_concepts, soilvoc_path)

    print("=" * 80)
    print("MERGE COMPLETE")
    print("=" * 80)

if __name__ == '__main__':
    main()
