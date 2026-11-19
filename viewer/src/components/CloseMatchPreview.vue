<script setup>
import { externalHref } from '../presentation.js'
import { definitionText } from '../definition-text.js'

// The matched concept's own label is shown as the mapping link; this adds its source definitions.
defineProps({ record: Object })
</script>

<template>
  <div class="close-match-preview">
    <details v-if="record.definitions.length" class="mapping-definitions">
      <summary>Source {{ record.definitions.length === 1 ? 'definition' : `definitions (${record.definitions.length})` }}</summary>
      <div v-for="(definition, i) in record.definitions" :key="i" class="definition-entry">
        <p class="definition-text" :lang="definition.language || undefined">{{ definitionText(definition.text) }}<small v-if="!definition.language || !definition.language.startsWith('en')" class="language-tag">{{ definition.language || 'Language not specified' }}</small></p>
        <div v-for="(source, j) in definition.sources" :key="j" class="definition-source">
          <span>Source:</span>
          <a v-if="source.uri && externalHref(source.uri)" :href="externalHref(source.uri)" target="_blank" rel="noopener noreferrer">{{ source.uri }}</a>
          <span v-else>{{ source.text || source.uri }}</span>
        </div>
      </div>
    </details>
    <p v-else class="mapping-preview-status">No English definition in the source record.</p>
  </div>
</template>
