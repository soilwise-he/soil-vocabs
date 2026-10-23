<script setup>
import { computed } from 'vue'
import { ArrowUpRight } from '@lucide/vue'
import { safeExternalUrl, compact } from '../vocabulary.js'
import { conceptHref, followLink } from '../navigation.js'

const props = defineProps({ value: Object, model: Object, showUri: Boolean })
const emit = defineEmits(['navigate'])
const external = computed(() => safeExternalUrl(props.value.uri || ''))
</script>

<template>
  <span v-if="value.kind === 'literal'" class="literal-value">{{ value.text }}<small v-if="value.language && value.language !== 'en'" class="language-tag">{{ value.language }}</small></span>
  <span v-else-if="value.kind === 'resource'" class="resource-value">
    <a v-if="value.local || value.defined" :class="{ 'concept-link': value.local }" :href="conceptHref(value.uri)" :title="value.uri" @click="followLink($event, () => emit('navigate', value.uri))">{{ value.label }}</a>
    <a v-else-if="external" :href="external" :title="value.uri" target="_blank" rel="noopener noreferrer">{{ showUri ? value.uri : value.label }}<ArrowUpRight :size="13" aria-label="External resource" /></a>
    <span v-else :title="value.uri">{{ value.label }}</span>
    <span v-if="model.concepts.get(value.uri)?.isProcedure" class="procedure-badge">Procedure</span>
  </span>
  <dl v-else-if="value.kind === 'blank'" class="blank-node">
    <template v-for="(property, i) in value.properties" :key="`${property.predicate}-${i}`">
      <dt :title="property.predicate">{{ property.label || compact(property.predicate) }}</dt>
      <dd><TermValue :model="model" :value="property.value" @navigate="emit('navigate', $event)" /></dd>
    </template>
  </dl>
</template>
