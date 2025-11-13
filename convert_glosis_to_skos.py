#!/usr/bin/env python3
"""
Convert GloSIS ontology to SKOS-based vocabulary
"""
import re
from collections import defaultdict
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import SKOS, RDF

def camel_to_label(camel_str):
    """Convert CamelCase to space-separated label (lowercase)"""
    # Insert space before uppercase letters
    result = re.sub('(.)([A-Z][a-z]+)', r'\1 \2', camel_str)
    result = re.sub('([a-z0-9])([A-Z])', r'\1 \2', result)
    return result.lower()

def parse_glosis_common(ttl_file):
    """Parse glosis_common.ttl to extract classes and their properties"""

    with open(ttl_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find all owl:Class definitions
    class_pattern = r'glosis_cm:(\w+)\s+a\s+owl:Class'
    classes = re.findall(class_pattern, content)

    # Find all sosa:ObservableProperty definitions
    property_pattern = r'glosis_cm:(\w+Property)\s+a\s+sosa:ObservableProperty'
    properties = set(re.findall(property_pattern, content))

    # Find mappings between classes and properties
    class_to_property = {}

    for cls in classes:
        # Look for the pattern: owl:hasValue glosis_cm:someProperty
        # within the class definition
        class_block_pattern = rf'glosis_cm:{cls}\s+a\s+owl:Class\s*;.*?(?=\nglosis_cm:\w+|$)'
        class_block_match = re.search(class_block_pattern, content, re.DOTALL)

        if class_block_match:
            class_block = class_block_match.group(0)
            # Find property in this block
            prop_match = re.search(r'owl:hasValue\s+glosis_cm:(\w+Property)', class_block)
            if prop_match:
                prop_name = prop_match.group(1)
                if prop_name in properties:
                    class_to_property[cls] = prop_name

    # Separate classes with and without properties
    classes_with_props = {cls: prop for cls, prop in class_to_property.items()}
    classes_without_props = [cls for cls in classes if cls not in class_to_property]

    return classes_with_props, classes_without_props

def generate_skos_ttl(classes_with_props, output_file):
    """Generate SKOS-based TTL file using rdflib"""

    # Create a new graph
    g = Graph()

    # Define namespaces
    SHE = Namespace("https://soilwise-he.github.io/soil-health#")
    GLOSIS_CM = Namespace("http://w3id.org/glosis/model/common/")

    # Bind prefixes
    g.bind("she", SHE)
    g.bind("glosis_cm", GLOSIS_CM)
    g.bind("skos", SKOS)

    # Generate SKOS concepts
    for cls, prop in sorted(classes_with_props.items()):
        label = camel_to_label(cls)

        concept_uri = SHE[cls]
        property_uri = GLOSIS_CM[prop]

        # Add triples for the concept
        g.add((concept_uri, RDF.type, SKOS.Concept))
        g.add((concept_uri, SKOS.prefLabel, Literal(label, lang="en")))
        g.add((concept_uri, SKOS.exactMatch, property_uri))

    # Serialize to file
    g.serialize(destination=output_file, format='turtle')

def generate_hierarchical_skos_ttl(classes_with_props, output_file):
    """Generate hierarchical SKOS-based TTL file with broader/narrower relationships"""

    # Create a new graph
    g = Graph()

    # Define namespaces
    SHE = Namespace("https://soilwise-he.github.io/soil-health#")
    GLOSIS_CM = Namespace("http://w3id.org/glosis/model/common/")

    # Bind prefixes
    g.bind("she", SHE)
    g.bind("glosis_cm", GLOSIS_CM)
    g.bind("skos", SKOS)

    # Define hierarchical structure
    hierarchies = {
        'SoilColour': {
            'label': 'soil colour',
            'narrower': ['ColourDry', 'ColourMoist'],
            'has_property': False  # This is a grouping concept, no property match
        },
        'SoilDepth': {
            'label': 'soil depth',
            'narrower': ['SoilDepthBedrock', 'SoilDepthRootable', 'SoilDepthRootableClass', 'SoilDepthSampled'],
            'has_property': True  # SoilDepth itself exists with a property
        },
        'InfiltrationRate': {
            'label': 'infiltration rate',
            'narrower': ['InfiltrationRateClass', 'InfiltrationRateNumeric'],
            'has_property': False
        },
        'SoilCracks': {
            'label': 'soil cracks',
            'narrower': ['CracksDepth', 'CracksDistance', 'CracksWidth'],
            'has_property': False
        },
        'RockProperties': {
            'label': 'rock properties',
            'narrower': ['RockAbundance', 'RockShape', 'RockSize'],
            'has_property': False
        },
        'FragmentProperties': {
            'label': 'fragment properties',
            'narrower': ['FragmentCover', 'FragmentsSize', 'WeatheringFragments'],
            'has_property': False
        }
    }

    # Track which concepts are part of hierarchies
    concepts_in_hierarchies = set()
    for hierarchy in hierarchies.values():
        concepts_in_hierarchies.update(hierarchy['narrower'])

    # Generate SKOS concepts for all original classes
    for cls, prop in sorted(classes_with_props.items()):
        label = camel_to_label(cls)
        concept_uri = SHE[cls]
        property_uri = GLOSIS_CM[prop]

        # Add triples for the concept
        g.add((concept_uri, RDF.type, SKOS.Concept))
        g.add((concept_uri, SKOS.prefLabel, Literal(label, lang="en")))
        g.add((concept_uri, SKOS.exactMatch, property_uri))

    # Add hierarchical relationships
    for broader_concept, hierarchy_info in hierarchies.items():
        broader_uri = SHE[broader_concept]

        # Add broader concept if it doesn't have its own property (i.e., it's a grouping concept)
        if not hierarchy_info['has_property']:
            g.add((broader_uri, RDF.type, SKOS.Concept))
            g.add((broader_uri, SKOS.prefLabel, Literal(hierarchy_info['label'], lang="en")))

        # Add narrower relationships
        for narrower_concept in hierarchy_info['narrower']:
            if narrower_concept in classes_with_props:
                narrower_uri = SHE[narrower_concept]
                g.add((broader_uri, SKOS.narrower, narrower_uri))
                g.add((narrower_uri, SKOS.broader, broader_uri))

    # Serialize to file
    g.serialize(destination=output_file, format='turtle')

def main():
    input_file = '/home/user/soil-vocabs/ontovocabs/glosis/glosis_common.ttl'
    output_file = '/home/user/soil-vocabs/ontovocabs/glosis/glosis_common_skos.ttl'
    hierarchical_output_file = '/home/user/soil-vocabs/ontovocabs/glosis/glosis_common_skos_hierarchical.ttl'

    print("Parsing glosis_common.ttl...")
    classes_with_props, classes_without_props = parse_glosis_common(input_file)

    print(f"\nFound {len(classes_with_props)} classes WITH observable properties:")
    for cls, prop in sorted(classes_with_props.items()):
        label = camel_to_label(cls)
        print(f"  - {cls} -> {prop}")
        print(f"    SKOS Concept: she:{cls}")
        print(f"    prefLabel: \"{label}\"")
        print(f"    exactMatch: glosis_cm:{prop}")
        print()

    print(f"\nFound {len(classes_without_props)} classes WITHOUT observable properties:")
    print("(These will NOT be converted to SKOS concepts)")
    for cls in sorted(classes_without_props):
        print(f"  - {cls}")

    print(f"\nGenerating flat SKOS vocabulary file: {output_file}")
    generate_skos_ttl(classes_with_props, output_file)

    print(f"\nGenerating hierarchical SKOS vocabulary file: {hierarchical_output_file}")
    print("\nHierarchical structure:")
    print("  - SoilColour (broader)")
    print("    - ColourDry (narrower)")
    print("    - ColourMoist (narrower)")
    print("  - SoilDepth (broader, has own property)")
    print("    - SoilDepthBedrock (narrower)")
    print("    - SoilDepthRootable (narrower)")
    print("    - SoilDepthRootableClass (narrower)")
    print("    - SoilDepthSampled (narrower)")
    print("  - InfiltrationRate (broader)")
    print("    - InfiltrationRateClass (narrower)")
    print("    - InfiltrationRateNumeric (narrower)")
    print("  - SoilCracks (broader)")
    print("    - CracksDepth (narrower)")
    print("    - CracksDistance (narrower)")
    print("    - CracksWidth (narrower)")
    print("  - RockProperties (broader)")
    print("    - RockAbundance (narrower)")
    print("    - RockShape (narrower)")
    print("    - RockSize (narrower)")
    print("  - FragmentProperties (broader)")
    print("    - FragmentCover (narrower)")
    print("    - FragmentsSize (narrower)")
    print("    - WeatheringFragments (narrower)")
    print("\n  Standalone concepts (no hierarchy):")
    print("    - Texture")
    print("    - BleachedSand")
    print("    - OrganicMatterClass")

    generate_hierarchical_skos_ttl(classes_with_props, hierarchical_output_file)
    print("\nDone!")

if __name__ == '__main__':
    main()
