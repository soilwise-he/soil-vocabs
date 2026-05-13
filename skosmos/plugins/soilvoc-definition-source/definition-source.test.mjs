import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

const climateUri = "https://w3id.org/eusoilvoc#Climate";
const planetaryUri = "https://w3id.org/eusoilvoc#PlanetaryPhenomena";
const externalFactorsUri = "https://w3id.org/eusoilvoc#ExternalFactors";

const jsonLdDocument = {
  "@context": {
    soilvoc: "https://w3id.org/eusoilvoc#",
    skos: "http://www.w3.org/2004/02/skos/core#",
    uri: "@id",
    prefLabel: "skos:prefLabel",
    broader: "skos:broader",
    graph: "@graph",
  },
  graph: [
    {
      uri: "soilvoc:Climate",
      prefLabel: { lang: "en", value: "climate" },
      "soilvoc:skosmosHierarchyParent": [
        { uri: "soilvoc:PlanetaryPhenomena" },
        { uri: "soilvoc:ExternalFactors" },
      ],
    },
    {
      uri: "soilvoc:PlanetaryPhenomena",
      prefLabel: { lang: "en", value: "planetary phenomena" },
    },
    {
      uri: "soilvoc:ExternalFactors",
      prefLabel: { lang: "en", value: "external factors" },
    },
  ],
};

const childrenByUri = new Map([
  [
    planetaryUri,
    [
      { uri: climateUri, prefLabel: "climate", hasChildren: false },
      { uri: "https://w3id.org/eusoilvoc#Weather", prefLabel: "weather", hasChildren: true },
    ],
  ],
  [
    externalFactorsUri,
    [
      { uri: climateUri, prefLabel: "climate", hasChildren: false },
      { uri: "https://w3id.org/eusoilvoc#LandUse", prefLabel: "land use", hasChildren: true },
    ],
  ],
  [climateUri, []],
]);

function jsonResponse(data) {
  return new Response(JSON.stringify(data), {
    status: 200,
    headers: { "content-type": "application/json" },
  });
}

const fetchCalls = [];
const originalFetch = async (input) => {
  const url = new URL(typeof input === "string" ? input : input.url);
  fetchCalls.push(url.toString());

  if (url.pathname === "/rest/v1/soilvoc/hierarchy/") {
    return new Response("ERROR: HTTP request for SPARQL query failed", { status: 500 });
  }

  if (url.pathname === "/rest/v1/soilvoc/data") {
    return jsonResponse(jsonLdDocument);
  }

  if (url.pathname === "/rest/v1/soilvoc/children") {
    return jsonResponse({ narrower: childrenByUri.get(url.searchParams.get("uri")) || [] });
  }

  throw new Error(`Unexpected fetch: ${url}`);
};

const context = {
  console,
  document: {
    baseURI: "http://localhost:9090/soilvoc/en/page/Climate",
    addEventListener() {},
    querySelector() {
      return { textContent: climateUri };
    },
    querySelectorAll(selector) {
      if (selector === 'script[type="application/ld+json"]') {
        return [{ textContent: JSON.stringify(jsonLdDocument) }];
      }
      return [];
    },
  },
  fetch: originalFetch,
  Response,
  URL,
  URLSearchParams,
  window: {
    fetch: originalFetch,
    location: { pathname: "/soilvoc/en/page/Climate", href: "http://localhost:9090/soilvoc/en/page/Climate" },
  },
};
context.window.window = context.window;
context.window.document = context.document;

vm.runInNewContext(fs.readFileSync(new URL("./definition-source.js", import.meta.url), "utf8"), context);

const response = await context.window.fetch(
  "http://localhost:9090/rest/v1/soilvoc/hierarchy/?uri=https%3A%2F%2Fw3id.org%2Feusoilvoc%23Climate&lang=en",
);

assert.equal(response.status, 200);
const data = await response.json();
const hierarchy = data.broaderTransitive;

assert.ok(hierarchy[climateUri], "selected concept should be present in fallback hierarchy");
assert.deepEqual(hierarchy[climateUri].broader.sort(), [externalFactorsUri, planetaryUri].sort());
assert.ok(
  hierarchy[planetaryUri].narrower.some((child) => child.uri === climateUri),
  "parent children should include selected concept",
);
assert.ok(fetchCalls.some((url) => url.includes("/rest/v1/soilvoc/children")));
