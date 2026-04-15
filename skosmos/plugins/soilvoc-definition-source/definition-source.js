(function () {
  "use strict";

  const SKOS_DEFINITION_KEYS = [
    "skos:definition",
    "definition",
    "http://www.w3.org/2004/02/skos/core#definition",
  ];
  const RDF_VALUE_KEYS = [
    "rdf:value",
    "value",
    "http://www.w3.org/1999/02/22-rdf-syntax-ns#value",
    "schema:text",
    "http://schema.org/text",
    "https://schema.org/text",
  ];
  const SOURCE_KEYS = [
    "dcterms:source",
    "dct:source",
    "dc:source",
    "source",
    "http://purl.org/dc/terms/source",
  ];
  const LABEL_KEYS = [
    "prefLabel",
    "skos:prefLabel",
    "label",
    "rdfs:label",
    "http://www.w3.org/2004/02/skos/core#prefLabel",
    "http://www.w3.org/2000/01/rdf-schema#label",
  ];

  function asArray(value) {
    if (value === undefined || value === null) {
      return [];
    }
    return Array.isArray(value) ? value : [value];
  }

  function mergeByUri(existingValues, newValues) {
    const merged = [];
    const seen = new Set();

    for (const value of [...asArray(existingValues), ...asArray(newValues)]) {
      const id = getId(value);
      const key = id || JSON.stringify(value);
      if (!seen.has(key)) {
        seen.add(key);
        merged.push(value);
      }
    }

    return merged;
  }

  function firstDefined(node, keys) {
    if (!node) {
      return null;
    }
    for (const key of keys) {
      if (node[key] !== undefined && node[key] !== null) {
        const values = asArray(node[key]);
        if (values.length > 0) {
          return values[0];
        }
      }
    }
    return null;
  }

  function getId(node) {
    if (!node || typeof node !== "object") {
      return null;
    }
    return node.uri || node["@id"] || null;
  }

  function valueToText(value) {
    if (value === undefined || value === null) {
      return "";
    }
    if (typeof value === "string") {
      return value;
    }
    if (typeof value === "object") {
      return value.value || value["@value"] || value.uri || value["@id"] || "";
    }
    return String(value);
  }

  function getNodeLabel(nodeMap, value) {
    const id = getId(value);
    const node = id ? nodeMap.get(id) : value;
    const labelValue = firstDefined(node, LABEL_KEYS);
    return valueToText(labelValue) || valueToText(value);
  }

  function expandCurie(value, context) {
    if (typeof value !== "string" || !context || value.startsWith("_:") || /^https?:\/\//.test(value)) {
      return value;
    }

    const separatorIndex = value.indexOf(":");
    if (separatorIndex === -1) {
      return value;
    }

    const prefix = value.slice(0, separatorIndex);
    const localName = value.slice(separatorIndex + 1);
    const namespace = context[prefix];
    if (typeof namespace === "string") {
      return `${namespace}${localName}`;
    }
    if (namespace && typeof namespace === "object" && typeof namespace["@id"] === "string") {
      return `${namespace["@id"]}${localName}`;
    }
    return value;
  }

  function readJsonLdDocument() {
    const scripts = document.querySelectorAll('script[type="application/ld+json"]');
    for (const script of scripts) {
      try {
        const data = JSON.parse(script.textContent || "{}");
        const graph = data.graph || data["@graph"];
        if (Array.isArray(graph)) {
          return {
            context: data["@context"] || {},
            graph,
          };
        }
      } catch (_error) {
        // Ignore non-Skosmos JSON-LD blocks.
      }
    }
    return { context: {}, graph: [] };
  }

  function buildNodeMap(graph, context) {
    const nodeMap = new Map();
    for (const node of graph) {
      const id = getId(node);
      if (id) {
        nodeMap.set(id, node);
        nodeMap.set(expandCurie(id, context), node);
      }
    }
    return nodeMap;
  }

  function findConceptNode(graph, context) {
    const conceptUri = document.querySelector("#concept-uri")?.textContent?.trim();
    if (!conceptUri) {
      return null;
    }
    return graph.find((node) => {
      const id = getId(node);
      return id === conceptUri || expandCurie(id, context) === conceptUri;
    }) || null;
  }

  function collectDefinitions(conceptNode, nodeMap) {
    const definitions = [];
    for (const definitionRef of asArray(firstDefined(conceptNode, SKOS_DEFINITION_KEYS))) {
      const definitionId = getId(definitionRef);
      const definitionNode = definitionId ? nodeMap.get(definitionId) : definitionRef;
      if (!definitionNode) {
        continue;
      }

      const text = valueToText(firstDefined(definitionNode, RDF_VALUE_KEYS));
      const source = firstDefined(definitionNode, SOURCE_KEYS);
      if (text) {
        definitions.push({ text, source });
      }
    }
    return definitions;
  }

  function appendSource(container, source, nodeMap) {
    if (!source) {
      return;
    }

    const sourceWrapper = document.createElement("div");
    sourceWrapper.className = "soilvoc-definition-source";

    const sourceLabel = document.createElement("span");
    sourceLabel.className = "soilvoc-definition-source-label";
    sourceLabel.textContent = "Source: ";
    sourceWrapper.appendChild(sourceLabel);

    const sourceId = getId(source);
    if (sourceId && /^https?:\/\//.test(sourceId)) {
      const sourceLink = document.createElement("a");
      sourceLink.href = sourceId;
      sourceLink.textContent = getNodeLabel(nodeMap, source);
      sourceWrapper.appendChild(sourceLink);
    } else {
      const sourceText = document.createElement("span");
      sourceText.textContent = getNodeLabel(nodeMap, source);
      sourceWrapper.appendChild(sourceText);
    }

    container.appendChild(sourceWrapper);
  }

  function renderDefinitions(definitions, nodeMap) {
    const definitionRow = document.querySelector(".prop-skos_definition");
    const valuesList = definitionRow?.querySelector(".property-value ul");
    if (!definitionRow || !valuesList || definitions.length === 0) {
      return;
    }

    valuesList.replaceChildren();
    definitionRow.classList.add("soilvoc-definition-source-enhanced");

    for (const definition of definitions) {
      const listItem = document.createElement("li");
      const text = document.createElement("span");
      text.className = "soilvoc-definition-text";
      text.textContent = definition.text;
      listItem.appendChild(text);
      appendSource(listItem, definition.source, nodeMap);
      valuesList.appendChild(listItem);
    }
  }

  function getRequestUrl(input) {
    const url = typeof input === "string" ? input : input?.url;
    if (!url) {
      return null;
    }

    try {
      return new URL(url, document.baseURI || window.location.href);
    } catch (_error) {
      return null;
    }
  }

  function shouldPatchHierarchyResponse(url) {
    return window.location.pathname.includes("/soilvoc/")
      && url.pathname === "/rest/v1/soilvoc/hierarchy/";
  }

  function findHierarchyConcept(data, conceptUri) {
    const broaderTransitive = data?.broaderTransitive || {};
    return Object.values(broaderTransitive).find((concept) => concept?.uri === conceptUri) || null;
  }

  async function fetchHierarchyChildren(originalFetch, requestUrl, conceptUri) {
    const childrenUrl = new URL("/rest/v1/soilvoc/children", requestUrl.origin);
    childrenUrl.searchParams.set("uri", conceptUri);

    const lang = requestUrl.searchParams.get("lang");
    if (lang) {
      childrenUrl.searchParams.set("lang", lang);
    }

    const response = await originalFetch(childrenUrl.toString());
    if (!response.ok) {
      return [];
    }

    const data = await response.json();
    return asArray(data?.narrower);
  }

  async function patchHierarchyResponse(response, requestUrl, originalFetch) {
    if (!response.ok) {
      return response;
    }

    const conceptUri = requestUrl.searchParams.get("uri");
    if (!conceptUri) {
      return response;
    }

    let data;
    try {
      data = await response.clone().json();
    } catch (_error) {
      return response;
    }

    const concept = findHierarchyConcept(data, conceptUri);
    if (!concept) {
      return response;
    }

    const children = await fetchHierarchyChildren(originalFetch, requestUrl, conceptUri);
    if (children.length === 0) {
      return response;
    }

    concept.narrower = mergeByUri(concept.narrower, children);

    return new Response(JSON.stringify(data), {
      status: response.status,
      statusText: response.statusText,
      headers: response.headers,
    });
  }

  function installSoilVocHierarchyPatch() {
    if (!window.fetch || window.fetch.soilvocHierarchyPatched) {
      return;
    }

    const originalFetch = window.fetch.bind(window);

    async function soilvocFetch(input, init) {
      const response = await originalFetch(input, init);
      const requestUrl = getRequestUrl(input);
      if (!requestUrl || !shouldPatchHierarchyResponse(requestUrl)) {
        return response;
      }

      return patchHierarchyResponse(response, requestUrl, originalFetch);
    }

    soilvocFetch.soilvocHierarchyPatched = true;
    window.fetch = soilvocFetch;
  }

  function soilvocDefinitionSource() {
    if (!window.location.pathname.includes("/soilvoc/")) {
      return;
    }

    const { context, graph } = readJsonLdDocument();
    const nodeMap = buildNodeMap(graph, context);
    const conceptNode = findConceptNode(graph, context);
    if (!conceptNode) {
      return;
    }

    renderDefinitions(collectDefinitions(conceptNode, nodeMap), nodeMap);
  }

  installSoilVocHierarchyPatch();
  window.soilvocDefinitionSource = soilvocDefinitionSource;
  document.addEventListener("DOMContentLoaded", soilvocDefinitionSource);
})();
