#!/usr/bin/env python3
"""
Add skos:definition to all SKOS concepts by extracting definitions from original GloSIS ontologies.
- For glosis_lh/su/sp/pr/cm terms: use rdfs:comment
- For glosis_cl terms: use skos:definition
"""

from rdflib import Graph, Namespace, RDF, RDFS, SKOS, Literal
import os

# Namespaces
GLOSIS_LH = Namespace("http://w3id.org/glosis/model/layerhorizon/")
GLOSIS_SU = Namespace("http://w3id.org/glosis/model/surface/")
GLOSIS_SP = Namespace("http://w3id.org/glosis/model/siteplot/")
GLOSIS_PR = Namespace("http://w3id.org/glosis/model/profile/")
GLOSIS_CM = Namespace("http://w3id.org/glosis/model/common/")
GLOSIS_CL = Namespace("http://w3id.org/glosis/model/codelists/")
SHE = Namespace("https://soilwise-he.github.io/soil-health#")

def load_all_definitions():
    """
    Load all definitions from GloSIS ontology files.
    Returns dict: {URI: definition_text}
    """
    print("Loading definitions from original GloSIS ontologies...")

    definitions = {}

    # Map of ontology files to parse
    ontology_files = {
        'common': 'ontovocabs/glosis/glosis_ori/glosis_common.ttl',
        'surface': 'ontovocabs/glosis/glosis_ori/glosis_surface.ttl',
        'siteplot': 'ontovocabs/glosis/glosis_ori/glosis_siteplot.ttl',
        'profile': 'ontovocabs/glosis/glosis_ori/glosis_profile.ttl',
        'layer_horizon': 'ontovocabs/glosis/glosis_ori/glosis_layer_horizon.ttl',
        'codelists': 'ontovocabs/glosis/glosis_ori/glosis_cl.ttl'
    }

    for module_name, file_path in ontology_files.items():
        if not os.path.exists(file_path):
            print(f"  Warning: {file_path} not found, skipping")
            continue

        print(f"  Loading {module_name}...")
        g = Graph()
        g.parse(file_path, format='turtle')

        # Collect both rdfs:comment and skos:definition from all modules
        for s, o in g.subject_objects(RDFS.comment):
            definitions[str(s)] = str(o)

        for s, o in g.subject_objects(SKOS.definition):
            # Only add if not already added from rdfs:comment (prefer rdfs:comment)
            if str(s) not in definitions:
                definitions[str(s)] = str(o)

    print(f"  Loaded {len(definitions)} definitions\n")
    return definitions

def add_definitions_to_skos_file(input_file, output_file, all_definitions):
    """
    Add skos:definition to concepts in a SKOS file based on their skos:exactMatch.
    Returns list of concepts without definitions.
    """
    print(f"Processing {input_file}...")

    g = Graph()
    g.parse(input_file, format='turtle')

    # Preserve namespace bindings
    for prefix, namespace in g.namespace_manager.namespaces():
        g.bind(prefix, namespace)

    concepts_without_definitions = []
    concepts_with_definitions = []

    # Find all concepts
    for concept in g.subjects(RDF.type, SKOS.Concept):
        # Skip if already has definition
        if (concept, SKOS.definition, None) in g:
            continue

        # Get exactMatch URIs
        exact_matches = list(g.objects(concept, SKOS.exactMatch))

        if not exact_matches:
            # No exactMatch, skip
            continue

        # Try to find definition from any exactMatch
        definition_found = False
        for match_uri in exact_matches:
            match_str = str(match_uri)
            if match_str in all_definitions:
                definition_text = all_definitions[match_str]
                g.add((concept, SKOS.definition, Literal(definition_text, lang='en')))
                concepts_with_definitions.append(str(concept).replace(str(SHE), 'she:'))
                definition_found = True
                break

        # If exactMatch points to glosis_cl but not found, try to find the class definition
        # by constructing the class URI from the concept name
        if not definition_found:
            for match_uri in exact_matches:
                match_str = str(match_uri)
                # Check if this is a glosis_cl property that doesn't exist
                if 'glosis/model/codelists/' in match_str:
                    # Try to find corresponding class in other modules
                    concept_name = str(concept).replace(str(SHE), '')
                    # Try glosis_lh, glosis_sp, etc.
                    for namespace in [GLOSIS_LH, GLOSIS_SP, GLOSIS_SU, GLOSIS_PR, GLOSIS_CM]:
                        class_uri = str(namespace[concept_name])
                        if class_uri in all_definitions:
                            definition_text = all_definitions[class_uri]
                            g.add((concept, SKOS.definition, Literal(definition_text, lang='en')))
                            concepts_with_definitions.append(str(concept).replace(str(SHE), 'she:'))
                            definition_found = True
                            break
                    if definition_found:
                        break

        if not definition_found:
            concept_name = str(concept).replace(str(SHE), 'she:')
            match_names = [str(m) for m in exact_matches]
            concepts_without_definitions.append({
                'concept': concept_name,
                'exactMatch': match_names
            })

    # Save updated file
    g.serialize(destination=output_file, format='turtle')

    print(f"  Added {len(concepts_with_definitions)} definitions")
    print(f"  {len(concepts_without_definitions)} concepts without definitions")

    return concepts_without_definitions

def main():
    print("=" * 80)
    print("Adding skos:definition to all SKOS concepts")
    print("=" * 80 + "\n")

    # Load all definitions from original ontologies
    all_definitions = load_all_definitions()

    # Files to process
    skos_files = [
        {
            'module': 'common',
            'input': 'ontovocabs/glosis/glosis_skos_hier/glosis_common_skos_hierarchical.ttl',
            'output': 'ontovocabs/glosis/glosis_skos_hier/glosis_common_skos_hierarchical.ttl'
        },
        {
            'module': 'surface',
            'input': 'ontovocabs/glosis/glosis_skos_hier/glosis_surface_skos_hierarchical.ttl',
            'output': 'ontovocabs/glosis/glosis_skos_hier/glosis_surface_skos_hierarchical.ttl'
        },
        {
            'module': 'siteplot',
            'input': 'ontovocabs/glosis/glosis_skos_hier/glosis_siteplot_skos_hierarchical.ttl',
            'output': 'ontovocabs/glosis/glosis_skos_hier/glosis_siteplot_skos_hierarchical.ttl'
        },
        {
            'module': 'profile',
            'input': 'ontovocabs/glosis/glosis_skos_hier/glosis_profile_skos_hierarchical.ttl',
            'output': 'ontovocabs/glosis/glosis_skos_hier/glosis_profile_skos_hierarchical.ttl'
        },
        {
            'module': 'layer_horizon',
            'input': 'ontovocabs/glosis/glosis_skos_hier/glosis_layer_horizon_skos_hierarchical_with_procedures.ttl',
            'output': 'ontovocabs/glosis/glosis_skos_hier/glosis_layer_horizon_skos_hierarchical_with_procedures.ttl'
        }
    ]

    all_missing = {}

    for file_info in skos_files:
        module = file_info['module']
        missing = add_definitions_to_skos_file(
            file_info['input'],
            file_info['output'],
            all_definitions
        )
        if missing:
            all_missing[module] = missing
        print()

    # Report concepts without definitions
    print("=" * 80)
    print("CONCEPTS WITHOUT DEFINITIONS")
    print("=" * 80 + "\n")

    if all_missing:
        for module, concepts in all_missing.items():
            print(f"{module.upper()} MODULE ({len(concepts)} concepts):")
            for item in concepts:
                print(f"  {item['concept']}")
                for match in item['exactMatch']:
                    print(f"    exactMatch: {match}")
            print()
    else:
        print("All concepts have definitions!")

    print("=" * 80)
    print("COMPLETE")
    print("=" * 80)

if __name__ == '__main__':
    main()
