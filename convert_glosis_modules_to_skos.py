#!/usr/bin/env python3
"""
Convert GloSIS ontology modules to SKOS-based vocabularies
"""
import re
from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import SKOS, RDF

def camel_to_label(camel_str):
    """Convert CamelCase to space-separated label (lowercase)"""
    result = re.sub('(.)([A-Z][a-z]+)', r'\1 \2', camel_str)
    result = re.sub('([a-z0-9])([A-Z])', r'\1 \2', result)
    return result.lower()

def parse_glosis_module(ttl_file, prefix):
    """Parse GloSIS module TTL file to extract classes and their properties"""

    with open(ttl_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find all owl:Class definitions with the given prefix
    class_pattern = rf'{prefix}:(\w+)\s+a\s+owl:Class'
    classes = re.findall(class_pattern, content)

    # Find all sosa:ObservableProperty definitions
    property_pattern = rf'{prefix}:(\w+Property)\s+a\s+sosa:ObservableProperty'
    properties = set(re.findall(property_pattern, content))

    # Find mappings between classes and properties
    class_to_property = {}

    for cls in classes:
        # Look for the pattern: owl:hasValue prefix:someProperty
        class_block_pattern = rf'{prefix}:{cls}\s+a\s+owl:Class\s*;.*?(?=\n{prefix}:\w+|$)'
        class_block_match = re.search(class_block_pattern, content, re.DOTALL)

        if class_block_match:
            class_block = class_block_match.group(0)
            # Find property in this block
            prop_match = re.search(rf'owl:hasValue\s+{prefix}:(\w+Property)', class_block)
            if prop_match:
                prop_name = prop_match.group(1)
                if prop_name in properties:
                    class_to_property[cls] = prop_name

    # Separate classes with and without properties
    classes_with_props = {cls: prop for cls, prop in class_to_property.items()}
    classes_without_props = [cls for cls in classes if cls not in class_to_property]

    return classes_with_props, classes_without_props

def generate_skos_ttl(classes_with_props, output_file, module_prefix_uri):
    """Generate flat SKOS-based TTL file using rdflib"""

    g = Graph()

    SHE = Namespace("https://soilwise-he.github.io/soil-health#")
    MODULE = Namespace(module_prefix_uri)

    g.bind("she", SHE)
    g.bind("glosis", MODULE)
    g.bind("skos", SKOS)

    for cls, prop in sorted(classes_with_props.items()):
        label = camel_to_label(cls)

        concept_uri = SHE[cls]
        property_uri = MODULE[prop]

        g.add((concept_uri, RDF.type, SKOS.Concept))
        g.add((concept_uri, SKOS.prefLabel, Literal(label, lang="en")))
        g.add((concept_uri, SKOS.exactMatch, property_uri))

    g.serialize(destination=output_file, format='turtle')

def generate_hierarchical_skos_ttl(classes_with_props, output_file, module_prefix_uri, hierarchies, additional_concepts=None):
    """Generate hierarchical SKOS-based TTL file with broader/narrower relationships

    Args:
        classes_with_props: Dict of classes that have observable properties
        output_file: Output file path
        module_prefix_uri: URI for the module namespace
        hierarchies: Dict defining hierarchical relationships
        additional_concepts: Dict of additional concepts to include without exactMatch
    """

    g = Graph()

    SHE = Namespace("https://soilwise-he.github.io/soil-health#")
    MODULE = Namespace(module_prefix_uri)

    g.bind("she", SHE)
    g.bind("glosis", MODULE)
    g.bind("skos", SKOS)

    # Track all concepts (with and without properties)
    all_concepts = set(classes_with_props.keys())

    # Generate SKOS concepts for all original classes with properties
    for cls, prop in sorted(classes_with_props.items()):
        label = camel_to_label(cls)
        concept_uri = SHE[cls]
        property_uri = MODULE[prop]

        g.add((concept_uri, RDF.type, SKOS.Concept))
        g.add((concept_uri, SKOS.prefLabel, Literal(label, lang="en")))
        g.add((concept_uri, SKOS.exactMatch, property_uri))

    # Add additional concepts (without exactMatch)
    if additional_concepts:
        for cls, label in additional_concepts.items():
            concept_uri = SHE[cls]
            g.add((concept_uri, RDF.type, SKOS.Concept))
            g.add((concept_uri, SKOS.prefLabel, Literal(label, lang="en")))
            all_concepts.add(cls)

    # Add hierarchical relationships
    for broader_concept, hierarchy_info in hierarchies.items():
        broader_uri = SHE[broader_concept]

        # Add broader concept if it doesn't have its own property
        if not hierarchy_info.get('has_property', False):
            g.add((broader_uri, RDF.type, SKOS.Concept))
            g.add((broader_uri, SKOS.prefLabel, Literal(hierarchy_info['label'], lang="en")))

        # Add narrower relationships
        for narrower_concept in hierarchy_info['narrower']:
            if narrower_concept in all_concepts:
                narrower_uri = SHE[narrower_concept]
                g.add((broader_uri, SKOS.narrower, narrower_uri))
                g.add((narrower_uri, SKOS.broader, broader_uri))

    g.serialize(destination=output_file, format='turtle')

def get_additional_concepts(module_name):
    """Define additional concepts (without observable properties) to include in hierarchical SKOS"""

    additional = {}

    if module_name == 'profile':
        # These are subclasses of SoilClassification but don't have their own properties
        additional = {
            'SoilClassificationUSDA': 'soil classification usda',
            'SoilClassificationFAO': 'soil classification fao',
            'SoilClassificationWRB': 'soil classification wrb'
        }

    return additional

def get_module_hierarchies(module_name, classes_with_props):
    """Define hierarchies for each module based on class naming patterns"""

    hierarchies = {}

    if module_name == 'surface':
        hierarchies = {
            'SaltProperties': {
                'label': 'salt properties',
                'narrower': ['SaltPresence', 'SaltThickness', 'SaltCover'],
                'has_property': False
            },
            'SealingProperties': {
                'label': 'sealing properties',
                'narrower': ['SealingConsistence', 'SealingThickness'],
                'has_property': False
            }
        }

    elif module_name == 'siteplot':
        hierarchies = {
            'SlopeProperties': {
                'label': 'slope properties',
                'narrower': ['SlopeOrientationClass', 'SlopeOrientationNumeric', 'SlopeForm', 'SlopeGradientClass', 'SlopeGradientNumeric'],
                'has_property': False
            },
            'ErosionProperties': {
                'label': 'erosion properties',
                'narrower': ['ErosionCategory', 'ErosionAreaAffected', 'ErosionDegree'],
                'has_property': False
            },
            'LandUse': {
                'label': 'land use',
                'narrower': ['LandUseGrass', 'LandUseBareCover', 'LandUseForest'],
                'has_property': False
            },
            'ParentMaterial': {
                'label': 'parent material',
                'narrower': ['ParentTextureUnconsolidated', 'ParentLithology', 'ParentDeposition'],
                'has_property': False
            }
        }

    elif module_name == 'profile':
        hierarchies = {
            'SoilClassification': {
                'label': 'soil classification',
                'narrower': ['SoilClassificationUSDA', 'SoilClassificationFAO', 'SoilClassificationWRB'],
                'has_property': True
            }
        }

    elif module_name == 'layer_horizon':
        hierarchies = {
            'Mottles': {
                'label': 'mottles',
                'narrower': ['MottlesPresence', 'MottlesColour', 'MottlesSize', 'MottlesAbundance'],
                'has_property': False
            },
            'Coating': {
                'label': 'coating',
                'narrower': ['CoatingNature', 'CoatingContrast', 'CoatingAbundance'],
                'has_property': False
            },
            'MineralConcretions': {
                'label': 'mineral concretions',
                'narrower': ['MineralConcKind', 'MineralConcNature', 'MineralConcShape'],
                'has_property': False
            },
            'Cementation': {
                'label': 'cementation',
                'narrower': ['CementationDegree', 'CementationFabric'],
                'has_property': False
            },
            'Structure': {
                'label': 'structure',
                'narrower': ['StructureGrade', 'StructureSize'],
                'has_property': False
            },
            'Voids': {
                'label': 'voids',
                'narrower': ['VoidsClassification', 'VoidsDiameter'],
                'has_property': False
            },
            'Consistency': {
                'label': 'consistency',
                'narrower': ['DryConsistency', 'ConsistenceDry'],
                'has_property': False
            },
            'Roots': {
                'label': 'roots',
                'narrower': ['RootsPresence'],
                'has_property': False
            },
            'Gypsum': {
                'label': 'gypsum',
                'narrower': ['GypsumForms', 'GypsumWeight'],
                'has_property': False
            },
            'ParticleSizeAnalysis': {
                'label': 'particle size analysis',
                'narrower': ['Sand', 'Silt', 'ParticleSizeFractionsSum'],
                'has_property': False
            }
        }

    # Return hierarchies without filtering - filtering will be done in process_module
    return hierarchies

def process_module(module_name, prefix, prefix_uri):
    """Process a single GloSIS module"""

    input_file = f'/home/user/soil-vocabs/ontovocabs/glosis/glosis_{module_name}.ttl'
    output_file = f'/home/user/soil-vocabs/ontovocabs/glosis/glosis_{module_name}_skos.ttl'
    hierarchical_output_file = f'/home/user/soil-vocabs/ontovocabs/glosis/glosis_{module_name}_skos_hierarchical.ttl'

    print(f"\n{'='*60}")
    print(f"Processing module: {module_name}")
    print(f"{'='*60}")

    classes_with_props, classes_without_props = parse_glosis_module(input_file, prefix)

    print(f"\nFound {len(classes_with_props)} classes WITH observable properties")
    print(f"Found {len(classes_without_props)} classes WITHOUT observable properties")

    if not classes_with_props:
        print(f"No classes with properties found for {module_name}, skipping...")
        return

    # Generate flat SKOS
    print(f"\nGenerating flat SKOS: {output_file}")
    generate_skos_ttl(classes_with_props, output_file, prefix_uri)

    # Generate hierarchical SKOS
    hierarchies = get_module_hierarchies(module_name, classes_with_props)
    additional_concepts = get_additional_concepts(module_name)

    # Filter hierarchies to only include narrower concepts that exist
    all_available_concepts = set(classes_with_props.keys()) | set(additional_concepts.keys())
    filtered_hierarchies = {}
    for broader, info in hierarchies.items():
        existing_narrower = [n for n in info['narrower'] if n in all_available_concepts]
        if existing_narrower or info.get('has_property', False):
            filtered_hierarchies[broader] = {
                'label': info['label'],
                'narrower': existing_narrower,
                'has_property': info.get('has_property', False)
            }

    print(f"Generating hierarchical SKOS: {hierarchical_output_file}")
    if filtered_hierarchies:
        print(f"  With {len(filtered_hierarchies)} hierarchies:")
        for broader, info in filtered_hierarchies.items():
            print(f"    - {broader} ({len(info['narrower'])} narrower concepts)")
    if additional_concepts:
        print(f"  With {len(additional_concepts)} additional concepts (without exactMatch)")

    generate_hierarchical_skos_ttl(classes_with_props, hierarchical_output_file, prefix_uri, filtered_hierarchies, additional_concepts)

    print(f"✓ Module {module_name} completed")

def main():
    """Process all GloSIS modules"""

    modules = [
        ('surface', 'glosis_su', 'http://w3id.org/glosis/model/surface/'),
        ('siteplot', 'glosis_sp', 'http://w3id.org/glosis/model/siteplot/'),
        ('profile', 'glosis_pr', 'http://w3id.org/glosis/model/profile/'),
        ('layer_horizon', 'glosis_lh', 'http://w3id.org/glosis/model/layerhorizon/')
    ]

    print("Converting GloSIS modules to SKOS vocabularies")
    print("=" * 60)

    for module_name, prefix, prefix_uri in modules:
        try:
            process_module(module_name, prefix, prefix_uri)
        except Exception as e:
            print(f"✗ Error processing {module_name}: {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'='*60}")
    print("All modules processed!")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()
