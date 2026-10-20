<script setup>
import { computed } from 'vue'
import { ItemName } from 'jskos-vue'
import { ChevronRight } from '@lucide/vue'
import { pathKey } from '../vocabulary.js'
import { conceptHref, followLink } from '../navigation.js'

const props = defineProps({ model: Object, uri: String, path: Array, expanded: Set, selectedPath: Array, focusedKey: String })
const emit = defineEmits(['navigate', 'toggle'])
const concept = computed(() => props.model.concepts.get(props.uri))
const key = computed(() => pathKey(props.path))
const open = computed(() => props.expanded.has(key.value))
const selected = computed(() => key.value === pathKey(props.selectedPath))
const children = computed(() => props.model.sort(props.model.children.get(props.uri) || []))
const cycle = computed(() => props.path.slice(0, -1).includes(props.uri))
const expandable = computed(() => children.value.length > 0 && !cycle.value)
const accessibleName = computed(() => `${concept.value.label}${concept.value.isProcedure ? ', Procedure' : ''}${cycle.value ? ', Cycle' : ''}`)
</script>

<template>
  <li role="treeitem" :aria-label="accessibleName" :tabindex="key === focusedKey ? 0 : -1" :data-path="key" :aria-expanded="expandable ? open : undefined" :aria-selected="selected" :aria-level="path.length" :style="{ '--depth': Math.min(path.length - 1, 10) }">
    <div class="tree-row" :data-selected="selected" :data-path="key">
      <button v-if="expandable" class="tree-toggle icon-button" tabindex="-1" :aria-label="`${open ? 'Collapse' : 'Expand'} ${concept.label}`" :aria-expanded="open" @click="emit('toggle', path)">
        <ChevronRight :size="15" :class="{ rotated: open }" />
      </button>
      <span v-else class="tree-spacer"></span>
      <a class="tree-select" tabindex="-1" :aria-label="accessibleName" :href="conceptHref(uri, path)" @click="followLink($event, () => emit('navigate', { uri, path }))" :aria-current="selected ? 'page' : undefined">
        <ItemName :item="model.asJskos(uri)" :show-notation="false" :draggable="false" />
        <span v-if="concept.isProcedure" class="procedure-badge">Procedure</span>
        <span v-if="cycle" class="cycle-marker" title="Cycle in the source graph; this branch is not expanded again">Cycle</span>
      </a>
    </div>
    <ul v-if="open && expandable" role="group" class="hierarchy-list">
      <HierarchyNode v-for="child in children" :key="pathKey([...path, child])" :model="model" :uri="child" :path="[...path, child]" :expanded="expanded" :selected-path="selectedPath" :focused-key="focusedKey"
        @navigate="emit('navigate', $event)" @toggle="emit('toggle', $event)" />
    </ul>
  </li>
</template>
