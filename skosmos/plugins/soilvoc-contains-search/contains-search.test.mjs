import assert from "node:assert/strict";
import fs from "node:fs";
import { test } from "node:test";
import vm from "node:vm";

const source = fs.readFileSync(new URL("./contains-search.js", import.meta.url), "utf8");

const skosConcept = "http://www.w3.org/2004/02/skos/core#Concept";
const observableProperty = "http://www.w3.org/ns/sosa/ObservableProperty";
const procedure = "http://www.w3.org/ns/sosa/Procedure";

function harness(href = "http://localhost:9090/soilvoc/en/", pageType = "vocab", types = { [skosConcept]: "Concept" }) {
  const apps = [];
  const replacements = [];
  const requests = [];
  const Vue = {
    createApp(component, ...args) {
      const app = { component, args, receiver: this, directive() {}, mount() {} };
      apps.push(app);
      return app;
    },
  };
  const window = {
    Vue,
    SKOSMOS: { pageType, vocab: "soilvoc", lang: "en", content_lang: "en", baseHref: "http://localhost:9090/", types },
    location: { href, replace: (value) => replacements.push(value) },
  };
  const context = vm.createContext({
    window,
    Vue,
    URL,
    URLSearchParams,
    document: { getElementById: () => null },
    onTranslationReady: (callback) => callback(),
    fetch: async (url) => {
      requests.push(new URL(url, window.SKOSMOS.baseHref));
      return { json: async () => ({ results: [], "@context": {} }) };
    },
  });
  vm.runInContext(source, context);
  return { apps, replacements, requests, window, context };
}

function searchComponent() {
  return {
    methods: {
      autoComplete() {},
      formatSearchTerm() {
        return this.searchTerm.includes("*") ? this.searchTerm : `${this.searchTerm}*`;
      },
      search(marker) {
        return { query: this.formatSearchTerm(), marker };
      },
      gotoSearchPage() {
        return new URLSearchParams({ q: this.searchTerm, clang: this.selectedLanguage });
      },
    },
  };
}

function instance(component, state = {}) {
  const result = { ...state };
  for (const [name, method] of Object.entries(component.methods)) {
    result[name] = method.bind(result);
  }
  return result;
}

for (const [input, expected] of [
  ["Hydraulic conductivity", "*Hydraulic conductivity*"],
  ["Hydraulic conductivity*", "*Hydraulic conductivity*"],
  ["*Hydraulic conductivity", "*Hydraulic conductivity*"],
  ["*Hydraulic conductivity*", "*Hydraulic conductivity*"],
  ["hydraulic*conductivity", "*hydraulic*conductivity*"],
  ["  conductivity  ", "*conductivity*"],
  ["pHCaCl2_ratio1-1", "*pHCaCl2_ratio1-1*"],
  ["pH (CaCl2) & salts", "*pH (CaCl2) & salts*"],
  ["porosit\u00e9", "*porosit\u00e9*"],
  ["*", "*"],
]) {
  test(`both search paths normalize ${JSON.stringify(input)} without changing typed text`, () => {
    const { window } = harness();
    const app = window.Vue.createApp(searchComponent());
    const state = instance(app.component, { searchTerm: input, selectedLanguage: "en" });
    const result = state.search("passed-through");
    assert.equal(result.query, expected);
    assert.equal(result.marker, "passed-through");
    assert.equal(state.searchTerm, input);
    const params = state.gotoSearchPage();
    assert.equal(params.get("q"), expected);
    assert.equal(params.get("clang"), "en");
    assert.equal(state.searchTerm, input);
  });
}

test("empty, whitespace-only and missing input do not issue searches", () => {
  const { window } = harness();
  const app = window.Vue.createApp(searchComponent());
  for (const searchTerm of ["", "   ", null, undefined]) {
    const state = instance(app.component, { searchTerm });
    assert.equal(state.search(), undefined);
    assert.equal(state.gotoSearchPage(), undefined);
    assert.equal(state.searchTerm, searchTerm);
  }
});

test("restores input even when a native method fails", () => {
  const { window } = harness();
  const component = searchComponent();
  component.methods.search = function () { throw new Error(this.searchTerm); };
  const state = instance(window.Vue.createApp(component).component, { searchTerm: "conductivity" });
  assert.throws(() => state.search(), /\*conductivity\*/);
  assert.equal(state.searchTerm, "conductivity");
});

test("preserves native component options, arguments and unrelated Vue apps", () => {
  const { window } = harness();
  const component = searchComponent();
  const nativeSearch = component.methods.search;
  const props = { example: true };
  const app = window.Vue.createApp(component, props);
  assert.equal(component.methods.search, nativeSearch);
  assert.equal(app.component.methods.autoComplete, component.methods.autoComplete);
  assert.equal(app.args[0], props);
  assert.equal(app.receiver, window.Vue);
  for (const other of [{ methods: { search() {} } }, {}, () => null, null]) {
    assert.equal(window.Vue.createApp(other).component, other);
  }
});

test("loading the plugin twice does not stack wrappers or replace fetch", () => {
  const { window, context } = harness();
  const createApp = window.Vue.createApp;
  const fetch = context.fetch;
  vm.runInContext(source, context);
  assert.equal(window.Vue.createApp, createApp);
  assert.equal(context.fetch, fetch);
});

test("supplies missing SOSA labels without overriding native type labels", () => {
  const { window } = harness();
  assert.equal(window.SKOSMOS.types[observableProperty], "Observable Property");
  assert.equal(window.SKOSMOS.types[procedure], "Procedure");
  assert.equal(window.SKOSMOS.types[skosConcept], "Concept");
  const localized = harness(undefined, undefined, {
    [observableProperty]: "Localized property label",
    "https://example.org/CustomClass": "Custom class",
  });
  assert.equal(localized.window.SKOSMOS.types[observableProperty], "Localized property label");
  assert.equal(localized.window.SKOSMOS.types["https://example.org/CustomClass"], "Custom class");
});

test("restores type-label fallbacks after partial navigation replaces SKOSMOS", () => {
  const { window } = harness();
  window.SKOSMOS = { pageType: "concept" };
  window.soilvocContainsSearch();
  assert.equal(window.SKOSMOS.types[observableProperty], "Observable Property");
  assert.equal(window.SKOSMOS.types[procedure], "Procedure");
});

for (const pageType of ["vocab-search", "global-search"]) {
  test(`${pageType}: normalizes saved URLs and preserves filters and base path`, () => {
    const href = "http://localhost:9090/skosmos/en/search?q=hydraulic+conductivity*&clang=en&anylang=on&vocabs=soilvoc&offset=20#results";
    const { window, replacements } = harness(href, pageType);
    window.soilvocContainsSearch();
    assert.equal(replacements.length, 1);
    const updated = new URL(replacements[0]);
    assert.equal(updated.pathname, "/skosmos/en/search");
    assert.equal(updated.searchParams.get("q"), "*hydraulic conductivity*");
    for (const key of ["clang", "anylang", "vocabs", "offset"]) {
      assert.equal(updated.searchParams.get(key), new URL(href).searchParams.get(key));
    }
    assert.equal(updated.hash, "#results");
    window.location.href = updated.href;
    window.soilvocContainsSearch();
    assert.equal(replacements.length, 1, "no redirect loop");
  });
}

test("does not redirect concept pages or empty searches", () => {
  for (const [href, pageType] of [
    ["http://localhost:9090/soilvoc/en/page/SoilpH?q=pH", "concept"],
    ["http://localhost:9090/en/search", "global-search"],
    ["http://localhost:9090/en/search?q=++", "global-search"],
    ["http://localhost:9090/en/search?q=*", "global-search"],
  ]) {
    const { window, replacements } = harness(href, pageType);
    window.soilvocContainsSearch();
    assert.equal(replacements.length, 0);
  }
});

// Optional compatibility tests against the actual JS in the running image.
// No browser or triplestore data is changed; native requests are captured.
const liveBase = process.env.SKOSMOS_TEST_URL;
for (const file of ["vocab-search.js", "global-search.js"]) {
  test(`Skosmos image compatibility: ${file}`, { skip: !liveBase }, async () => {
    const response = await fetch(new URL(`resource/js/${file}`, liveBase));
    assert.equal(response.status, 200);
    const { window, context, apps, requests } = harness();
    if (file === "global-search.js") window.SKOSMOS.vocab = "";
    vm.runInContext(await response.text(), context);
    assert.equal(apps.length, 1);
    const component = apps[0].component;
    for (const selectedLanguage of ["en", "all"]) {
      window.location.href = `http://localhost:9090/en/?${selectedLanguage === "all" ? "anylang=on" : "clang=en"}`;
      const state = instance(component, {
        ...component.data(),
        searchTerm: "Hydraulic conductivity",
        selectedLanguage,
        getSelectedVocabs: [{ key: "soilvoc" }],
        uriPrefixes: { skos: "http://www.w3.org/2004/02/skos/core#", sosa: "http://www.w3.org/ns/sosa/" },
      });
      assert.equal(state.renderType(observableProperty), "Observable Property");
      assert.equal(state.renderType("sosa:ObservableProperty"), "Observable Property");
      assert.equal(state.renderType(procedure), "Procedure");
      assert.equal(state.renderType("sosa:Procedure"), "Procedure");
      assert.equal(state.renderType("skos:Concept"), "Concept");
      assert.equal(state.renderType("https://example.org/UnknownClass"), "https://example.org/UnknownClass");
      state.renderResults = () => {};
      state.search();
      assert.equal(state.searchTerm, "Hydraulic conductivity");
      const apiUrl = requests.at(-1);
      assert.equal(apiUrl.searchParams.get("query"), "*Hydraulic conductivity*");
      assert.equal(apiUrl.searchParams.get("unique"), "true");
      if (selectedLanguage === "en") assert.equal(apiUrl.searchParams.get("lang"), "en");
      state.gotoSearchPage();
      const pageUrl = new URL(window.location.href, "http://localhost:9090/");
      assert.equal(pageUrl.searchParams.get("q"), "*Hydraulic conductivity*");
      assert.equal(state.searchTerm, "Hydraulic conductivity");
      if (selectedLanguage === "all") assert.ok(pageUrl.searchParams.has("anylang"));
      else assert.equal(pageUrl.searchParams.get("clang"), "en");
      if (file === "global-search.js") {
        assert.equal(apiUrl.searchParams.get("vocab"), "soilvoc");
        assert.equal(pageUrl.searchParams.get("vocabs"), "soilvoc");
      }
      await new Promise(setImmediate);
    }
  });
}
