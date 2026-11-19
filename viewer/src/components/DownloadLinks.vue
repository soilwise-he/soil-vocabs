<script setup>
import { RDF_FORMATS, downloadRdf } from '../download.js'

const props = defineProps({ model: Object, uri: String })
const emit = defineEmits(['notice'])
async function download(format) {
  try {
    await downloadRdf(props.model, props.uri, format)
    emit('notice', 'Download prepared')
  } catch (error) { emit('notice', error.message) }
}
</script>

<template>
  <span class="download-links">
    <button v-for="entry in RDF_FORMATS" :key="entry.format" type="button" class="download-link"
      :aria-label="`Download ${uri ? 'this concept' : 'the vocabulary'} as ${entry.name}`" @click="download(entry.format)">{{ entry.name }}</button>
  </span>
</template>
