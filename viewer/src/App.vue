<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import { ItemDetails, ItemName, ItemList } from 'jskos-vue'
import { Search, X, Copy, ClipboardCopy, Download, Menu, ChevronsDownUp, ChevronRight, Check, ArrowLeft, ArrowRight, ArrowUpRight } from '@lucide/vue'
import HierarchyNode from './components/HierarchyNode.vue'
import TermValue from './components/TermValue.vue'
import DownloadMenu from './components/DownloadMenu.vue'
import HighlightedText from './components/HighlightedText.vue'
import PropertyHeading from './components/PropertyHeading.vue'
import MappingSection from './components/MappingSection.vue'
import { createVocabulary, NS, TYPE, CONCEPT, PROCEDURE, PROPERTY, pathKey, compact } from './vocabulary.js'
import { conceptHref, followLink, parseRoute } from './navigation.js'
import { detailSections, displayValues } from './presentation.js'

const baseUrl = import.meta.env.BASE_URL
const model = shallowRef(null), manifest = ref(null), error = ref(''), loading = ref(true)
const route = ref(parseRoute('', NS.eusoilvoc))
const query = ref(''), typeFilter = ref(''), sidebarTab = ref('hierarchy'), letter = ref('All'), alphabetLimit = ref(100)
const expanded = ref(new Set()), selectedPath = ref([]), mobileSidebar = ref(false)
const showSuggestions = ref(false), suggestionIndex = ref(-1), searchInput = ref(null), toast = ref('')
const page = computed(() => Math.min(route.value.page, Math.max(0, Math.ceil(searchResults.value.length / 30) - 1)))
const rdfMode = ref(false), rdfText = ref(''), rdfLoading = ref(false)
let toastTimer, blurTimer, desktopLayout, rdfRequest = 0
const selected = computed(() => model.value?.concepts.get(route.value.uri))
const searchResults = computed(() => model.value?.search(route.value.q, route.value.type) || [])
const pageResults = computed(() => searchResults.value.slice(page.value * 30, (page.value + 1) * 30))
const suggestions = computed(() => query.value.trim() ? model.value?.searchMatches(query.value, typeFilter.value, 8) || [] : [])
const types = computed(() => [PROPERTY, PROCEDURE, CONCEPT].map(uri => ({ uri, label: model.value?.label(uri) || uri })))
const alphabet = computed(() => (model.value?.sortedConcepts || []).filter(c => letter.value === 'All' || (letter.value === '#' ? !/^[a-z]/i.test(c.label) : c.label.toUpperCase().startsWith(letter.value))))
const groups = computed(() => model.value && selected.value ? model.value.propertiesFor(selected.value.uri) : [])
const sections = computed(() => detailSections(groups.value))
const crumbs = computed(() => selectedPath.value.slice(0, -1))
const hierarchyPaths = computed(() => selected.value ? model.value.pathsTo(selected.value.uri) : [])
const advancedTypes = computed(() => selected.value?.types.filter(uri => uri !== CONCEPT) || [])
const resourceGroups = computed(() => model.value?.propertiesFor(route.value.uri, true) || [])
const resourceConcepts = computed(() => model.value?.sortedConcepts.filter(c => c.types.includes(route.value.uri)) || [])
const ontologyTab = ref('classes')
const ontologyRows = computed(() => model.value?.ontology[ontologyTab.value] || [])

function notice(message) {
  toast.value = message
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toast.value = '' }, 3000)
}
async function copyText(text, name) {
  try { await navigator.clipboard.writeText(text); notice(`${name} copied`) }
  catch { notice(`Clipboard access unavailable. The ${name.toLowerCase()} is selectable on this page.`) }
}
function copyUri(uri) { return copyText(uri, 'URI') }
function readRoute() {
  route.value = parseRoute(window.location.search, NS.eusoilvoc, window.location.hash)
  query.value = route.value.q
  typeFilter.value = route.value.type
  rdfMode.value = false
  showSuggestions.value = false
  nextTick(() => document.querySelector('.reading-pane')?.scrollTo({ top: window.history.state?.readingScroll || 0 }))
}
function go(params) {
  const url = new URL(window.location.href)
  url.search = ''
  url.hash = ''
  for (const [key, value] of Object.entries(params)) if (value !== undefined && value !== null) url.searchParams.set(key, typeof value === 'string' ? value : JSON.stringify(value))
  window.history.replaceState({ ...window.history.state, readingScroll: document.querySelector('.reading-pane')?.scrollTop || 0 }, '')
  window.history.pushState({ readingScroll: 0 }, '', url)
  readRoute()
  mobileSidebar.value = false
}
function navigate(input) {
  const uri = typeof input === 'string' ? input : input.uri
  const path = typeof input === 'object' && model.value.validPath(input.path, uri) ? input.path : model.value.pathTo(uri, selectedPath.value)
  go({ uri, ...(path.length ? { path } : {}) })
}
function runSearch() { go({ q: query.value.trim(), ...(typeFilter.value ? { type: typeFilter.value } : {}) }) }
function chooseSuggestion(index) {
  const concept = suggestions.value[index]?.concept
  if (concept) navigate(concept.uri)
}
function searchKey(event) {
  if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
    event.preventDefault()
    showSuggestions.value = true
    const count = suggestions.value.length
    suggestionIndex.value = !count ? -1 : suggestionIndex.value < 0 ? (event.key === 'ArrowDown' ? 0 : count - 1) : (suggestionIndex.value + (event.key === 'ArrowDown' ? 1 : -1) + count) % count
  } else if (event.key === 'Enter') {
    event.preventDefault()
    if (showSuggestions.value && suggestionIndex.value >= 0) chooseSuggestion(suggestionIndex.value)
    else runSearch()
  } else if (event.key === 'Escape') showSuggestions.value = false
}
function blurSearch() { blurTimer = setTimeout(() => { showSuggestions.value = false }, 150) }
function toggle(path) {
  const key = pathKey(path)
  if (expanded.value.has(key)) expanded.value.delete(key)
  else expanded.value.add(key)
}
function reveal(path, includeSelected = true) {
  for (let n = 1; n <= path.length - (includeSelected ? 0 : 1); n++) expanded.value.add(pathKey(path.slice(0, n)))
}
function collapseAll() { expanded.value = new Set(); reveal(selectedPath.value, false) }
function typeCaption(concept) { return concept.types.filter(uri => uri !== CONCEPT).map(uri => model.value.label(uri)).join(', ') || 'Concept' }
function snippet(concept) { const text = concept.definitions[0]?.text || ''; return text.length > 220 ? text.slice(0, 220) + '...' : text }
function navParents(uri) { return model.value.sort(model.value.parents.get(uri) || []) }
function typeSearch(uri) { go({ q: '', type: uri }) }
function resetQuery() { query.value = ''; suggestionIndex.value = -1; searchInput.value?.focus() }
function retry() { window.location.reload() }
function changePage(delta) {
  go({ q: route.value.q, ...(route.value.type ? { type: route.value.type } : {}), page: page.value + delta + 1 })
}
function handleGlobalKey(event) {
  if (event.key === 'Escape') mobileSidebar.value = false
  if (event.key === '/' && !/INPUT|TEXTAREA|SELECT/.test(event.target.tagName) && !event.ctrlKey && !event.metaKey) {
    event.preventDefault(); searchInput.value?.focus()
  }
}
async function updateRdf() {
  const request = ++rdfRequest
  if (!rdfMode.value || !selected.value) return
  rdfLoading.value = true
  const text = await model.value.serialize(selected.value.uri, 'ttl')
  if (request === rdfRequest) { rdfText.value = text; rdfLoading.value = false }
}
function revealSelectedRow() {
  const current = document.querySelector('.sidebar [data-selected="true"]')
  current?.scrollIntoView({ block: 'center', inline: 'nearest' })
  return current
}
async function onDesktopLayoutChange(event) {
  if (!event.matches) return
  mobileSidebar.value = false
  await nextTick()
  revealSelectedRow()
}
watch([route, model], async () => {
  if (!model.value) return
  const uri = route.value.uri
  selectedPath.value = model.value.validPath(route.value.path, uri) ? route.value.path : model.value.pathTo(uri, selectedPath.value)
  reveal(selectedPath.value)
  document.title = selected.value ? `${selected.value.label} | SoilVoc` : route.value.view === 'concept' ? `${model.value.label(uri)} | SoilVoc` : 'SoilVoc - Soil science vocabulary'
  await nextTick()
  revealSelectedRow()
})
watch(rdfMode, updateRdf)
watch(mobileSidebar, async open => {
  if (!open) return
  await nextTick()
  const current = revealSelectedRow()
  current?.querySelector('a')?.focus({ preventScroll: true })
})
watch([suggestionIndex, showSuggestions], ([index, open]) => {
  if (open && index >= 0) document.getElementById(`suggestion-${index}`)?.scrollIntoView({ block: 'nearest', inline: 'nearest' })
}, { flush: 'post' })
watch([query, typeFilter], () => { suggestionIndex.value = -1 })
onMounted(async () => {
  window.addEventListener('popstate', readRoute)
  window.addEventListener('hashchange', readRoute)
  window.addEventListener('keydown', handleGlobalKey)
  desktopLayout = window.matchMedia('(min-width: 761px)')
  desktopLayout.addEventListener('change', onDesktopLayoutChange)
  try {
    const base = import.meta.env.BASE_URL
    const [response, metaResponse] = await Promise.all([fetch(base + 'data/SoilVoc.ttl'), fetch(base + 'data/manifest.json')])
    if (!response.ok) throw new Error(`Vocabulary file could not be loaded (HTTP ${response.status}).`)
    const source = await response.text()
    if (metaResponse.ok) manifest.value = await metaResponse.json()
    model.value = createVocabulary(source)
    readRoute()
  } catch (failure) { error.value = failure.message }
  finally { loading.value = false }
})
onBeforeUnmount(() => {
  window.removeEventListener('popstate', readRoute)
  window.removeEventListener('hashchange', readRoute)
  window.removeEventListener('keydown', handleGlobalKey)
  desktopLayout?.removeEventListener('change', onDesktopLayoutChange)
  clearTimeout(toastTimer); clearTimeout(blurTimer)
})
</script>

<template>
  <div class="app-shell">
    <header class="masthead">
      <a class="brand" href="?" @click="followLink($event, () => go({}))">SoilVoc</a>
      <span class="brand-description">Soil science vocabulary</span>
      <nav aria-label="Main navigation" class="top-nav">
        <a href="?" :class="{ active: !['ontology', 'about'].includes(route.view) }" @click="followLink($event, () => go({}))">Browse</a>
        <a href="?view=ontology" :class="{ active: route.view === 'ontology' }" @click="followLink($event, () => go({ view: 'ontology' }))">Ontology</a>
        <a href="?view=about" :class="{ active: route.view === 'about' }" @click="followLink($event, () => go({ view: 'about' }))">About</a>
        <a class="icon-button" :href="`${baseUrl}data/SoilVoc.ttl`" download title="Download complete vocabulary (Turtle)" aria-label="Download complete vocabulary"><Download :size="21" /></a>
      </nav>
    </header>

    <form v-if="model" class="search-band" role="search" @submit.prevent="runSearch">
      <button type="button" class="icon-button mobile-menu" aria-label="Toggle vocabulary sidebar" :aria-expanded="mobileSidebar" @click="mobileSidebar = !mobileSidebar"><Menu :size="22" /></button>
      <div class="search-field">
        <Search :size="20" aria-hidden="true" />
        <input ref="searchInput" v-model="query" aria-label="Search vocabulary" placeholder="Search concepts" role="combobox" aria-autocomplete="list" :aria-expanded="showSuggestions && !!query.trim()" aria-controls="search-suggestions" :aria-activedescendant="suggestionIndex >= 0 ? `suggestion-${suggestionIndex}` : undefined"
          @focus="showSuggestions = true" @input="showSuggestions = true" @blur="blurSearch" @keydown="searchKey" />
        <button v-if="query" type="button" class="icon-button" aria-label="Clear search" @click="resetQuery"><X :size="19" /></button>
        <ul v-if="showSuggestions && query.trim()" id="search-suggestions" class="suggestions" role="listbox">
          <li v-for="({ concept, match }, index) in suggestions" :id="`suggestion-${index}`" :key="concept.uri" role="option" :aria-selected="index === suggestionIndex" @mousedown.prevent="chooseSuggestion(index)">
            <span class="suggestion-label"><template v-if="match && !match.preferred"><HighlightedText :text="match.text" :ranges="match.ranges" /><ArrowRight :size="14" aria-label="Preferred label" /></template><HighlightedText :text="concept.label" :ranges="model.matchLabel(concept.label, query)?.ranges" /></span>
            <span class="suggestion-type">{{ typeCaption(concept) }}</span>
          </li>
          <li v-if="!suggestions.length" class="no-suggestions">No matching concepts</li>
          <li v-else class="all-results" @mousedown.prevent="runSearch">View all results<ArrowRight :size="15" /></li>
        </ul>
      </div>
      <label class="sr-only" for="type-filter">Concept type</label>
      <select id="type-filter" v-model="typeFilter"><option value="">All types</option><option v-for="type in types" :key="type.uri" :value="type.uri">{{ type.label }}</option></select>
      <button type="submit" class="button primary">Search</button>
    </form>

    <main v-if="loading || error" class="load-screen" aria-live="polite">
      <h1>{{ error ? 'Vocabulary unavailable' : 'Loading SoilVoc' }}</h1>
      <p>{{ error || 'Reading the local RDF vocabulary...' }}</p>
      <button v-if="error" class="button primary" @click="retry">Retry</button>
    </main>
    <div v-else class="workspace">
      <div v-if="mobileSidebar" class="sidebar-backdrop" @click="mobileSidebar = false"></div>
      <aside class="sidebar" :class="{ 'mobile-open': mobileSidebar }" aria-label="Vocabulary navigation">
        <div class="sidebar-toolbar">
          <div class="tabs" role="tablist" aria-label="Navigation view">
            <button role="tab" :aria-selected="sidebarTab === 'hierarchy'" @click="sidebarTab = 'hierarchy'">Hierarchy</button>
            <button role="tab" :aria-selected="sidebarTab === 'alphabetical'" @click="sidebarTab = 'alphabetical'">A-Z</button>
          </div>
          <button class="icon-button collapse-button" title="Collapse all branches" aria-label="Collapse all branches" @click="collapseAll"><ChevronsDownUp :size="17" /></button>
        </div>
        <div class="sidebar-content">
          <ul v-if="sidebarTab === 'hierarchy'" role="tree" aria-label="SoilVoc hierarchy" class="hierarchy-list">
            <HierarchyNode v-for="root in model.roots" :key="root" :model="model" :uri="root" :path="[root]" :expanded="expanded" :selected-path="selectedPath" @toggle="toggle" @navigate="navigate" />
          </ul>
          <div v-else class="alphabetical-index">
            <div class="letters" aria-label="Alphabetical filter"><button v-for="char in ['All', ...'ABCDEFGHIJKLMNOPQRSTUVWXYZ', '#']" :key="char" :class="{ active: letter === char }" @click="letter = char; alphabetLimit = 100">{{ char }}</button></div>
            <p class="list-count">{{ alphabet.length.toLocaleString() }} concepts</p>
            <ItemList :items="alphabet.slice(0, alphabetLimit).map(c => model.asJskos(c.uri))" :draggable="false" :row-mode="false" :item-name-options="{ showNotation: false }">
              <template #beforeItem="{ item }"><a class="alphabetical-link" :href="conceptHref(item.uri)" @click="followLink($event, () => navigate(item.uri))"><ItemName :item="item" :show-notation="false" :draggable="false" /><span v-if="model.concepts.get(item.uri).isProcedure" class="procedure-badge">Procedure</span></a></template>
            </ItemList>
            <button v-if="alphabet.length > alphabetLimit" class="button secondary more-button" @click="alphabetLimit += 100">Show more</button>
          </div>
        </div>
        <footer class="sidebar-footer"><span>{{ model.stats.concepts.toLocaleString() }} concepts</span><span>English</span></footer>
      </aside>

      <main class="reading-pane" id="content" :inert="mobileSidebar">
        <template v-if="selected">
          <div v-if="crumbs.length || hierarchyPaths.length > 1" class="concept-navigation">
            <nav v-if="crumbs.length" class="breadcrumbs" aria-label="Concept path">
              <template v-for="(uri, i) in crumbs" :key="`${uri}-${i}`"><ChevronRight v-if="i" :size="13" /><a :href="conceptHref(uri, selectedPath.slice(0, i + 1))" @click="followLink($event, () => navigate({ uri, path: selectedPath.slice(0, i + 1) }))">{{ model.label(uri) }}</a></template>
            </nav>
            <details v-if="hierarchyPaths.length > 1" :key="selected.uri" class="hierarchy-paths">
              <summary>Hierarchy paths ({{ hierarchyPaths.length }})</summary>
              <ul><li v-for="path in hierarchyPaths" :key="pathKey(path)"><a :class="{ current: pathKey(path) === pathKey(selectedPath) }" :aria-current="pathKey(path) === pathKey(selectedPath) ? 'true' : undefined" :href="conceptHref(selected.uri, path)" @click="followLink($event, () => navigate({ uri: selected.uri, path }))"><span class="path-chain"><template v-for="(uri, i) in path" :key="uri"><ChevronRight v-if="i" :size="12" /><span>{{ model.label(uri) }}</span></template></span><Check v-if="pathKey(path) === pathKey(selectedPath)" :size="15" aria-label="Current path" /></a></li></ul>
            </details>
          </div>
          <ItemDetails :item="model.asJskos(selected.uri)" class="concept-detail" :show-tabs="false" :show-ancestors="false" :show-broader="false" :show-narrower="false" :draggable="false" :dropzone="false">
            <template #beforeName><h1 class="sr-only">{{ selected.label }}</h1></template>
            <template #afterName>
              <button class="icon-button copy-label" title="Copy preferred label" aria-label="Copy preferred label" @click="copyText(selected.label, 'Preferred label')"><ClipboardCopy :size="18" /></button>
              <div class="type-row"><a v-for="type in advancedTypes.length ? advancedTypes : [CONCEPT]" :key="type" class="type-label" :href="conceptHref(type)" :title="type" @click="followLink($event, () => navigate(type))">{{ model.label(type) }}</a></div>
              <div class="concept-identity"><span>URI</span><a :href="selected.uri" target="_blank" rel="noopener noreferrer" class="canonical-uri">{{ selected.uri }}<ArrowUpRight :size="13" /></a><button class="icon-button" aria-label="Copy concept URI" title="Copy concept URI" @click="copyUri(selected.uri)"><Copy :size="16" /></button></div>
            </template>
            <template #afterTabs>
              <div class="concept-toolbar">
                <div class="detail-view-switch" role="tablist" aria-label="Concept representation"><button role="tab" :aria-selected="!rdfMode" @click="rdfMode = false">Details</button><button role="tab" :aria-selected="rdfMode" @click="rdfMode = true">RDF</button></div>
                <DownloadMenu :model="model" :uri="selected.uri" @notice="notice" />
              </div>
              <div v-if="rdfMode" class="rdf-view"><p v-if="rdfLoading">Preparing Turtle...</p><pre v-else>{{ rdfText }}</pre></div>
              <div v-else class="concept-sections">
                <section v-if="selected.definitions.length" class="detail-section definitions-section" aria-label="Definitions">
                  <PropertyHeading label="Definitions" :predicate="NS.skos + 'definition'" :description="model.propertyTooltip(NS.skos + 'definition')" />
                  <div v-for="(definition, i) in selected.definitions" :key="i" class="definition-entry"><p class="definition-text">{{ definition.text }}</p><div v-for="(source, j) in definition.sources" :key="j" class="definition-source"><span>Source:</span><TermValue :value="model.describe(source)" :model="model" show-uri @navigate="navigate" /></div><small v-if="definition.language && definition.language !== 'en'" class="language-tag">{{ definition.language }}</small></div>
                </section>
                <template v-for="section in sections" :key="section.id">
                  <template v-if="section.id === 'mappings'"><MappingSection v-for="group in section.groups" :key="group.predicate" :group="group" :model="model" @navigate="navigate" /></template>
                  <section v-else v-for="group in section.groups" :key="group.predicate" class="property-row" :data-predicate="group.predicate" :aria-label="group.label">
                    <PropertyHeading :label="group.label" :predicate="group.predicate" :description="model.propertyTooltip(group.predicate)" />
                    <ul class="values-list"><li v-for="(value, i) in displayValues(group.values)" :key="i"><TermValue :model="model" :value="value" @navigate="navigate" /></li></ul>
                  </section>
                </template>
              </div>
            </template>
          </ItemDetails>
        </template>

        <template v-else-if="route.view === 'search'">
          <div class="page-heading"><h1>Search results</h1><p>{{ searchResults.length.toLocaleString() }} results{{ route.q ? ` for "${route.q}"` : '' }}<template v-if="route.type"> · {{ model.label(route.type) }}</template></p></div>
          <div v-if="!searchResults.length" class="empty-state"><Search :size="28" /><h2>No matching concepts</h2><p>{{ route.q }}</p><button v-if="route.type" class="button secondary" @click="go({ q: route.q })">Search all types</button></div>
          <article v-for="concept in pageResults" :key="concept.uri" class="search-result">
            <div class="result-heading"><a :href="conceptHref(concept.uri)" @click="followLink($event, () => navigate(concept.uri))"><HighlightedText :text="concept.label" :ranges="model.matchLabel(concept.label, route.q)?.ranges" /></a><span class="result-type">{{ typeCaption(concept) }}</span></div>
            <p v-if="concept.altLabels.length" class="result-alternatives"><span>Also known as: </span><template v-for="(label, i) in concept.altLabels" :key="i"><span v-if="i">; </span><HighlightedText :text="label.text" :ranges="model.matchLabel(label.text, route.q)?.ranges" /></template></p>
            <p v-if="snippet(concept)">{{ snippet(concept) }}</p>
            <p v-if="navParents(concept.uri).length" class="result-parents"><span>Under</span><template v-for="parent in navParents(concept.uri)" :key="parent"><a :href="conceptHref(parent)" @click="followLink($event, () => navigate(parent))">{{ model.label(parent) }}</a></template></p>
          </article>
          <nav v-if="searchResults.length > 30" class="pagination" aria-label="Results pages"><button class="button secondary" :disabled="page === 0" @click="changePage(-1)"><ArrowLeft :size="16" />Previous</button><span>{{ page + 1 }} / {{ Math.ceil(searchResults.length / 30) }}</span><button class="button secondary" :disabled="(page + 1) * 30 >= searchResults.length" @click="changePage(1)">Next<ArrowRight :size="16" /></button></nav>
        </template>

        <template v-else-if="route.view === 'ontology'">
          <div class="page-heading"><h1>SoilVoc ontology</h1><p>Classes and properties used in the loaded vocabulary.</p></div>
          <div class="tabs ontology-tabs"><button :class="{ active: ontologyTab === 'classes' }" @click="ontologyTab = 'classes'">Classes ({{ model.ontology.classes.length }})</button><button :class="{ active: ontologyTab === 'properties' }" @click="ontologyTab = 'properties'">Properties ({{ model.ontology.properties.length }})</button></div>
          <div class="ontology-list"><article v-for="uri in ontologyRows" :key="uri"><a :href="conceptHref(uri)" @click="followLink($event, () => navigate(uri))">{{ model.label(uri) }}</a><code>{{ compact(uri) }}</code><button v-if="model.typeUris.includes(uri)" class="text-button" @click="typeSearch(uri)">Browse concepts<ArrowRight :size="14" /></button></article></div>
          <p v-if="!ontologyRows.length" class="empty-state">No used {{ ontologyTab === 'classes' ? 'classes' : 'properties' }} are declared in this vocabulary.</p>
        </template>

        <template v-else-if="route.view === 'concept'">
          <template v-if="resourceGroups.length">
            <div class="page-heading resource-heading"><p class="resource-category">Ontology resource</p><h1>{{ model.label(route.uri) }}</h1><div class="resource-tools"><button class="icon-button bordered" title="Copy resource URI" aria-label="Copy resource URI" @click="copyUri(route.uri)"><Copy :size="17" /></button><DownloadMenu :model="model" :uri="route.uri" @notice="notice" /></div></div>
            <div class="property-table"><section v-for="group in resourceGroups" :key="group.predicate" class="property-row"><PropertyHeading :label="group.label" :predicate="group.predicate" :description="model.propertyTooltip(group.predicate)" /><ul class="values-list"><li v-for="(value, i) in group.values" :key="i"><TermValue :model="model" :value="value" @navigate="navigate" /></li></ul></section><section class="property-row"><h2>URI</h2><code class="canonical-uri">{{ route.uri }}</code></section></div>
            <section v-if="resourceConcepts.length" class="typed-concepts"><h2>{{ resourceConcepts.length }} concepts of this type</h2><button class="button secondary" @click="typeSearch(route.uri)">Browse {{ model.label(route.uri) }} concepts<ArrowRight :size="16" /></button></section>
          </template>
          <div v-else class="empty-state"><h1>Concept not found</h1><p class="canonical-uri">{{ route.uri }}</p><button class="button primary" @click="go({})">Back to vocabulary</button></div>
        </template>

        <template v-else>
          <div class="page-heading"><h1>{{ route.view === 'about' ? 'About SoilVoc' : 'Browse SoilVoc' }}</h1><p>{{ route.view === 'about' ? 'Soil science vocabulary' : `${model.stats.concepts.toLocaleString()} concepts in soil science` }}</p></div>
          <div v-if="route.view === 'about'" class="vocabulary-facts"><div><strong>{{ model.stats.concepts.toLocaleString() }}</strong><span>Concepts</span></div><div><strong>{{ model.stats.properties }}</strong><span>Observable properties</span></div><div><strong>{{ model.stats.procedures }}</strong><span>Procedures</span></div><div><strong>{{ model.stats.definitions.toLocaleString() }}</strong><span>Definitions</span></div></div>
          <section v-if="route.view === 'about'" class="label-statistics" aria-label="Label statistics"><h2>Labels</h2><dl><div><dt>Preferred labels</dt><dd>{{ model.stats.preferredLabels.toLocaleString() }}</dd></div><div><dt>Alternative labels</dt><dd>{{ model.stats.alternativeLabels.toLocaleString() }}</dd></div><div><dt>Hidden labels</dt><dd>{{ model.stats.hiddenLabels.toLocaleString() }}</dd></div></dl></section>
          <template v-if="route.view === 'home'"><section class="overview-section"><h2>Top concepts</h2><div class="top-concepts"><a v-for="uri in model.roots" :key="uri" :href="conceptHref(uri)" @click="followLink($event, () => navigate(uri))">{{ model.label(uri) }}<ChevronRight :size="15" /></a></div></section></template>
          <template v-else><div class="property-table"><section class="property-row"><h2>Vocabulary URI</h2><a :href="model.schemeUri" target="_blank" rel="noopener noreferrer">{{ model.schemeUri }}</a></section><section class="property-row"><h2>Language</h2><span>English</span></section><section class="property-row"><h2>Source file</h2><code>{{ manifest?.source || 'viewer/data/SoilVoc.ttl' }}</code></section><section class="property-row"><h2>RDF statements</h2><span>{{ model.stats.triples.toLocaleString() }}</span></section><section class="property-row"><h2>Source checksum</h2><code class="checksum">{{ manifest?.sha256 }}</code></section><section class="property-row"><h2>Downloads</h2><DownloadMenu :model="model" @notice="notice" /></section></div><section class="overview-section"><h2>Ontology</h2><p>{{ model.ontology.classes.length }} classes and {{ model.ontology.properties.length }} properties are used in the vocabulary.</p><button class="button secondary" @click="go({ view: 'ontology' })">Browse ontology<ArrowRight :size="16" /></button></section></template>
          <section v-if="route.view === 'about'" class="overview-section workflow-section"><h2>SoilVoc in SoilWise</h2><img class="workflow-image" :src="`${baseUrl}workflow.png`" alt="SoilWise workflow and the role of SoilVoc" loading="lazy" /></section>
        </template>
      </main>
    </div>
    <div v-if="toast" class="toast" role="status"><Check :size="16" />{{ toast }}</div>
  </div>
</template>
