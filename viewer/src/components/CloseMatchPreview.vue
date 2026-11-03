<script setup>
import { externalHref } from '../presentation.js'

defineProps({ record: Object })
</script>

<template>
  <div class="close-match-preview">
    <div v-for="(label, i) in record.prefLabels" :key="i" class="mapping-original-label" :lang="label.language || undefined">
      {{ label.text }}<small v-if="label.language && !label.language.startsWith('en')" class="language-tag">{{ label.language }}</small>
    </div>
    <details v-if="record.definitions.length" class="mapping-definitions">
      <summary>Source {{ record.definitions.length === 1 ? 'definition' : `definitions (${record.definitions.length})` }}</summary>
      <div v-for="(definition, i) in record.definitions" :key="i" class="definition-entry">
        <p class="definition-text" :lang="definition.language || undefined">{{ definition.text }}<small v-if="!definition.language || !definition.language.startsWith('en')" class="language-tag">{{ definition.language || 'Language not specified' }}</small></p>
        <div v-for="(source, j) in definition.sources" :key="j" class="definition-source">
          <span>Source:</span>
          <a v-if="source.uri && externalHref(source.uri)" :href="externalHref(source.uri)" target="_blank" rel="noopener noreferrer">{{ source.uri }}</a>
          <span v-else>{{ source.text || source.uri }}</span>
        </div>
      </div>
    </details>
    <p v-else class="mapping-preview-status">No definition in the source record.</p>
  </div>
</template>
