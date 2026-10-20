<script setup>
import { computed, useId } from 'vue'
import { ArrowUpRight } from '@lucide/vue'
import PropertyHeading from './PropertyHeading.vue'
import TermValue from './TermValue.vue'
import { safeExternalUrl } from '../vocabulary.js'
import { mappingSources } from '../mapping-sources.js'

const props = defineProps({ group: Object, model: Object })
const emit = defineEmits(['navigate'])
const headingId = useId()
const rows = computed(() => props.group.values.map(value => ({ value, sources: mappingSources(value, props.model) })))
</script>

<template>
  <section class="detail-section mapping-section" :data-predicate="group.predicate" :aria-labelledby="headingId">
    <PropertyHeading :id="headingId" :label="group.label" :predicate="group.predicate" :description="model.propertyTooltip(group.predicate)" />
    <table class="mapping-table" :aria-labelledby="headingId">
      <thead><tr><th scope="col">Concept URI</th><th scope="col">Source vocabulary</th></tr></thead>
      <tbody>
        <tr v-for="({ value, sources }, index) in rows" :key="index">
          <td class="mapping-target">
            <a v-if="value.kind === 'resource' && safeExternalUrl(value.uri)" :href="value.uri" target="_blank" rel="noopener noreferrer">{{ value.uri }}<ArrowUpRight :size="13" aria-label="External resource" /></a>
            <TermValue v-else :value="value" :model="model" show-uri @navigate="emit('navigate', $event)" />
          </td>
          <td class="mapping-source">
            <ul v-if="sources.length"><li v-for="source in sources" :key="source.uri"><span v-if="source.label !== source.uri" class="mapping-source-name">{{ source.label }}</span><a :href="source.uri" target="_blank" rel="noopener noreferrer">{{ source.uri }}<ArrowUpRight :size="13" aria-label="External resource" /></a></li></ul>
            <span v-else class="mapping-source-unknown">Not specified</span>
          </td>
        </tr>
      </tbody>
    </table>
  </section>
</template>
