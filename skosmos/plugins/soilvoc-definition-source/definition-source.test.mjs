import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

const climateUri = "https://w3id.org/eusoilvoc#Climate";
const planetaryUri = "https://w3id.org/eusoilvoc#PlanetaryPhenomena";
const externalFactorsUri = "https://w3id.org/eusoilvoc#ExternalFactors";
const solubleSaltsUri = "https://w3id.org/eusoilvoc#SolubleSalts";
const solubleSaltsProcedureUri = "https://w3id.org/eusoilvoc#solubleSaltsProcedure-SlbAn_calcul-unkn";
const saltContentsUri = "https://w3id.org/eusoilvoc#SaltContents";
const soilPhUri = "https://w3id.org/eusoilvoc#SoilpH";
const pHCaCl2Uri = "https://w3id.org/eusoilvoc#pHProcedure-pHCaCl2";
const pHCaCl2RatioUri = "https://w3id.org/eusoilvoc#pHProcedure-pHCaCl2_ratio1-1";
const baseSaturationUri = "https://w3id.org/eusoilvoc#BaseSaturation";
const baseSaturationProcedureCecUri = "https://w3id.org/eusoilvoc#baseSaturationProcedure-BSat_calcul-cec";
const baseSaturationProcedureEcecUri = "https://w3id.org/eusoilvoc#baseSaturationProcedure-BSat_calcul-ecec";
const soilChemicalPropertiesUri = "https://w3id.org/eusoilvoc#SoilChemicalProperties";
const soilPropertiesUri = "https://w3id.org/eusoilvoc#SoilProperties";

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

const nativeFetchCalls = [];
const nativeFetch = async (input) => {
  const url = new URL(typeof input === "string" ? input : input.url);
  nativeFetchCalls.push(url.toString());

  if (url.pathname === "/rest/v1/soilvoc/hierarchy/") {
    throw new Error("native hierarchy should not be used for SoilVoc");
  }

  if (url.pathname === "/rest/v1/soilvoc/children") {
    const children = url.searchParams.get("uri") === solubleSaltsUri
      ? [
          { uri: solubleSaltsProcedureUri, prefLabel: "SlbAn_calcul-unk", hasChildren: false },
          { uri: saltContentsUri, prefLabel: "salt contents", hasChildren: false },
        ]
      : [];
    return jsonResponse({ narrower: children });
  }

  if (url.pathname === "/rest/v1/soilvoc/data") {
    return jsonResponse({
      "@context": jsonLdDocument["@context"],
      graph: [
        {
          uri: solubleSaltsProcedureUri,
          prefLabel: { lang: "en", value: "SlbAn_calcul-unk" },
          "soilvoc:skosmosHierarchyParent": { uri: solubleSaltsUri },
        },
        {
          uri: solubleSaltsUri,
          prefLabel: { lang: "en", value: "soluble salts" },
        },
      ],
    });
  }

  throw new Error(`Unexpected native fetch: ${url}`);
};

const nativeContext = {
  console,
  document: {
    baseURI: "http://localhost:9090/soilvoc/en/page/solubleSaltsProcedure-SlbAn_calcul-unkn",
    addEventListener() {},
    querySelector(selector) {
      return selector === "#concept-uri" ? { textContent: solubleSaltsProcedureUri } : null;
    },
    querySelectorAll() {
      return [];
    },
  },
  fetch: nativeFetch,
  Response,
  URL,
  URLSearchParams,
  window: {
    fetch: nativeFetch,
    location: {
      pathname: "/soilvoc/en/page/solubleSaltsProcedure-SlbAn_calcul-unkn",
      href: "http://localhost:9090/soilvoc/en/page/solubleSaltsProcedure-SlbAn_calcul-unkn",
    },
  },
};
nativeContext.window.window = nativeContext.window;
nativeContext.window.document = nativeContext.document;

vm.runInNewContext(fs.readFileSync(new URL("./definition-source.js", import.meta.url), "utf8"), nativeContext);

const nativeResponse = await nativeContext.window.fetch(
  "http://localhost:9090/rest/v1/soilvoc/hierarchy/?uri=https%3A%2F%2Fw3id.org%2Feusoilvoc%23solubleSaltsProcedure-SlbAn_calcul-unkn&lang=en",
);

assert.equal(nativeResponse.status, 200);
const nativeData = await nativeResponse.json();
const nativeHierarchy = nativeData.broaderTransitive;

assert.ok(
  nativeHierarchy[solubleSaltsUri].narrower.some((child) => child.uri === solubleSaltsProcedureUri),
  "native parent children should be repaired to include the selected procedure concept",
);
assert.ok(
  nativeHierarchy[solubleSaltsUri].narrower.some((child) => child.uri === saltContentsUri),
  "existing native children should be preserved while repairing the selected path",
);
assert.ok(
  nativeFetchCalls.some((url) => url.includes(`/rest/v1/soilvoc/children?uri=${encodeURIComponent(solubleSaltsUri)}`)),
  "successful hierarchy repair should fetch the selected concept parent children",
);
assert.ok(
  nativeFetchCalls.every((url) => !url.includes("/rest/v1/soilvoc/hierarchy/")),
  "native hierarchy should not be called when building SoilVoc hierarchy",
);

const deepFetchCalls = [];
const deepFetch = async (input) => {
  const url = new URL(typeof input === "string" ? input : input.url);
  deepFetchCalls.push(url.toString());

  if (url.pathname === "/rest/v1/soilvoc/hierarchy/") {
    throw new Error("native hierarchy should not be used for SoilVoc");
  }

  if (url.pathname === "/rest/v1/soilvoc/children") {
    const uri = url.searchParams.get("uri");
    const children = {
      [soilPhUri]: [{ uri: pHCaCl2Uri, prefLabel: "pHCaCl2", hasChildren: true }],
      [pHCaCl2Uri]: [{ uri: pHCaCl2RatioUri, prefLabel: "pHCaCl2_ratio1-1", hasChildren: false }],
    }[uri] || [];
    return jsonResponse({ narrower: children });
  }

  if (url.pathname === "/rest/v1/soilvoc/data") {
    return jsonResponse({
      "@context": jsonLdDocument["@context"],
      graph: [
        {
          uri: pHCaCl2RatioUri,
          prefLabel: { lang: "en", value: "pHCaCl2_ratio1-1" },
          broader: { uri: pHCaCl2Uri },
        },
        {
          uri: pHCaCl2Uri,
          prefLabel: { lang: "en", value: "pHCaCl2" },
          "soilvoc:skosmosHierarchyParent": { uri: soilPhUri },
        },
        {
          uri: soilPhUri,
          prefLabel: { lang: "en", value: "soil pH" },
          "soilvoc:skosmosHierarchyParent": { uri: soilChemicalPropertiesUri },
        },
        {
          uri: soilChemicalPropertiesUri,
          prefLabel: { lang: "en", value: "soil chemical properties" },
        },
      ],
    });
  }

  throw new Error(`Unexpected deep fetch: ${url}`);
};

const deepContext = {
  console,
  document: {
    baseURI: "http://localhost:9090/soilvoc/en/page/pHProcedure-pHCaCl2_ratio1-1",
    addEventListener() {},
    querySelector(selector) {
      return selector === "#concept-uri" ? { textContent: pHCaCl2RatioUri } : null;
    },
    querySelectorAll() {
      return [];
    },
  },
  fetch: deepFetch,
  Response,
  URL,
  URLSearchParams,
  window: {
    fetch: deepFetch,
    location: {
      pathname: "/soilvoc/en/page/pHProcedure-pHCaCl2_ratio1-1",
      href: "http://localhost:9090/soilvoc/en/page/pHProcedure-pHCaCl2_ratio1-1",
    },
  },
};
deepContext.window.window = deepContext.window;
deepContext.window.document = deepContext.document;

vm.runInNewContext(fs.readFileSync(new URL("./definition-source.js", import.meta.url), "utf8"), deepContext);

const deepResponse = await deepContext.window.fetch(
  "http://localhost:9090/rest/v1/soilvoc/hierarchy/?uri=https%3A%2F%2Fw3id.org%2Feusoilvoc%23pHProcedure-pHCaCl2_ratio1-1&lang=en",
);

assert.equal(deepResponse.status, 200);
const deepData = await deepResponse.json();
const deepHierarchy = deepData.broaderTransitive;
const soilPhChildren = deepHierarchy[soilPhUri].narrower || [];

assert.ok(
  soilPhChildren.some((child) => child.uri === pHCaCl2Uri),
  "native grandparent children should be repaired to include the selected concept parent",
);
assert.ok(
  deepFetchCalls.some((url) => url.includes(`/rest/v1/soilvoc/children?uri=${encodeURIComponent(soilPhUri)}`)),
  "successful hierarchy repair should fetch ancestor parent children beyond the selected concept",
);
assert.ok(
  deepFetchCalls.every((url) => !url.includes("/rest/v1/soilvoc/hierarchy/")),
  "native hierarchy should not be called for deep SoilVoc hierarchy paths",
);

const baseSaturationFetchCalls = [];
const baseSaturationFetch = async (input) => {
  const url = new URL(typeof input === "string" ? input : input.url);
  baseSaturationFetchCalls.push(url.toString());

  if (url.pathname === "/rest/v1/soilvoc/hierarchy/") {
    throw new Error("native hierarchy should not be used for SoilVoc");
  }

  if (url.pathname === "/rest/v1/soilvoc/children") {
    const uri = url.searchParams.get("uri");
    const children = {
      [baseSaturationUri]: [
        { uri: baseSaturationProcedureCecUri, prefLabel: "BSat_calcul-cec", hasChildren: false },
        { uri: baseSaturationProcedureEcecUri, prefLabel: "BSat_calcul-ecec", hasChildren: false },
      ],
      [soilChemicalPropertiesUri]: [
        { uri: baseSaturationUri, prefLabel: "base saturation", hasChildren: true },
      ],
      [soilPropertiesUri]: [
        { uri: soilChemicalPropertiesUri, prefLabel: "soil chemical properties", hasChildren: true },
      ],
    }[uri] || [];
    return jsonResponse({ narrower: children });
  }

  if (url.pathname === "/rest/v1/soilvoc/data") {
    return jsonResponse({
      "@context": jsonLdDocument["@context"],
      graph: [
        {
          uri: baseSaturationUri,
          prefLabel: { lang: "en", value: "base saturation" },
          "soilvoc:skosmosHierarchyParent": { uri: soilChemicalPropertiesUri },
        },
        {
          uri: soilChemicalPropertiesUri,
          prefLabel: { lang: "en", value: "soil chemical properties" },
          "soilvoc:skosmosHierarchyParent": { uri: soilPropertiesUri },
        },
        {
          uri: soilPropertiesUri,
          prefLabel: { lang: "en", value: "soil properties" },
        },
      ],
    });
  }

  throw new Error(`Unexpected base saturation fetch: ${url}`);
};

const baseSaturationContext = {
  console,
  document: {
    baseURI: "http://localhost:9090/soilvoc/en/page/BaseSaturation",
    addEventListener() {},
    querySelector(selector) {
      return selector === "#concept-uri" ? { textContent: baseSaturationUri } : null;
    },
    querySelectorAll() {
      return [];
    },
  },
  fetch: baseSaturationFetch,
  Response,
  URL,
  URLSearchParams,
  window: {
    fetch: baseSaturationFetch,
    location: {
      pathname: "/soilvoc/en/page/BaseSaturation",
      href: "http://localhost:9090/soilvoc/en/page/BaseSaturation",
    },
  },
};
baseSaturationContext.window.window = baseSaturationContext.window;
baseSaturationContext.window.document = baseSaturationContext.document;

vm.runInNewContext(fs.readFileSync(new URL("./definition-source.js", import.meta.url), "utf8"), baseSaturationContext);

const baseSaturationResponse = await baseSaturationContext.window.fetch(
  "http://localhost:9090/rest/v1/soilvoc/hierarchy/?uri=https%3A%2F%2Fw3id.org%2Feusoilvoc%23BaseSaturation&lang=en",
);

assert.equal(baseSaturationResponse.status, 200);
const baseSaturationData = await baseSaturationResponse.json();
const baseSaturationHierarchy = baseSaturationData.broaderTransitive;
const baseSaturationChildren = baseSaturationHierarchy[baseSaturationUri].narrower || [];
const soilChemicalPropertiesChildren = baseSaturationHierarchy[soilChemicalPropertiesUri].narrower || [];

assert.ok(
  baseSaturationChildren.some((child) => child.uri === baseSaturationProcedureCecUri),
  "custom hierarchy should include BaseSaturation procedures from children endpoint",
);
assert.ok(
  soilChemicalPropertiesChildren.some((child) => child.uri === baseSaturationUri && child.hasChildren === true),
  "custom hierarchy should keep BaseSaturation expandable under soil chemical properties",
);
assert.ok(
  baseSaturationFetchCalls.every((url) => !url.includes("/rest/v1/soilvoc/hierarchy/")),
  "native hierarchy should not be called for BaseSaturation",
);
