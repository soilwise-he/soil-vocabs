<script setup>
import { computed, useId } from 'vue'
import { ArrowUpRight } from '@lucide/vue'
import PropertyHeading from './PropertyHeading.vue'
import TermValue from './TermValue.vue'
import CloseMatchPreview from './CloseMatchPreview.vue'
import { NS } from '../vocabulary.js'
import { externalHref } from '../presentation.js'
import { mappingSources } from '../mapping-sources.js'

const props = defineProps({ group: Object, model: Object, previews: Object })
const emit = defineEmits(['navigate', 'retry-previews'])
const headingId = useId()
const isCloseMatch = computed(() => props.group.predicate === NS.skos + 'closeMatch')
const rows = computed(() => props.group.values.map(value => ({ value, sources: mappingSources(value, props.model) })))
</script>

<template>
  <section class="detail-section mapping-section" :data-predicate="group.predicate" :aria-labelledby="headingId">
    <PropertyHeading :id="headingId" :label="group.label" :predicate="group.predicate" :description="model.propertyTooltip(group.predicate)" />
    <p v-if="isCloseMatch" class="mapping-preview-note">Descriptions from the matched vocabularies, not definitions of this SoilVoc concept.</p>
    <p v-if="isCloseMatch && previews?.status === 'error'" class="mapping-preview-status" role="status">Source previews could not be loaded. <button type="button" class="text-button" @click="emit('retry-previews')">Retry</button></p>
    <table class="mapping-table" role="table" :aria-labelledby="headingId">
      <thead role="rowgroup"><tr role="row"><th role="columnheader" scope="col">Concept URI</th><th role="columnheader" scope="col">Source vocabulary</th></tr></thead>
      <tbody role="rowgroup">
        <tr v-for="({ value, sources }, index) in rows" :key="value.uri || index" role="row">
          <td class="mapping-target" role="cell">
            <span class="mapping-mobile-label" aria-hidden="true">Concept URI</span>
            <a v-if="value.kind === 'resource' && externalHref(value.uri)" :href="externalHref(value.uri)" target="_blank" rel="noopener noreferrer">{{ value.uri }}<ArrowUpRight :size="13" aria-label="External resource" /></a>
            <TermValue v-else :value="value" :model="model" show-uri @navigate="emit('navigate', $event)" />
            <template v-if="isCloseMatch && value.kind === 'resource'">
              <CloseMatchPreview v-if="previews?.records.has(value.uri)" :record="previews.records.get(value.uri)" />
              <p v-else-if="previews?.status === 'loading'" class="mapping-preview-status" role="status">Loading source preview...</p>
              <p v-else-if="previews?.status === 'ready'" class="mapping-preview-status">Source preview not cached yet.</p>
            </template>
          </td>
          <td class="mapping-source" role="cell">
            <span class="mapping-mobile-label" aria-hidden="true">Source vocabulary</span>
            <ul v-if="sources.length"><li v-for="source in sources" :key="source.uri"><span v-if="source.label !== source.uri" class="mapping-source-name">{{ source.label }}</span><a :href="source.uri" target="_blank" rel="noopener noreferrer">{{ source.uri }}<ArrowUpRight :size="13" aria-label="External resource" /></a></li></ul>
            <span v-else class="mapping-source-unknown">Not specified</span>
          </td>
        </tr>
      </tbody>
    </table>
  </section>
</template>
