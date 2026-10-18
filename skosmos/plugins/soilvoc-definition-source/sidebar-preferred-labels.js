(function () {
  "use strict";

  if (window.soilvocPreferredLabelsLoaded || !window.Vue?.createApp) {
    return;
  }
  window.soilvocPreferredLabelsLoaded = true;

  const indexStates = new WeakMap();

  function filterIndex(entries) {
    const previous = indexStates.get(this);
    const previousCount = previous?.letter === this.selectedLetter ? previous.count : 0;
    const preferred = entries.filter(concept => !concept.altLabel);
    indexStates.set(this, { letter: this.selectedLetter, count: preferred.length });

    if (preferred.length === entries.length) {
      return;
    }
    this.indexConcepts = preferred;

    // An alias-only page adds no scrollable rows. Let native pagination skip it.
    if (preferred.length === previousCount) {
      const letter = this.selectedLetter;
      const offset = this.currentOffset;
      this.$nextTick(() => {
        if (this.selectedLetter === letter && this.currentOffset === offset
            && !this.loadingConcepts && !this.loadingMoreConcepts) {
          this.loadMoreConcepts();
        }
      });
    }
  }

  function extendAlphabetical(component) {
    const methods = component?.methods;
    if (window.SKOSMOS?.vocab !== "soilvoc"
        || typeof methods?.loadLetters !== "function"
        || typeof methods?.loadConcepts !== "function"
        || typeof methods?.loadMoreConcepts !== "function"
        || typeof methods?.handleClickAlphabeticalEvent !== "function") {
      return component;
    }

    const existing = component.watch?.indexConcepts;
    return {
      ...component,
      watch: {
        ...component.watch,
        indexConcepts: [
          ...(existing ? (Array.isArray(existing) ? existing : [existing]) : []),
          { deep: true, handler: filterIndex },
        ],
      },
    };
  }

  const createApp = window.Vue.createApp;
  window.Vue.createApp = function (component, ...args) {
    return createApp.call(this, extendAlphabetical(component), ...args);
  };
}());
