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
const rows = computed(() => props.group.values.map(value => {
  const record = value.kind === 'resource' ? props.previews?.records.get(value.uri) : null
  return {
    value, record, href: value.kind === 'resource' ? externalHref(value.uri) : null,
    // Skosmos shows the matched concept's original label; without a known label it shows the URI.
    labels: record?.prefLabels.length ? record.prefLabels : value.label && value.label !== value.uri ? [{ text: value.label, language: '' }] : [],
    sources: mappingSources(value, props.model),
  }
}))
</script>

<template>
  <section class="property-row mapping-row" :data-predicate="group.predicate" :aria-labelledby="headingId">
    <PropertyHeading :id="headingId" :label="group.label" :predicate="group.predicate" :description="model.propertyTooltip(group.predicate)" />
    <div class="mapping-values">
      <p v-if="isCloseMatch" class="mapping-preview-note">Descriptions from the matched vocabularies, not definitions of this SoilVoc concept.</p>
      <p v-if="isCloseMatch && previews?.status === 'error'" class="mapping-preview-status" role="status">Source previews could not be loaded. <button type="button" class="text-button" @click="emit('retry-previews')">Retry</button></p>
      <ul class="mapping-list">
        <li v-for="({ value, record, href, labels, sources }, index) in rows" :key="value.uri || index" class="mapping-entry">
          <div class="mapping-target">
            <a v-if="href" :href="href" :title="value.uri" target="_blank" rel="noopener noreferrer" :class="{ 'mapping-uri': !labels.length }">
              <template v-if="labels.length"><template v-for="(label, i) in labels" :key="i"><span v-if="i"> / </span><span :lang="label.language || undefined">{{ label.text }}</span><small v-if="label.language && !label.language.startsWith('en')" class="language-tag">{{ label.language }}</small></template></template>
              <template v-else>{{ value.uri }}</template><ArrowUpRight :size="13" aria-label="External resource" />
            </a>
            <TermValue v-else :value="value" :model="model" show-uri @navigate="emit('navigate', $event)" />
            <template v-if="isCloseMatch && value.kind === 'resource'">
              <CloseMatchPreview v-if="record?.definitions" :record="record" />
              <p v-else-if="previews?.status === 'loading'" class="mapping-preview-status" role="status">Loading source preview...</p>
              <p v-else-if="previews?.status === 'ready'" class="mapping-preview-status">Source preview not cached yet.</p>
            </template>
          </div>
          <div v-if="sources.length" class="mapping-vocabulary">
            <span v-for="source in sources" :key="source.uri" :title="source.uri">{{ source.label }}</span>
          </div>
        </li>
      </ul>
    </div>
  </section>
</template>
