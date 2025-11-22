#!/usr/bin/env python3
"""
Enriches layer_horizon hierarchical SKOS file with procedure concepts and links.
"""

from rdflib import Graph, Namespace, RDF, RDFS, OWL, SKOS, URIRef, Literal
import re

# Namespaces
GLOSIS_LH = Namespace("http://w3id.org/glosis/model/layerhorizon/")
GLOSIS_CL = Namespace("http://w3id.org/glosis/model/codelists/")
GLOSIS_PROC = Namespace("http://w3id.org/glosis/model/procedure/")
SOSA = Namespace("http://www.w3.org/ns/sosa/")
SHE = Namespace("https://soilwise-he.github.io/soil-health#")

def parse_class_to_procedure_mapping(ttl_file):
    """
    Parse layer_horizon.ttl to extract which classes use which procedures.
    Returns dict: {ClassName: ProcedureClassName}
    """
    print(f"Parsing {ttl_file} for class-to-procedure mappings...")

    with open(ttl_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find all class definitions with usedProcedure
    class_pattern = r'glosis_lh:(\w+)\s+a\s+owl:Class\s*;(.*?)(?=glosis_lh:\w+\s+a\s+owl:Class|glosis_\w+:\w+\s+rdfs:subClassOf|$)'
    class_to_procedure = {}

    for match in re.finditer(class_pattern, content, re.DOTALL):
        class_name = match.group(1)
        class_block = match.group(2)

        # Look for usedProcedure
        proc_match = re.search(r'sosa:usedProcedure\s*;\s*owl:someValuesFrom\s+glosis_proc:(\w+)', class_block)
        if proc_match:
            procedure_class = proc_match.group(1)
            class_to_procedure[class_name] = procedure_class
            print(f"  Found: {class_name} -> {procedure_class}")

    print(f"Found {len(class_to_procedure)} classes with procedures\n")
    return class_to_procedure

def parse_procedure_instances(ttl_file):
    """
    Parse glosis_procedure.ttl to extract all procedure instances and hierarchies.
    Returns:
    - procedure_instances: dict {ProcedureClass: [instance1, instance2, ...]}
    - procedure_hierarchies: dict {parent_instance: [child1, child2, ...]}
    - all_procedure_uris: set of all procedure instance URIs
    """
    print(f"Parsing {ttl_file} for procedure instances...")

    g = Graph()
    g.parse(ttl_file, format='turtle')

    # Get all procedure instances (they are skos:Concept)
    procedure_instances = {}
    all_procedure_uris = set()

    # Find all procedure class definitions with owl:oneOf
    for proc_class in g.subjects(RDF.type, OWL.Class):
        if str(proc_class).startswith(str(GLOSIS_PROC)):
            proc_class_name = str(proc_class).replace(str(GLOSIS_PROC), '')

            # Get instances via rdf:type
            instances = list(g.subjects(RDF.type, proc_class))
            if instances:
                # Filter to only those that are also skos:Concept
                concept_instances = [inst for inst in instances if (inst, RDF.type, SKOS.Concept) in g]
                if concept_instances:
                    procedure_instances[proc_class_name] = concept_instances
                    all_procedure_uris.update(concept_instances)
                    print(f"  {proc_class_name}: {len(concept_instances)} instances")

    # Extract hierarchies (broader/narrower relationships)
    procedure_hierarchies = {}
    for proc_uri in all_procedure_uris:
        narrower_concepts = list(g.objects(proc_uri, SKOS.narrower))
        if narrower_concepts:
            procedure_hierarchies[proc_uri] = narrower_concepts
            print(f"  Hierarchy: {proc_uri} has {len(narrower_concepts)} narrower concepts")

    print(f"Found {len(all_procedure_uris)} total procedure instances\n")
    print(f"Found {len(procedure_hierarchies)} procedure hierarchies\n")

    return procedure_instances, procedure_hierarchies, all_procedure_uris, g

def camel_to_words(name):
    """Convert CamelCase to space-separated words."""
    # Insert space before uppercase letters
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1 \2', name)
    # Insert space before uppercase letters that follow lowercase letters or numbers
    s2 = re.sub('([a-z0-9])([A-Z])', r'\1 \2', s1)
    return s2.lower()

def create_enriched_skos(input_skos_file, output_file, class_to_procedure, procedure_instances,
                         procedure_hierarchies, all_procedure_uris, proc_graph):
    """
    Create enriched SKOS file with procedures.
    """
    print(f"Creating enriched SKOS file...")

    # Load existing SKOS file
    g = Graph()
    g.parse(input_skos_file, format='turtle')

    # Add namespace bindings
    g.bind("she", SHE)
    g.bind("glosis_lh", GLOSIS_LH)
    g.bind("glosis_cl", GLOSIS_CL)
    g.bind("glosis_proc", GLOSIS_PROC)
    g.bind("skos", SKOS)

    # Define she:hasProcedure property
    has_procedure = SHE.hasProcedure

    # Track which procedures we've added
    added_procedures = set()

    # For each layer horizon class in the SKOS file, add procedure links
    for class_name, procedure_class in class_to_procedure.items():
        # Find the corresponding she: concept
        she_concept = SHE[class_name]

        # Check if this concept exists in the SKOS file
        if (she_concept, RDF.type, SKOS.Concept) in g:
            # Get the procedure instances for this procedure class
            if procedure_class in procedure_instances:
                instances = procedure_instances[procedure_class]

                # Determine which instances to link:
                # If any instance has narrower concepts, link only to those top-level instances
                # Otherwise, link to all instances
                top_level_instances = []
                for inst in instances:
                    # Check if this instance has narrower concepts
                    if inst in procedure_hierarchies:
                        # This is a top-level (broader) procedure
                        top_level_instances.append(inst)
                    elif not any(inst in children for children in procedure_hierarchies.values()):
                        # This instance is not a child of any other instance
                        top_level_instances.append(inst)

                # If we found top-level instances, use them; otherwise use all
                instances_to_link = top_level_instances if top_level_instances else instances

                for proc_inst_uri in instances_to_link:
                    # Extract the procedure instance name
                    proc_inst_name = str(proc_inst_uri).replace(str(GLOSIS_PROC), '')

                    # Create she: mirror of the procedure
                    she_proc_uri = SHE[proc_inst_name]

                    # Add the procedure concept if not already added
                    if she_proc_uri not in added_procedures:
                        g.add((she_proc_uri, RDF.type, SKOS.Concept))
                        g.add((she_proc_uri, SKOS.exactMatch, proc_inst_uri))

                        # Get prefLabel from original
                        pref_labels = list(proc_graph.objects(proc_inst_uri, SKOS.prefLabel))
                        if pref_labels:
                            g.add((she_proc_uri, SKOS.prefLabel, pref_labels[0]))
                        else:
                            # Generate from name
                            label = camel_to_words(proc_inst_name)
                            g.add((she_proc_uri, SKOS.prefLabel, Literal(label, lang='en')))

                        # Get definition from original
                        definitions = list(proc_graph.objects(proc_inst_uri, SKOS.definition))
                        if definitions:
                            g.add((she_proc_uri, SKOS.definition, definitions[0]))

                        added_procedures.add(she_proc_uri)
                        print(f"  Added procedure: {proc_inst_name}")

                    # Link the layer horizon concept to the procedure
                    g.add((she_concept, has_procedure, she_proc_uri))
                    print(f"  Linked: {class_name} -> {proc_inst_name}")

    # Add procedure hierarchies (broader/narrower relationships)
    print("\nAdding procedure hierarchies...")
    for parent_uri, children_uris in procedure_hierarchies.items():
        parent_name = str(parent_uri).replace(str(GLOSIS_PROC), '')
        she_parent = SHE[parent_name]

        # Make sure parent is added
        if she_parent not in added_procedures:
            g.add((she_parent, RDF.type, SKOS.Concept))
            g.add((she_parent, SKOS.exactMatch, parent_uri))

            pref_labels = list(proc_graph.objects(parent_uri, SKOS.prefLabel))
            if pref_labels:
                g.add((she_parent, SKOS.prefLabel, pref_labels[0]))
            else:
                label = camel_to_words(parent_name)
                g.add((she_parent, SKOS.prefLabel, Literal(label, lang='en')))

            definitions = list(proc_graph.objects(parent_uri, SKOS.definition))
            if definitions:
                g.add((she_parent, SKOS.definition, definitions[0]))

            added_procedures.add(she_parent)

        for child_uri in children_uris:
            child_name = str(child_uri).replace(str(GLOSIS_PROC), '')
            she_child = SHE[child_name]

            # Make sure child is added
            if she_child not in added_procedures:
                g.add((she_child, RDF.type, SKOS.Concept))
                g.add((she_child, SKOS.exactMatch, child_uri))

                pref_labels = list(proc_graph.objects(child_uri, SKOS.prefLabel))
                if pref_labels:
                    g.add((she_child, SKOS.prefLabel, pref_labels[0]))
                else:
                    label = camel_to_words(child_name)
                    g.add((she_child, SKOS.prefLabel, Literal(label, lang='en')))

                definitions = list(proc_graph.objects(child_uri, SKOS.definition))
                if definitions:
                    g.add((she_child, SKOS.definition, definitions[0]))

                added_procedures.add(she_child)

            # Add broader/narrower relationships
            g.add((she_child, SKOS.broader, she_parent))
            g.add((she_parent, SKOS.narrower, she_child))
            print(f"  {parent_name} -> {child_name}")

    print(f"\nTotal procedures added: {len(added_procedures)}")

    # Serialize to file
    g.serialize(destination=output_file, format='turtle')
    print(f"\nEnriched SKOS file saved to: {output_file}")

def main():
    # File paths
    layer_horizon_ttl = 'ontovocabs/glosis/glosis_ori/glosis_layer_horizon.ttl'
    procedure_ttl = 'ontovocabs/glosis/glosis_ori/glosis_procedure.ttl'
    input_skos = 'ontovocabs/glosis/glosis_skos_hier/glosis_layer_horizon_skos_hierarchical.ttl'
    output_skos = 'ontovocabs/glosis/glosis_skos_hier/glosis_layer_horizon_skos_hierarchical_with_procedures.ttl'

    # Parse mappings
    class_to_procedure = parse_class_to_procedure_mapping(layer_horizon_ttl)

    # Parse procedure instances and hierarchies
    procedure_instances, procedure_hierarchies, all_procedure_uris, proc_graph = parse_procedure_instances(procedure_ttl)

    # Create enriched SKOS file
    create_enriched_skos(input_skos, output_skos, class_to_procedure, procedure_instances,
                        procedure_hierarchies, all_procedure_uris, proc_graph)

if __name__ == '__main__':
    main()
