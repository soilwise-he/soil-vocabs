(function () {
  "use strict";

  if (window.soilvocContainsSearchLoaded) {
    return;
  }
  window.soilvocContainsSearchLoaded = true;

  function addTypeLabels() {
    if (!window.SKOSMOS) {
      return;
    }
    const types = window.SKOSMOS.types ??= {};
    // These classes have labels in soilvoc_ontology.ttl, but Skosmos may omit
    // them from type discovery. Keep native labels, including translations.
    const labels = {
      "http://www.w3.org/ns/sosa/ObservableProperty": "Observable Property",
      "http://www.w3.org/ns/sosa/Procedure": "Procedure",
    };
    for (const [uri, label] of Object.entries(labels)) {
      if (!types[uri]) {
        types[uri] = label;
      }
    }
  }

  function containsQuery(value) {
    const term = String(value ?? "").trim();
    if (!term) {
      return "";
    }
    return `${term.startsWith("*") ? "" : "*"}${term}${term.endsWith("*") ? "" : "*"}`;
  }

  function withContainsQuery(method) {
    return function (...args) {
      const originalTerm = this.searchTerm;
      const query = containsQuery(originalTerm);
      if (!query) {
        return;
      }

      // Skosmos 3.2 builds both REST and navigation URLs synchronously. Restore
      // the typed text before Vue renders or the asynchronous results arrive.
      this.searchTerm = query;
      try {
        return method.apply(this, args);
      } finally {
        this.searchTerm = originalTerm;
      }
    };
  }

  function extendSearchComponent(component) {
    const methods = component?.methods;
    if (typeof methods?.autoComplete !== "function"
        || typeof methods?.search !== "function"
        || typeof methods?.gotoSearchPage !== "function"
        || (typeof methods?.formatSearchTerm !== "function"
          && typeof methods?.formatSearchApiParams !== "function")) {
      return component;
    }

    return {
      ...component,
      methods: {
        ...methods,
        search: withContainsQuery(methods.search),
        gotoSearchPage: withContainsQuery(methods.gotoSearchPage),
      },
    };
  }

  function normalizeSearchPage() {
    if (!["vocab-search", "global-search"].includes(window.SKOSMOS?.pageType)) {
      return;
    }

    // Old bookmarks can bypass the search controls. Replace once, retaining
    // language, vocabulary, pagination and other native URL parameters.
    const url = new URL(window.location.href);
    const term = url.searchParams.get("q");
    const query = containsQuery(term);
    if (query && query !== term) {
      url.searchParams.set("q", query);
      window.location.replace(url.href);
    }
  }

  window.soilvocContainsSearch = function () {
    addTypeLabels();
    normalizeSearchPage();
  };
  addTypeLabels();

  // Skosmos loads plugin scripts after Vue, before its search components.
  // Extend public component options; do not access private Vue instances or
  // intercept unrelated fetch requests (including the hierarchy plugin).
  if (window.Vue?.createApp) {
    const createApp = window.Vue.createApp;
    window.Vue.createApp = function (component, ...args) {
      return createApp.call(this, extendSearchComponent(component), ...args);
    };
  }
}());
