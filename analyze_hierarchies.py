#!/usr/bin/env python3
"""
Analyze SKOS concepts and suggest hierarchies based on shared prefixes
"""
import re
from collections import defaultdict

def extract_concepts_from_skos(file_path):
    """Extract all concept names from a SKOS file"""
    concepts = []
    with open(file_path, 'r') as f:
        for line in f:
            match = re.match(r'she:(\w+)\s+a\s+skos:Concept', line)
            if match:
                concepts.append(match.group(1))
    return sorted(set(concepts))

def find_shared_prefixes(concepts, min_length=2, min_count=2):
    """Find prefixes shared by multiple concepts"""
    prefix_groups = defaultdict(list)

    for concept in concepts:
        # Try all possible prefix lengths from longest to shortest
        for length in range(len(concept)-1, min_length-1, -1):
            prefix = concept[:length]
            # Check if this could be a meaningful prefix
            # (ends at a capital letter or is the full word before a capital)
            if length < len(concept):
                next_char = concept[length]
                if next_char.isupper() or next_char.islower():
                    prefix_groups[prefix].append(concept)

    # Filter to only keep prefixes with multiple matches
    meaningful_prefixes = {}
    for prefix, matches in prefix_groups.items():
        if len(matches) >= min_count:
            # Check if this isn't already covered by a longer prefix
            is_best = True
            for other_prefix in prefix_groups:
                if other_prefix != prefix and other_prefix.startswith(prefix) and set(matches).issubset(set(prefix_groups[other_prefix])):
                    is_best = False
                    break
            if is_best:
                meaningful_prefixes[prefix] = matches

    return meaningful_prefixes

def analyze_module(module_name, file_path):
    """Analyze a module and suggest hierarchies"""
    print(f"\n{'='*70}")
    print(f"Module: {module_name}")
    print(f"{'='*70}")

    concepts = extract_concepts_from_skos(file_path)
    print(f"Total concepts: {len(concepts)}")

    # Find hierarchies
    prefixes = find_shared_prefixes(concepts)

    hierarchies = {}
    for prefix, members in sorted(prefixes.items(), key=lambda x: len(x[1]), reverse=True):
        # Filter out members that are exactly the prefix itself
        children = [m for m in members if m != prefix]
        if len(children) >= 2:
            hierarchies[prefix] = children

    print(f"\nSuggested hierarchies ({len(hierarchies)}):")
    for prefix, children in sorted(hierarchies.items()):
        # Check if prefix itself is a concept
        is_concept = prefix in concepts
        marker = " (concept)" if is_concept else " (group)"
        print(f"\n  {prefix}{marker}:")
        for child in sorted(children):
            print(f"    - {child}")

    return hierarchies

def main():
    modules = [
        ('common', '/home/user/soil-vocabs/ontovocabs/glosis/glosis_skos/glosis_common_skos.ttl'),
        ('surface', '/home/user/soil-vocabs/ontovocabs/glosis/glosis_skos/glosis_surface_skos.ttl'),
        ('siteplot', '/home/user/soil-vocabs/ontovocabs/glosis/glosis_skos/glosis_siteplot_skos.ttl'),
        ('profile', '/home/user/soil-vocabs/ontovocabs/glosis/glosis_skos/glosis_profile_skos.ttl'),
        ('layer_horizon', '/home/user/soil-vocabs/ontovocabs/glosis/glosis_skos/glosis_layer_horizon_skos.ttl')
    ]

    all_hierarchies = {}
    for module_name, file_path in modules:
        hierarchies = analyze_module(module_name, file_path)
        all_hierarchies[module_name] = hierarchies

    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    for module_name, hierarchies in all_hierarchies.items():
        print(f"{module_name}: {len(hierarchies)} hierarchies")

if __name__ == '__main__':
    main()
