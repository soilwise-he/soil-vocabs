#!/usr/bin/env python3
"""
Generate enhanced interactive HTML mind map from SoilVoc.ttl with:
- skos:definition display
- skos:exactMatch with clickable links
- Copy URI button for concepts
- she:hasProcedure relationships
- Visual differentiation for procedures
"""

from rdflib import Graph, Namespace, URIRef, BNode
from rdflib.namespace import SKOS, DCTERMS, RDF, RDFS, SDO
import json
import traceback

SHE = Namespace("https://soilwise-he.github.io/soil-health#")

def parse_skos_vocabulary_enhanced(ttl_file_path):
    """
    Parse a SKOS vocabulary from a Turtle file and extract the hierarchy with procedures.

    Args:
        ttl_file_path: Path to the .ttl file

    Returns:
        dict: Dictionary containing the vocabulary structure
    """
    # Load the graph
    g = Graph()
    g.parse(ttl_file_path, format='turtle')

    # Find the ConceptScheme
    concept_schemes = list(g.subjects(RDF.type, SKOS.ConceptScheme))

    if not concept_schemes:
        raise ValueError("No SKOS ConceptScheme found in the file")

    # Use the first ConceptScheme
    scheme = concept_schemes[0]

    # Get scheme information
    scheme_label = str(g.value(scheme, SKOS.prefLabel) or
                      g.value(scheme, RDFS.label) or
                      scheme.split('/')[-1].split('#')[-1])

    # Find top concepts
    top_concepts = []

    # Try hasTopConcept property
    for top_concept in g.objects(scheme, SKOS.hasTopConcept):
        top_concepts.append(top_concept)

    # Try topConceptOf property (inverse)
    for top_concept in g.subjects(SKOS.topConceptOf, scheme):
        if top_concept not in top_concepts:
            top_concepts.append(top_concept)

    # If no top concepts found, find concepts with no broader concepts
    if not top_concepts:
        all_concepts = set(g.subjects(RDF.type, SKOS.Concept))
        concepts_with_broader = set(g.subjects(SKOS.broader, None))
        top_concepts = list(all_concepts - concepts_with_broader)

    def pick_text_literal(defn_node):
        texts = list(g.objects(defn_node, SDO.text))
        if not texts:
            texts = list(g.objects(defn_node, RDF.value))
        if not texts:
            return None
        for t in texts:
            if getattr(t, 'language', None) == 'en':
                return t
        return texts[0]

    # Build the hierarchy
    def get_concept_info(concept_uri):
        """Extract information about a concept."""
        pref_label = g.value(concept_uri, SKOS.prefLabel)
        alt_label = g.value(concept_uri, SKOS.altLabel)
        notation = g.value(concept_uri, SKOS.notation)

        label = str(pref_label or concept_uri.split('/')[-1].split('#')[-1])
        alt_label_str = str(alt_label) if alt_label else None

        # Get definitions and sources (blank node structure)
        definitions = []
        for defn in g.objects(concept_uri, SKOS.definition):
            if isinstance(defn, BNode):
                text_literal = pick_text_literal(defn)
                text = str(text_literal) if text_literal else None
                source_val = g.value(defn, DCTERMS.source)
                source = str(source_val) if source_val else None
                if text:
                    definitions.append({
                        'text': text,
                        'source': source
                    })
            else:
                definitions.append({
                    'text': str(defn),
                    'source': None
                })

        # Get exactMatch links
        exact_matches = []
        for match_uri in g.objects(concept_uri, SKOS.exactMatch):
            match_str = str(match_uri)
            # Extract a readable label from the URI
            match_label = match_str.split('/')[-1].split('#')[-1]
            exact_matches.append({
                'uri': match_str,
                'label': match_label
            })

        # Check if this is a procedure (exactMatch to glosis_proc)
        is_procedure = any('glosis/model/procedure/' in m['uri'] for m in exact_matches)

        # Get narrower concepts
        narrower = list(g.objects(concept_uri, SKOS.narrower))

        # Also check for concepts that have this as broader (inverse)
        for concept in g.subjects(SKOS.broader, concept_uri):
            if concept not in narrower:
                narrower.append(concept)

        # Get procedures linked via she:hasProcedure
        procedures = []
        for proc_uri in g.objects(concept_uri, SHE.hasProcedure):
            proc_info = get_concept_info(proc_uri)
            procedures.append(proc_info)

        concept_info = {
            'uri': str(concept_uri),
            'label': label,
            'altLabel': alt_label_str,
            'notation': str(notation) if notation else None,
            'definition': definitions[0]['text'] if definitions else None,
            'definitions': definitions,
            'exactMatch': exact_matches,
            'isProcedure': is_procedure,
            'procedures': procedures,
            'narrower': [get_concept_info(n) for n in narrower] if narrower else []
        }

        return concept_info

    # Build the structure
    vocabulary = {
        'scheme_uri': str(scheme),
        'scheme_label': scheme_label,
        'top_concepts': [get_concept_info(tc) for tc in top_concepts]
    }

    return vocabulary


def generate_html_mindmap_enhanced(vocabulary_data, output_file='index.html'):
    """
    Generate an enhanced interactive HTML mind map from the vocabulary data.

    Args:
        vocabulary_data: Dictionary containing the vocabulary structure
        output_file: Output HTML file path
    """
    html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{vocabulary_data['scheme_label']}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #5a8e6b 0%, #8b6f47 100%);
            min-height: 100vh;
            padding: 20px;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: #faf8f3;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
            overflow: hidden;
        }}

        .header {{
            background: linear-gradient(135deg, #4a7c59 0%, #5a8e6b 100%);
            color: white;
            padding: 40px;
            text-align: center;
            border-bottom: 4px solid #8b6f47;
        }}

        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 12px;
            font-weight: 700;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.2);
        }}

        .header p {{
            opacity: 0.95;
            font-size: 1.15em;
            font-weight: 300;
        }}

        .mindmap {{
            padding: 40px;
            overflow-x: auto;
        }}

        .concept {{
            margin: 10px 0;
            animation: fadeIn 0.3s ease-in;
        }}

        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateX(-10px); }}
            to {{ opacity: 1; transform: translateX(0); }}
        }}

        .concept-header {{
            display: flex;
            align-items: center;
            padding: 12px 16px;
            background: #ffffff;
            border-left: 4px solid #5a8e6b;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.2s ease;
            margin-bottom: 5px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
        }}

        .concept-header.procedure {{
            background: #fff8e8;
            border-left-color: #d4a259;
        }}

        .concept-header.procedure:hover {{
            background: #ffedc9;
            border-left-color: #c4923f;
        }}

        .concept-header:hover {{
            background: #f0f5f1;
            border-left-color: #4a7c59;
            transform: translateX(5px);
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
        }}

        .concept-header.active {{
            background: #5a8e6b;
            color: white;
            border-left-color: #4a7c59;
        }}

        .concept-header.procedure.active {{
            background: #d4a259;
            color: #2c1810;
            border-left-color: #c4923f;
        }}

        .concept-header.highlighted {{
            background: #d4a259;
            border-left-color: #c4923f;
            animation: pulse 1s ease-in-out;
        }}

        @keyframes pulse {{
            0%, 100% {{ transform: scale(1); }}
            50% {{ transform: scale(1.02); }}
        }}

        .concept-header.no-children {{
            cursor: default;
            border-left-color: #a8b5a3;
        }}

        .concept-header.no-children:hover {{
            background: #ffffff;
            transform: none;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
        }}

        .concept-header.procedure.no-children:hover {{
            background: #fff8e8;
            transform: none;
        }}

        .toggle-icon {{
            width: 24px;
            height: 24px;
            margin-right: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
            font-weight: bold;
            transition: transform 0.2s ease;
        }}

        .toggle-icon.expanded {{
            transform: rotate(90deg);
        }}

        .concept-label {{
            flex: 1;
            font-weight: 500;
            font-size: 1.05em;
        }}

        .concept-alt-label {{
            display: block;
            font-size: 0.85em;
            font-weight: 400;
            color: #6c757d;
            font-style: italic;
            margin-top: 2px;
        }}

        .concept-header.active .concept-alt-label {{
            color: rgba(255, 255, 255, 0.85);
        }}

        .concept-header.procedure.active .concept-alt-label {{
            color: rgba(44, 24, 16, 0.85);
        }}

        .copy-uri-btn {{
            background: rgba(90, 142, 107, 0.1);
            color: #4a7c59;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            margin-left: 8px;
            cursor: pointer;
            transition: all 0.2s ease;
            border: 1px solid transparent;
        }}

        .copy-uri-btn:hover {{
            background: #5a8e6b;
            color: white;
            border-color: #5a8e6b;
        }}

        .concept-header.active .copy-uri-btn {{
            background: rgba(255, 255, 255, 0.2);
            color: white;
        }}

        .concept-header.active .copy-uri-btn:hover {{
            background: rgba(255, 255, 255, 0.3);
        }}

        .concept-notation {{
            background: rgba(90, 142, 107, 0.15);
            color: #3d6b4d;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 0.9em;
            font-weight: 600;
            margin-right: 10px;
        }}

        .concept-header.active .concept-notation {{
            background: rgba(255, 255, 255, 0.2);
            color: white;
        }}

        .concept-count {{
            background: rgba(90, 142, 107, 0.15);
            color: #3d6b4d;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: 600;
        }}

        .concept-header.active .concept-count {{
            background: rgba(255, 255, 255, 0.2);
            color: white;
        }}

        .concept-children {{
            margin-left: 30px;
            border-left: 2px solid #d4e0cf;
            padding-left: 20px;
            display: none;
        }}

        .concept-children.expanded {{
            display: block;
        }}

        .concept-definition {{
            margin: 5px 0 10px 54px;
            padding: 10px 15px;
            background: #f0f5f1;
            border-radius: 4px;
            font-size: 0.9em;
            color: #3d5a3f;
            font-style: normal;
            font-weight: 500;
            display: none;
            border-left: 3px solid #a8b5a3;
        }}

        .definition-item {{
            margin-bottom: 6px;
        }}

        .definition-item:last-child {{
            margin-bottom: 0;
        }}

        .definition-source-label {{
            margin-left: 6px;
            font-size: 0.85em;
            color: #6b5840;
            font-style: normal;
        }}

        .definition-source-link {{
            color: #4a7c59;
            text-decoration: none;
            font-style: normal;
            font-size: 0.75em;
            font-weight: 600;
            padding: 2px 6px;
            border-radius: 4px;
            background: rgba(90, 142, 107, 0.12);
        }}

        .definition-source-link:hover {{
            text-decoration: underline;
        }}

        .concept-definition.show {{
            display: block;
        }}

        .exact-match-info {{
            margin: 5px 0 10px 54px;
            padding: 8px 12px;
            background: #e8f4f0;
            border-left: 3px solid #4a7c59;
            border-radius: 4px;
            font-size: 0.85em;
            color: #2c4a35;
            display: none;
        }}

        .exact-match-info.show {{
            display: block;
        }}

        .exact-match-link {{
            color: #4a7c59;
            text-decoration: underline;
            cursor: pointer;
            font-weight: 500;
        }}

        .exact-match-link:hover {{
            color: #3d6b4d;
        }}

        .procedure-badge {{
            background: #d4a259;
            color: #2c1810;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 0.75em;
            font-weight: 700;
            margin-left: 8px;
            text-transform: uppercase;
        }}

        .procedures-section {{
            margin: 5px 0 10px 54px;
            padding: 10px 15px;
            background: #fff8e8;
            border-left: 3px solid #d4a259;
            border-radius: 4px;
            font-size: 0.9em;
            display: none;
        }}

        .procedures-section.show {{
            display: block;
        }}

        .procedures-title {{
            font-weight: 600;
            color: #8b6f47;
            margin-bottom: 8px;
        }}

        .top-level {{
            margin-left: 0;
            padding-left: 0;
            border-left: none;
        }}

        .stats {{
            padding: 20px 40px;
            background: linear-gradient(135deg, #f0f5f1 0%, #f5f1e8 100%);
            border-top: 3px solid #8b6f47;
            display: flex;
            justify-content: space-around;
            flex-wrap: wrap;
        }}

        .stat-item {{
            text-align: center;
            padding: 10px;
        }}

        .stat-value {{
            font-size: 2em;
            font-weight: bold;
            color: #5a8e6b;
            text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.05);
        }}

        .stat-label {{
            color: #6b5840;
            font-size: 0.9em;
            margin-top: 5px;
            font-weight: 500;
        }}

        .search-box {{
            padding: 20px 40px;
            background: linear-gradient(135deg, #f5f1e8 0%, #f0f5f1 100%);
            border-bottom: 2px solid #d4e0cf;
        }}

        .search-input {{
            width: 100%;
            padding: 12px 20px;
            font-size: 1em;
            border: 2px solid #d4e0cf;
            border-radius: 6px;
            transition: all 0.2s ease;
            background: white;
        }}

        .search-input:focus {{
            outline: none;
            border-color: #5a8e6b;
            box-shadow: 0 0 0 3px rgba(90, 142, 107, 0.15);
        }}

        .search-results {{
            margin-top: 15px;
            display: none;
        }}

        .search-results.show {{
            display: block;
        }}

        .search-result-item {{
            padding: 10px 15px;
            background: white;
            border: 1px solid #d4e0cf;
            border-radius: 6px;
            margin-bottom: 8px;
            cursor: pointer;
            transition: all 0.2s ease;
        }}

        .search-result-item:hover {{
            background: #f0f5f1;
            border-color: #5a8e6b;
            transform: translateX(5px);
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.1);
        }}

        .search-result-label {{
            font-weight: 500;
            color: #2c3e2d;
        }}

        .search-result-notation {{
            display: inline-block;
            background: rgba(90, 142, 107, 0.15);
            color: #3d6b4d;
            padding: 2px 8px;
            border-radius: 3px;
            font-size: 0.85em;
            font-weight: 600;
            margin-right: 8px;
        }}

        .search-result-path {{
            font-size: 0.85em;
            color: #6b5840;
            margin-top: 5px;
        }}

        .search-info {{
            padding: 10px 15px;
            background: #e8f4f0;
            border: 1px solid #a8cbba;
            border-radius: 6px;
            color: #2c4a35;
            font-size: 0.9em;
            margin-bottom: 10px;
        }}

        .no-results {{
            text-align: center;
            padding: 40px;
            color: #6b5840;
            font-style: italic;
        }}

        .clear-search {{
            display: inline-block;
            margin-top: 10px;
            padding: 8px 16px;
            background: #5a8e6b;
            color: white;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.9em;
            transition: all 0.2s ease;
        }}

        .clear-search:hover {{
            background: #4a7c59;
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.15);
        }}

        .toast {{
            position: fixed;
            bottom: 30px;
            right: 30px;
            background: #5a8e6b;
            color: white;
            padding: 12px 24px;
            border-radius: 6px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
            opacity: 0;
            transition: opacity 0.3s ease;
            pointer-events: none;
            z-index: 1000;
        }}

        .toast.show {{
            opacity: 1;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🌱 SoilVoc</h1>
            <p>Interactive Soil Vocabulary · <a href="https://soilwise-he.eu" target="_blank">SoilWise-HE Project</a></p>
        </div>

        <div class="search-box">
            <input type="text" class="search-input" id="searchInput" placeholder="Search all concepts by label or notation...">
            <div class="search-results" id="searchResults"></div>
        </div>

        <div class="mindmap" id="mindmap">
            <!-- Mind map will be generated here -->
        </div>

        <div class="stats" id="stats">
            <!-- Statistics will be generated here -->
        </div>
    </div>

    <div class="toast" id="toast">URI copied to clipboard!</div>

    <script>
        const vocabularyData = {json.dumps(vocabulary_data, indent=2)};

        let allConcepts = [];
        let uniqueConceptUris = new Set();
        let conceptMap = new Map(); // Maps URI to concept object with path info

        function buildConceptMap(concepts, path = []) {{
            concepts.forEach(concept => {{
                const currentPath = [...path, concept];

                // Store concept with its path
                if (!conceptMap.has(concept.uri)) {{
                    conceptMap.set(concept.uri, {{
                        concept: concept,
                        path: currentPath
                    }});
                }}

                uniqueConceptUris.add(concept.uri);
                allConcepts.push(concept);

                if (concept.narrower && concept.narrower.length > 0) {{
                    buildConceptMap(concept.narrower, currentPath);
                }}

                if (concept.procedures && concept.procedures.length > 0) {{
                    buildConceptMap(concept.procedures, currentPath);
                }}
            }});
        }}

        function countConcepts(concepts) {{
            concepts.forEach(concept => {{
                uniqueConceptUris.add(concept.uri);
                allConcepts.push(concept);
                if (concept.narrower && concept.narrower.length > 0) {{
                    countConcepts(concept.narrower);
                }}
                if (concept.procedures && concept.procedures.length > 0) {{
                    countConcepts(concept.procedures);
                }}
            }});
            return uniqueConceptUris.size;
        }}

        function getMaxDepth(concepts, depth = 1) {{
            let maxDepth = depth;
            concepts.forEach(concept => {{
                if (concept.narrower && concept.narrower.length > 0) {{
                    maxDepth = Math.max(maxDepth, getMaxDepth(concept.narrower, depth + 1));
                }}
                if (concept.procedures && concept.procedures.length > 0) {{
                    maxDepth = Math.max(maxDepth, getMaxDepth(concept.procedures, depth + 1));
                }}
            }});
            return maxDepth;
        }}

        function copyToClipboard(text) {{
            navigator.clipboard.writeText(text).then(() => {{
                showToast();
            }}).catch(err => {{
                console.error('Failed to copy:', err);
            }});
        }}

        function showToast() {{
            const toast = document.getElementById('toast');
            toast.classList.add('show');
            setTimeout(() => {{
                toast.classList.remove('show');
            }}, 2000);
        }}

        function renderConcept(concept, level = 0) {{
            const hasNarrower = concept.narrower && concept.narrower.length > 0;
            const hasProcedures = concept.procedures && concept.procedures.length > 0;
            const hasChildren = hasNarrower || hasProcedures;
            const hasDefinition = (concept.definitions && concept.definitions.length > 0) ||
                (concept.definition !== null && concept.definition !== undefined && concept.definition !== '');
            const hasExactMatch = concept.exactMatch && concept.exactMatch.length > 0;

            // Concept is clickable if it has children OR has definition/exactMatch
            const isClickable = hasChildren || hasDefinition || hasExactMatch;

            const notation = concept.notation ? `<span class="concept-notation">${{concept.notation}}</span>` : '';
            const procedureBadge = concept.isProcedure ? '<span class="procedure-badge">Procedure</span>' : '';
            const altLabelHtml = concept.altLabel ? `<span class="concept-alt-label">${{concept.altLabel}}</span>` : '';
            const childrenCount = hasNarrower ? concept.narrower.length + (hasProcedures ? concept.procedures.length : 0) : (hasProcedures ? concept.procedures.length : 0);
            const count = hasChildren ? `<span class="concept-count">${{childrenCount}}</span>` : '';
            const noChildClass = !isClickable ? 'no-children' : '';
            const procedureClass = concept.isProcedure ? 'procedure' : '';
            const toggleIcon = hasChildren ? '▶' : '●';

            let html = `
                <div class="concept" data-uri="${{concept.uri}}">
                    <div class="concept-header ${{noChildClass}} ${{procedureClass}}" onclick="toggleConcept(this)">
                        <span class="toggle-icon">${{toggleIcon}}</span>
                        ${{notation}}
                        <span class="concept-label">${{concept.label}}${{procedureBadge}}${{altLabelHtml}}</span>
                        <button class="copy-uri-btn" onclick="event.stopPropagation(); copyToClipboard('${{concept.uri}}')">📋 Copy URI</button>
                        ${{count}}
                    </div>
            `;

            if (concept.definitions && concept.definitions.length > 0) {{
                const defItems = concept.definitions.map(d => {{
                    const sourceHtml = d.source
                        ? ` <a href="${{d.source}}" target="_blank" class="definition-source-link" title="Source">source</a>`
                        : '';
                    return `<div class="definition-item">${{d.text}}${{sourceHtml}}</div>`;
                }}).join('');
                html += `<div class="concept-definition">${{defItems}}</div>`;
            }} else if (concept.definition) {{
                html += `<div class="concept-definition">${{concept.definition}}</div>`;
            }}

            if (concept.exactMatch && concept.exactMatch.length > 0) {{
                const exactMatchLinks = concept.exactMatch.map(m =>
                    `<a href="${{m.uri}}" target="_blank" class="exact-match-link">${{m.label}}</a>`
                ).join(', ');
                html += `<div class="exact-match-info">See also: ${{exactMatchLinks}}</div>`;
            }}

            if (hasProcedures) {{
                html += `<div class="procedures-section">
                    <div class="procedures-title">📋 Procedures:</div>
                    <div class="concept-children">`;
                concept.procedures.forEach(proc => {{
                    html += renderConcept(proc, level + 1);
                }});
                html += `</div></div>`;
            }}

            if (hasNarrower) {{
                html += `<div class="concept-children">`;
                concept.narrower.forEach(narrower => {{
                    html += renderConcept(narrower, level + 1);
                }});
                html += `</div>`;
            }}

            html += `</div>`;
            return html;
        }}

        function toggleConcept(header) {{
            const concept = header.parentElement;
            const children = concept.querySelectorAll(':scope > .concept-children');
            const definition = concept.querySelector(':scope > .concept-definition');
            const exactMatch = concept.querySelector(':scope > .exact-match-info');
            const procedures = concept.querySelector(':scope > .procedures-section');
            const icon = header.querySelector('.toggle-icon');

            // Check if there's anything to show
            const hasChildren = children.length > 0;
            const hasDefinition = definition !== null;
            const hasExactMatch = exactMatch !== null;
            const hasProcedures = procedures !== null;

            // If no children and no info to display, do nothing
            if (!hasChildren && !hasDefinition && !hasExactMatch && !hasProcedures) {{
                return;
            }}

            const isExpanding = !header.classList.contains('active');

            children.forEach(childDiv => {{
                childDiv.classList.toggle('expanded');
            }});

            header.classList.toggle('active');
            if (hasChildren || hasProcedures) {{
                icon.classList.toggle('expanded');
            }}

            if (definition) {{
                definition.classList.toggle('show');
            }}

            if (exactMatch) {{
                exactMatch.classList.toggle('show');
            }}

            if (procedures) {{
                procedures.classList.toggle('show');
                const procChildren = procedures.querySelector('.concept-children');
                if (procChildren && isExpanding) {{
                    procChildren.classList.add('expanded');
                }}
            }}
        }}

        function renderMindmap() {{
            const mindmapDiv = document.getElementById('mindmap');
            let html = '<div class="top-level">';

            vocabularyData.top_concepts.forEach(concept => {{
                html += renderConcept(concept, 0);
            }});

            html += '</div>';
            mindmapDiv.innerHTML = html;
        }}

        function renderStats() {{
            const totalConcepts = countConcepts(vocabularyData.top_concepts);
            const maxDepth = getMaxDepth(vocabularyData.top_concepts);
            const topConceptsCount = vocabularyData.top_concepts.length;

            const statsDiv = document.getElementById('stats');
            statsDiv.innerHTML = `
                <div class="stat-item">
                    <div class="stat-value">${{topConceptsCount}}</div>
                    <div class="stat-label">Top Concepts</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">${{totalConcepts}}</div>
                    <div class="stat-label">Total Concepts</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">${{maxDepth}}</div>
                    <div class="stat-label">Max Depth</div>
                </div>
            `;
        }}

        function searchConcepts() {{
            const searchTerm = document.getElementById('searchInput').value.toLowerCase().trim();
            const searchResultsDiv = document.getElementById('searchResults');

            if (searchTerm === '') {{
                searchResultsDiv.classList.remove('show');
                searchResultsDiv.innerHTML = '';
                clearHighlights();
                return;
            }}

            // Search in all concepts
            const matches = [];
            conceptMap.forEach((data, uri) => {{
                const concept = data.concept;
                const label = concept.label.toLowerCase();
                const altLabel = concept.altLabel ? concept.altLabel.toLowerCase() : '';
                const notation = concept.notation ? concept.notation.toLowerCase() : '';

                if (label.includes(searchTerm) || altLabel.includes(searchTerm) || notation.includes(searchTerm)) {{
                    matches.push({{
                        uri: uri,
                        concept: concept,
                        path: data.path
                    }});
                }}
            }});

            // Display results
            if (matches.length > 0) {{
                let html = `<div class="search-info">Found ${{matches.length}} matching concept(s). Click to navigate.</div>`;

                matches.forEach(match => {{
                    const pathLabels = match.path.map(c => c.notation ? `${{c.notation}} ${{c.label}}` : c.label).join(' → ');
                    const notation = match.concept.notation ? `<span class="search-result-notation">${{match.concept.notation}}</span>` : '';

                    html += `
                        <div class="search-result-item" onclick="navigateToConcept('${{match.uri}}')">
                            <div class="search-result-label">
                                ${{notation}}${{match.concept.label}}
                            </div>
                            <div class="search-result-path">${{pathLabels}}</div>
                        </div>
                    `;
                }});

                html += `<div class="clear-search" onclick="clearSearch()">Clear Search</div>`;
                searchResultsDiv.innerHTML = html;
                searchResultsDiv.classList.add('show');
            }} else {{
                searchResultsDiv.innerHTML = `
                    <div class="search-info">No concepts found matching "${{searchTerm}}".</div>
                    <div class="clear-search" onclick="clearSearch()">Clear Search</div>
                `;
                searchResultsDiv.classList.add('show');
            }}
        }}

        function navigateToConcept(targetUri) {{
            // Get the path to this concept
            const conceptData = conceptMap.get(targetUri);
            if (!conceptData) return;

            // First, collapse everything
            document.querySelectorAll('.concept-children.expanded').forEach(el => {{
                el.classList.remove('expanded');
            }});
            document.querySelectorAll('.concept-header.active').forEach(el => {{
                el.classList.remove('active');
            }});
            document.querySelectorAll('.toggle-icon.expanded').forEach(el => {{
                el.classList.remove('expanded');
            }});
            document.querySelectorAll('.concept-definition.show').forEach(el => {{
                el.classList.remove('show');
            }});
            document.querySelectorAll('.exact-match-info.show').forEach(el => {{
                el.classList.remove('show');
            }});
            document.querySelectorAll('.procedures-section.show').forEach(el => {{
                el.classList.remove('show');
            }});

            // Clear previous highlights
            clearHighlights();

            // Expand the path to the target concept
            const path = conceptData.path;
            for (let i = 0; i < path.length - 1; i++) {{
                const conceptUri = path[i].uri;
                const conceptElement = document.querySelector(`.concept[data-uri="${{conceptUri}}"]`);

                if (conceptElement) {{
                    const header = conceptElement.querySelector('.concept-header');
                    const children = conceptElement.querySelectorAll(':scope > .concept-children');
                    const icon = header.querySelector('.toggle-icon');
                    const procedures = conceptElement.querySelector(':scope > .procedures-section');

                    children.forEach(childDiv => {{
                        if (!childDiv.classList.contains('expanded')) {{
                            childDiv.classList.add('expanded');
                        }}
                    }});

                    if (!header.classList.contains('active')) {{
                        header.classList.add('active');
                        icon.classList.add('expanded');
                    }}

                    if (procedures) {{
                        procedures.classList.add('show');
                        const procChildren = procedures.querySelector('.concept-children');
                        if (procChildren) {{
                            procChildren.classList.add('expanded');
                        }}
                    }}
                }}
            }}

            // Highlight and scroll to the target concept
            const targetElement = document.querySelector(`.concept[data-uri="${{targetUri}}"]`);
            if (targetElement) {{
                const targetHeader = targetElement.querySelector('.concept-header');
                targetHeader.classList.add('highlighted');

                // Show definition, exact match, procedures if exists
                const definition = targetElement.querySelector(':scope > .concept-definition');
                if (definition) {{
                    definition.classList.add('show');
                }}

                const exactMatch = targetElement.querySelector(':scope > .exact-match-info');
                if (exactMatch) {{
                    exactMatch.classList.add('show');
                }}

                const procedures = targetElement.querySelector(':scope > .procedures-section');
                if (procedures) {{
                    procedures.classList.add('show');
                    const procChildren = procedures.querySelector('.concept-children');
                    if (procChildren) {{
                        procChildren.classList.add('expanded');
                    }}
                }}

                // Scroll to the target
                targetElement.scrollIntoView({{ behavior: 'smooth', block: 'center' }});

                // Remove highlight after animation
                setTimeout(() => {{
                    targetHeader.classList.remove('highlighted');
                }}, 2000);
            }}
        }}

        function clearHighlights() {{
            document.querySelectorAll('.concept-header.highlighted').forEach(el => {{
                el.classList.remove('highlighted');
            }});
        }}

        function clearSearch() {{
            document.getElementById('searchInput').value = '';
            searchConcepts();
        }}

        // Initialize
        buildConceptMap(vocabularyData.top_concepts);
        renderMindmap();
        renderStats();

        // Search functionality with debounce
        let searchTimeout;
        document.getElementById('searchInput').addEventListener('input', () => {{
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(searchConcepts, 300);
        }});

        // Keyboard navigation
        document.addEventListener('keydown', (e) => {{
            if (e.key === 'Escape') {{
                clearSearch();
            }}
        }});
    </script>
</body>
</html>'''

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"Enhanced interactive mind map generated: {output_file}")


# Main execution
if __name__ == '__main__':
    ttl_file = 'SoilVoc.ttl'

    try:
        print(f"Parsing SKOS vocabulary from: {ttl_file}")
        vocabulary = parse_skos_vocabulary_enhanced(ttl_file)

        print(f"Found ConceptScheme: {vocabulary['scheme_label']}")
        print(f"Number of top concepts: {len(vocabulary['top_concepts'])}")

        output_file = 'index.html'
        generate_html_mindmap_enhanced(vocabulary, output_file)

        print(f"\nSuccess! Open {output_file} in your web browser to view the enhanced interactive mind map.")
        print("\nNew features:")
        print("- ✓ Definitions displayed for all concepts")
        print("- ✓ Exact matches shown with clickable links")
        print("- ✓ Copy URI button for each concept")
        print("- ✓ Procedures displayed in hierarchy")
        print("- ✓ Visual differentiation for procedures (yellow background)")

    except FileNotFoundError:
        print(f"Error: File '{ttl_file}' not found.")
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
