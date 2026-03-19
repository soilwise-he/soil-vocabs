// soilvoc.js — SoilVoc interactive vocabulary viewer
// Data is loaded at runtime from soilvoc_data.json

let vocabularyData = null;
let fragmentAliasMap = null;

        let allConcepts = [];
        let uniqueConceptUris = new Set();
        let conceptMap = new Map(); // Maps URI to concept object with all paths

        function pathKey(path) {
            return path.map(c => c.uri).join('>');
        }

        function pathKeyEncoded(path) {
            return encodeURIComponent(pathKey(path));
        }

        function buildConceptMap(concepts, path = []) {
            concepts.forEach(concept => {
                const currentPath = [...path, concept];
                const currentKey = pathKey(currentPath);

                // Store concept with all possible paths
                if (!conceptMap.has(concept.uri)) {
                    conceptMap.set(concept.uri, {
                        concept: concept,
                        paths: [currentPath],
                        pathKeys: new Set([currentKey])
                    });
                } else {
                    const data = conceptMap.get(concept.uri);
                    if (!data.pathKeys.has(currentKey)) {
                        data.paths.push(currentPath);
                        data.pathKeys.add(currentKey);
                    }
                }

                uniqueConceptUris.add(concept.uri);
                allConcepts.push(concept);

                if (concept.narrower && concept.narrower.length > 0) {
                    buildConceptMap(concept.narrower, currentPath);
                }

                if (concept.procedures && concept.procedures.length > 0) {
                    buildConceptMap(concept.procedures, currentPath);
                }
            });
        }

        function countConcepts(concepts) {
            concepts.forEach(concept => {
                uniqueConceptUris.add(concept.uri);
                allConcepts.push(concept);
                if (concept.narrower && concept.narrower.length > 0) {
                    countConcepts(concept.narrower);
                }
                if (concept.procedures && concept.procedures.length > 0) {
                    countConcepts(concept.procedures);
                }
            });
            return uniqueConceptUris.size;
        }

        function getMaxDepth(concepts, depth = 1) {
            let maxDepth = depth;
            concepts.forEach(concept => {
                if (concept.narrower && concept.narrower.length > 0) {
                    maxDepth = Math.max(maxDepth, getMaxDepth(concept.narrower, depth + 1));
                }
                if (concept.procedures && concept.procedures.length > 0) {
                    maxDepth = Math.max(maxDepth, getMaxDepth(concept.procedures, depth + 1));
                }
            });
            return maxDepth;
        }

        function copyToClipboard(text) {
            navigator.clipboard.writeText(text).then(() => {
                showToast();
            }).catch(err => {
                console.error('Failed to copy:', err);
            });
        }

        function showToast() {
            const toast = document.getElementById('toast');
            toast.classList.add('show');
            setTimeout(() => {
                toast.classList.remove('show');
            }, 2000);
        }

        function getConceptUriFromHash() {
            const rawHash = window.location.hash;
            if (!rawHash || rawHash === '#') {
                return null;
            }

            let fragment;
            try {
                fragment = decodeURIComponent(rawHash.slice(1)).trim();
            } catch (err) {
                console.warn('Failed to decode location hash:', err);
                return null;
            }

            if (!fragment) {
                return null;
            }

            const targetUri = `${vocabularyData.scheme_uri}#${fragment}`;
            if (conceptMap.has(targetUri)) {
                return targetUri;
            }

            const aliasTargetUri = fragmentAliasMap[fragment.toLowerCase()];
            return aliasTargetUri || null;
        }

        function handleHashNavigation() {
            const targetUri = getConceptUriFromHash();
            if (targetUri) {
                navigateToConcept(targetUri);
            }
        }

        function renderConcept(concept, level = 0, path = []) {
            const currentPath = [...path, concept];
            const currentPathKey = pathKeyEncoded(currentPath);
            const hasNarrower = concept.narrower && concept.narrower.length > 0;
            const hasProcedures = concept.procedures && concept.procedures.length > 0;
            const hasChildren = hasNarrower || hasProcedures;
            const hasDefinition = (concept.definitions && concept.definitions.length > 0) ||
                (concept.definition !== null && concept.definition !== undefined && concept.definition !== '');
            const hasExactMatch = concept.exactMatch && concept.exactMatch.length > 0;
            const hasCloseMatch = concept.closeMatch && concept.closeMatch.length > 0;

            // Concept is clickable if it has children OR has definition/matches
            const isClickable = hasChildren || hasDefinition || hasExactMatch || hasCloseMatch;

            const notation = concept.notation ? `<span class="concept-notation">${concept.notation}</span>` : '';
            const procedureBadge = concept.isProcedure ? '<span class="procedure-badge">Procedure</span>' : '';
            const altLabelHtml = concept.altLabel ? `<span class="concept-alt-label">${concept.altLabel}</span>` : '';
            const childrenCount = hasNarrower ? concept.narrower.length + (hasProcedures ? concept.procedures.length : 0) : (hasProcedures ? concept.procedures.length : 0);
            const count = hasChildren ? `<span class="concept-count">${childrenCount}</span>` : '';
            const noChildClass = !isClickable ? 'no-children' : '';
            const procedureClass = concept.isProcedure ? 'procedure' : '';
            const toggleIcon = hasChildren ? '▶' : '●';

            let html = `
                <div class="concept" data-uri="${concept.uri}" data-path-key="${currentPathKey}">
                    <div class="concept-header ${noChildClass} ${procedureClass}" onclick="toggleConcept(this)">
                        <span class="toggle-icon">${toggleIcon}</span>
                        ${notation}
                        <span class="concept-label">${concept.label}${procedureBadge}${altLabelHtml}</span>
                        <button class="copy-uri-btn" onclick="event.stopPropagation(); copyToClipboard('${concept.uri}')">📋 Copy URI</button>
                        ${count}
                    </div>
            `;

            if (concept.definitions && concept.definitions.length > 0) {
                const defItems = concept.definitions.map(d => {
                    const sourceHtml = d.source
                        ? ` <a href="${d.source}" target="_blank" class="definition-source-link" title="Source">source</a>`
                        : '';
                    return `<div class="definition-item">${d.text}${sourceHtml}</div>`;
                }).join('');
                html += `<div class="concept-definition">${defItems}</div>`;
            } else if (concept.definition) {
                html += `<div class="concept-definition">${concept.definition}</div>`;
            }

            if (concept.exactMatch && concept.exactMatch.length > 0) {
                const exactMatchLinks = concept.exactMatch.map(m =>
                    `<a href="${m.uri}" target="_blank" class="exact-match-link">${m.label}</a>`
                ).join(', ');
                html += `<div class="exact-match-info">See also: ${exactMatchLinks}</div>`;
            }

            if (concept.closeMatch && concept.closeMatch.length > 0) {
                const closeMatchLinks = concept.closeMatch.map(m =>
                    `<a href="${m.uri}" target="_blank" class="close-match-link">${m.label}</a>`
                ).join(', ');
                html += `<div class="close-match-info">Related terms: ${closeMatchLinks}</div>`;
            }

            if (hasProcedures) {
                html += `<div class="procedures-section">
                    <div class="procedures-title">📋 Procedures:</div>
                    <div class="concept-children">`;
                concept.procedures.forEach(proc => {
                    html += renderConcept(proc, level + 1, currentPath);
                });
                html += `</div></div>`;
            }

            if (hasNarrower) {
                html += `<div class="concept-children">`;
                concept.narrower.forEach(narrower => {
                    html += renderConcept(narrower, level + 1, currentPath);
                });
                html += `</div>`;
            }

            html += `</div>`;
            return html;
        }

        function toggleConcept(header) {
            const concept = header.parentElement;
            const children = concept.querySelectorAll(':scope > .concept-children');
            const definition = concept.querySelector(':scope > .concept-definition');
            const exactMatch = concept.querySelector(':scope > .exact-match-info');
            const closeMatch = concept.querySelector(':scope > .close-match-info');
            const procedures = concept.querySelector(':scope > .procedures-section');
            const icon = header.querySelector('.toggle-icon');

            // Check if there's anything to show
            const hasChildren = children.length > 0;
            const hasDefinition = definition !== null;
            const hasExactMatch = exactMatch !== null;
            const hasCloseMatch = closeMatch !== null;
            const hasProcedures = procedures !== null;

            // If no children and no info to display, do nothing
            if (!hasChildren && !hasDefinition && !hasExactMatch && !hasCloseMatch && !hasProcedures) {
                return;
            }

            const isExpanding = !header.classList.contains('active');

            children.forEach(childDiv => {
                childDiv.classList.toggle('expanded');
            });

            header.classList.toggle('active');
            if (hasChildren || hasProcedures) {
                icon.classList.toggle('expanded');
            }

            if (definition) {
                definition.classList.toggle('show');
            }

            if (exactMatch) {
                exactMatch.classList.toggle('show');
            }

            if (closeMatch) {
                closeMatch.classList.toggle('show');
            }

            if (procedures) {
                procedures.classList.toggle('show');
                const procChildren = procedures.querySelector('.concept-children');
                if (procChildren && isExpanding) {
                    procChildren.classList.add('expanded');
                }
            }
        }

        function renderMindmap() {
            const mindmapDiv = document.getElementById('mindmap');
            let html = '<div class="top-level">';

            vocabularyData.top_concepts.forEach(concept => {
                html += renderConcept(concept, 0);
            });

            html += '</div>';
            mindmapDiv.innerHTML = html;
        }

        function renderStats() {
            const totalConcepts = countConcepts(vocabularyData.top_concepts);
            const maxDepth = getMaxDepth(vocabularyData.top_concepts);
            const topConceptsCount = vocabularyData.top_concepts.length;

            const statsDiv = document.getElementById('stats');
            statsDiv.innerHTML = `
                <div class="stat-item">
                    <div class="stat-value">${topConceptsCount}</div>
                    <div class="stat-label">Top Concepts</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">${totalConcepts}</div>
                    <div class="stat-label">Total Concepts</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">${maxDepth}</div>
                    <div class="stat-label">Max Depth</div>
                </div>
            `;
        }

        function searchConcepts() {
            const searchTerm = document.getElementById('searchInput').value.toLowerCase().trim();
            const searchResultsDiv = document.getElementById('searchResults');

            if (searchTerm === '') {
                searchResultsDiv.classList.remove('show');
                searchResultsDiv.innerHTML = '';
                clearHighlights();
                return;
            }

            // Search in all concepts
            const matches = [];
            conceptMap.forEach((data, uri) => {
                const concept = data.concept;
                const label = concept.label.toLowerCase();
                const altLabel = concept.altLabel ? concept.altLabel.toLowerCase() : '';
                const notation = concept.notation ? concept.notation.toLowerCase() : '';

                if (label.includes(searchTerm) || altLabel.includes(searchTerm) || notation.includes(searchTerm)) {
                    matches.push({
                        uri: uri,
                        concept: concept,
                        paths: data.paths
                    });
                }
            });

            // Display results
            if (matches.length > 0) {
                let html = `<div class="search-info">Found ${matches.length} matching concept(s). Click a path to navigate.</div>`;

                matches.forEach(match => {
                    const notation = match.concept.notation ? `<span class="search-result-notation">${match.concept.notation}</span>` : '';
                    const pathItems = match.paths.map((path, index) => {
                        const pathLabels = path.map(c => c.notation ? `${c.notation} ${c.label}` : c.label).join(' → ');
                        return `<div class="search-result-path-item" data-uri="${match.uri}" data-path-index="${index}">${pathLabels}</div>`;
                    }).join('');

                    html += `
                        <div class="search-result-item" data-uri="${match.uri}">
                            <div class="search-result-label">
                                ${notation}${match.concept.label}
                            </div>
                            <div class="search-result-paths">${pathItems}</div>
                        </div>
                    `;
                });

                html += `<div class="clear-search" onclick="clearSearch()">Clear Search</div>`;
                searchResultsDiv.innerHTML = html;
                searchResultsDiv.classList.add('show');
            } else {
                // Build DOM nodes safely to avoid injecting user input into innerHTML
                searchResultsDiv.innerHTML = '';

                const infoDiv = document.createElement('div');
                infoDiv.className = 'search-info';
                infoDiv.textContent = `No concepts found matching "${searchTerm}".`;

                const clearDiv = document.createElement('div');
                clearDiv.className = 'clear-search';
                clearDiv.textContent = 'Clear Search';
                clearDiv.onclick = clearSearch;

                searchResultsDiv.appendChild(infoDiv);
                searchResultsDiv.appendChild(clearDiv);
                searchResultsDiv.classList.add('show');
            }
        }

        function navigateToConcept(targetUri, pathIndex = 0) {
            // Get the path to this concept
            const conceptData = conceptMap.get(targetUri);
            if (!conceptData) return;

            const paths = conceptData.paths && conceptData.paths.length > 0
                ? conceptData.paths
                : (conceptData.path ? [conceptData.path] : []);
            if (paths.length === 0) return;
            const safeIndex = Math.min(Math.max(pathIndex, 0), paths.length - 1);
            const path = paths[safeIndex];

            // First, collapse everything
            document.querySelectorAll('.concept-children.expanded').forEach(el => {
                el.classList.remove('expanded');
            });
            document.querySelectorAll('.concept-header.active').forEach(el => {
                el.classList.remove('active');
            });
            document.querySelectorAll('.toggle-icon.expanded').forEach(el => {
                el.classList.remove('expanded');
            });
            document.querySelectorAll('.concept-definition.show').forEach(el => {
                el.classList.remove('show');
            });
            document.querySelectorAll('.exact-match-info.show').forEach(el => {
                el.classList.remove('show');
            });
            document.querySelectorAll('.close-match-info.show').forEach(el => {
                el.classList.remove('show');
            });
            document.querySelectorAll('.procedures-section.show').forEach(el => {
                el.classList.remove('show');
            });

            // Clear previous highlights
            clearHighlights();

            // Expand the path to the target concept
            for (let i = 0; i < path.length - 1; i++) {
                const conceptUri = path[i].uri;
                const pathKeyValue = pathKeyEncoded(path.slice(0, i + 1));
                const conceptElement = document.querySelector(`.concept[data-path-key="${pathKeyValue}"]`)
                    || document.querySelector(`.concept[data-uri="${conceptUri}"]`);

                if (conceptElement) {
                    const header = conceptElement.querySelector('.concept-header');
                    const children = conceptElement.querySelectorAll(':scope > .concept-children');
                    const icon = header.querySelector('.toggle-icon');
                    const procedures = conceptElement.querySelector(':scope > .procedures-section');

                    children.forEach(childDiv => {
                        if (!childDiv.classList.contains('expanded')) {
                            childDiv.classList.add('expanded');
                        }
                    });

                    if (!header.classList.contains('active')) {
                        header.classList.add('active');
                        icon.classList.add('expanded');
                    }

                    if (procedures) {
                        procedures.classList.add('show');
                        const procChildren = procedures.querySelector('.concept-children');
                        if (procChildren) {
                            procChildren.classList.add('expanded');
                        }
                    }
                }
            }

            // Highlight and scroll to the target concept
            const targetPathKey = pathKeyEncoded(path);
            const targetElement = document.querySelector(`.concept[data-path-key="${targetPathKey}"]`)
                || document.querySelector(`.concept[data-uri="${targetUri}"]`);
            if (targetElement) {
                const targetHeader = targetElement.querySelector('.concept-header');
                targetHeader.classList.add('highlighted');

                // Show definition, exact match, procedures if exists
                const definition = targetElement.querySelector(':scope > .concept-definition');
                if (definition) {
                    definition.classList.add('show');
                }

                const exactMatch = targetElement.querySelector(':scope > .exact-match-info');
                if (exactMatch) {
                    exactMatch.classList.add('show');
                }

                const closeMatch = targetElement.querySelector(':scope > .close-match-info');
                if (closeMatch) {
                    closeMatch.classList.add('show');
                }

                const procedures = targetElement.querySelector(':scope > .procedures-section');
                if (procedures) {
                    procedures.classList.add('show');
                    const procChildren = procedures.querySelector('.concept-children');
                    if (procChildren) {
                        procChildren.classList.add('expanded');
                    }
                }

                // Scroll to the target
                targetElement.scrollIntoView({ behavior: 'smooth', block: 'center' });

                // Remove highlight after animation
                setTimeout(() => {
                    targetHeader.classList.remove('highlighted');
                }, 2000);
            }
        }

        function clearHighlights() {
            document.querySelectorAll('.concept-header.highlighted').forEach(el => {
                el.classList.remove('highlighted');
            });
        }

        function clearSearch() {
            document.getElementById('searchInput').value = '';
            searchConcepts();
        }


// Load vocabulary data and initialize the viewer
fetch('assets/soilvoc_data.json')
    .then(r => r.json())
    .then(data => {
        vocabularyData = data.vocabulary;
        fragmentAliasMap = data.fragment_alias_map;
        document.getElementById('version-tag').textContent = data.version || '';

        buildConceptMap(vocabularyData.top_concepts);
        renderMindmap();
        renderStats();
        handleHashNavigation();

        window.addEventListener('hashchange', () => {
            handleHashNavigation();
        });

        // Search results click handling (paths + items)
        const searchResultsDiv = document.getElementById('searchResults');
        searchResultsDiv.addEventListener('click', (e) => {
            const pathItem = e.target.closest('.search-result-path-item');
            if (pathItem && searchResultsDiv.contains(pathItem)) {
                e.stopPropagation();
                const uri = pathItem.getAttribute('data-uri');
                const idx = parseInt(pathItem.getAttribute('data-path-index'), 10);
                navigateToConcept(uri, Number.isFinite(idx) ? idx : 0);
                return;
            }

            const resultItem = e.target.closest('.search-result-item');
            if (resultItem && searchResultsDiv.contains(resultItem)) {
                const uri = resultItem.getAttribute('data-uri');
                if (uri) {
                    navigateToConcept(uri);
                }
            }
        });

        // Search with debounce
        let searchTimeout;
        document.getElementById('searchInput').addEventListener('input', () => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(searchConcepts, 300);
        });

        // Keyboard: Escape clears search
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                clearSearch();
            }
        });
    })
    .catch(err => {
        document.getElementById('mindmap').innerHTML =
            '<p style="padding:40px;color:#c00;">Failed to load vocabulary data. ' +
            'If opening as a local file, serve via HTTP instead ' +
            '(e.g. <code>python -m http.server</code> then open http://localhost:8000/docs/).</p>';
        console.error('Failed to load soilvoc_data.json:', err);
    });

// Back-to-top (no data dependency)
const backToTopBtn = document.getElementById('backToTop');
window.addEventListener('scroll', () => {
    if (window.scrollY > 300) {
        backToTopBtn.classList.add('show');
    } else {
        backToTopBtn.classList.remove('show');
    }
});
backToTopBtn.addEventListener('click', () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
});
