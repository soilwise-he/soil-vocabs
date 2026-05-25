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
  const HIERARCHY_PARENT_KEYS = [
    "soilvoc:skosmosHierarchyParent",
    "eusoilvoc:skosmosHierarchyParent",
    "skosmosHierarchyParent",
    "https://w3id.org/eusoilvoc#skosmosHierarchyParent",
  ];
  const SKOS_BROADER_KEYS = [
    "broader",
    "skos:broader",
    "http://www.w3.org/2004/02/skos/core#broader",
  ];
  const TOP_CONCEPT_KEYS = [
    "topConceptOf",
    "skos:topConceptOf",
    "http://www.w3.org/2004/02/skos/core#topConceptOf",
  ];
  const SOILVOC_DATA_FORMAT = "application/ld+json";
  const FALLBACK_HIERARCHY_MAX_NODES = 50;
  const FEEDBACK_ENDPOINT = "https://soilvoc.wangbeichen.com/api/feedback";
  const TURNSTILE_SITE_KEY = "";

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

  function allDefined(node, keys) {
    const values = [];
    if (!node) {
      return values;
    }

    for (const key of keys) {
      if (node[key] !== undefined && node[key] !== null) {
        values.push(...asArray(node[key]));
      }
    }
    return values;
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

  function getValueId(value, context) {
    const id = typeof value === "string" ? value : getId(value);
    return id ? expandCurie(id, context) : null;
  }

  function uniqueUris(values, context) {
    return [...new Set(values.map((value) => getValueId(value, context)).filter(Boolean))];
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

  function mergeNodeData(existingNode, newNode) {
    const merged = { ...existingNode };

    for (const [key, value] of Object.entries(newNode)) {
      if ((key === "uri" || key === "@id") && merged[key]) {
        continue;
      }
      if (merged[key] === undefined || merged[key] === null) {
        merged[key] = value;
      } else {
        merged[key] = mergeByUri(merged[key], value);
      }
    }

    return merged;
  }

  function addNodesToMap(nodeMap, graph, context) {
    if (!Array.isArray(graph)) {
      return nodeMap;
    }

    for (const node of graph) {
      const id = getId(node);
      if (id) {
        const expandedId = expandCurie(id, context);
        const existingNode = nodeMap.get(expandedId) || nodeMap.get(id);
        const mergedNode = existingNode ? mergeNodeData(existingNode, node) : node;

        nodeMap.set(id, mergedNode);
        nodeMap.set(expandedId, mergedNode);
        if (existingNode) {
          const existingId = getId(existingNode);
          if (existingId) {
            nodeMap.set(existingId, mergedNode);
            nodeMap.set(expandCurie(existingId, context), mergedNode);
          }
        }
      }
    }
    return nodeMap;
  }

  function buildNodeMap(graph, context) {
    const nodeMap = new Map();
    return addNodesToMap(nodeMap, graph, context);
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

  async function fetchConceptDocument(originalFetch, requestUrl, conceptUri) {
    const dataUrl = new URL("/rest/v1/soilvoc/data", requestUrl.origin);
    dataUrl.searchParams.set("uri", conceptUri);
    dataUrl.searchParams.set("format", SOILVOC_DATA_FORMAT);

    const response = await originalFetch(dataUrl.toString());
    if (!response.ok) {
      return null;
    }

    try {
      const data = await response.json();
      const graph = data.graph || data["@graph"];
      if (Array.isArray(graph)) {
        return {
          context: data["@context"] || {},
          graph,
        };
      }
    } catch (_error) {
      return null;
    }

    return null;
  }

  function mergeDocument(state, documentData) {
    if (!documentData) {
      return;
    }

    Object.assign(state.context, documentData.context || {});
    addNodesToMap(state.nodeMap, documentData.graph, state.context);
  }

  function getHierarchyParentUris(node, context) {
    const customParents = uniqueUris(allDefined(node, HIERARCHY_PARENT_KEYS), context);
    if (customParents.length > 0) {
      return customParents;
    }
    return uniqueUris(allDefined(node, SKOS_BROADER_KEYS), context);
  }

  async function buildFallbackHierarchy(originalFetch, requestUrl, conceptUri) {
    const initialDocument = readJsonLdDocument();
    const state = {
      context: { ...(initialDocument.context || {}) },
      nodeMap: buildNodeMap(initialDocument.graph, initialDocument.context || {}),
    };
    const queue = [conceptUri];
    const visited = new Set();
    const loaded = new Set();
    const hierarchyUris = new Set();

    while (queue.length > 0 && visited.size < FALLBACK_HIERARCHY_MAX_NODES) {
      const uri = queue.shift();
      if (!uri || visited.has(uri)) {
        continue;
      }

      visited.add(uri);
      hierarchyUris.add(uri);

      if (!loaded.has(uri)) {
        mergeDocument(state, await fetchConceptDocument(originalFetch, requestUrl, uri));
        loaded.add(uri);
      }

      const node = state.nodeMap.get(uri);
      for (const parentUri of getHierarchyParentUris(node, state.context)) {
        hierarchyUris.add(parentUri);
        if (!visited.has(parentUri)) {
          queue.push(parentUri);
        }
      }
    }

    if (!hierarchyUris.has(conceptUri)) {
      return null;
    }

    const broaderTransitive = {};
    for (const uri of hierarchyUris) {
      if (!loaded.has(uri)) {
        mergeDocument(state, await fetchConceptDocument(originalFetch, requestUrl, uri));
        loaded.add(uri);
      }

      const node = state.nodeMap.get(uri);
      const parentUris = getHierarchyParentUris(node, state.context);
      const children = await fetchHierarchyChildren(originalFetch, requestUrl, uri);
      const label = getNodeLabel(state.nodeMap, { uri });
      const topConcepts = uniqueUris(allDefined(node, TOP_CONCEPT_KEYS), state.context);
      const concept = {
        uri,
        label,
        prefLabel: label,
        hasChildren: children.length > 0,
      };

      if (parentUris.length > 0) {
        concept.broader = parentUris;
      }
      if (children.length > 0) {
        concept.narrower = children;
      }
      if (topConcepts.length > 0) {
        concept.top = topConcepts[0];
        concept.tops = topConcepts;
      }

      broaderTransitive[uri] = concept;
    }

    return {
      broaderTransitive,
    };
  }

  async function patchHierarchyResponse(response, requestUrl, originalFetch) {
    const conceptUri = requestUrl.searchParams.get("uri");
    if (!conceptUri) {
      return response;
    }

    if (!response.ok) {
      const fallbackData = await buildFallbackHierarchy(originalFetch, requestUrl, conceptUri);
      return fallbackData
        ? new Response(JSON.stringify(fallbackData), {
            status: 200,
            statusText: "OK",
            headers: { "content-type": "application/json" },
          })
        : response;
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

  function setFeedbackStatus(statusElement, message, isError = false) {
    statusElement.textContent = message;
    statusElement.className = `soilvoc-feedback-status ${isError ? "soilvoc-feedback-status-error" : "soilvoc-feedback-status-ok"}`;
  }

  function ensureFeedbackStatus(form) {
    const existing = form.querySelector(".soilvoc-feedback-status");
    if (existing) {
      return existing;
    }

    const status = document.createElement("div");
    status.className = "soilvoc-feedback-status";
    status.setAttribute("role", "status");
    status.setAttribute("aria-live", "polite");

    const submitButton = form.querySelector("#submit-feedback");
    submitButton?.parentElement?.insertBefore(status, submitButton);
    return status;
  }

  function injectTurnstile(form) {
    if (!TURNSTILE_SITE_KEY || form.querySelector(".cf-turnstile")) {
      return;
    }

    const widget = document.createElement("div");
    widget.className = "cf-turnstile soilvoc-feedback-turnstile";
    widget.dataset.sitekey = TURNSTILE_SITE_KEY;

    const submitButton = form.querySelector("#submit-feedback");
    submitButton?.parentElement?.insertBefore(widget, submitButton);

    if (!document.querySelector('script[src^="https://challenges.cloudflare.com/turnstile/v0/api.js"]')) {
      const script = document.createElement("script");
      script.src = "https://challenges.cloudflare.com/turnstile/v0/api.js";
      script.async = true;
      script.defer = true;
      document.head.appendChild(script);
    }
  }

  function installFeedbackWorkerForm() {
    const form = document.querySelector("#feedback-form");
    if (!form || form.dataset.soilvocFeedbackWorker === "true") {
      return;
    }

    form.dataset.soilvocFeedbackWorker = "true";
    form.action = FEEDBACK_ENDPOINT;
    injectTurnstile(form);

    const status = ensureFeedbackStatus(form);
    const submitButton = form.querySelector("#submit-feedback");

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (typeof form.reportValidity === "function" && !form.reportValidity()) {
        return;
      }

      setFeedbackStatus(status, "Sending feedback...");
      if (submitButton) {
        submitButton.disabled = true;
      }

      try {
        const response = await fetch(FEEDBACK_ENDPOINT, {
          method: "POST",
          body: new FormData(form),
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok || !data.ok) {
          throw new Error(data.error || "Could not send feedback right now.");
        }

        form.replaceChildren();
        const confirmation = document.createElement("div");
        confirmation.className = "soilvoc-feedback-confirmation";
        confirmation.innerHTML = "<h2>Feedback has been sent!</h2><p>Thank you for your feedback.</p>";
        form.appendChild(confirmation);
      } catch (error) {
        setFeedbackStatus(status, error.message || "Could not send feedback right now.", true);
        if (submitButton) {
          submitButton.disabled = false;
        }
      }
    });
  }

  function soilvocDefinitionSource() {
    if (!window.location.pathname.includes("/soilvoc/")) {
      return;
    }

    installFeedbackWorkerForm();

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
