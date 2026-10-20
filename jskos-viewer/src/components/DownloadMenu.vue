<script setup>
import { ref } from 'vue'
import { Download, ChevronDown } from '@lucide/vue'
import { localName } from '../vocabulary.js'

const props = defineProps({ model: Object, uri: String })
const emit = defineEmits(['notice'])
const menu = ref(null)
async function download(format) {
  try {
    const text = await props.model.serialize(props.uri, format)
    const types = { ttl: 'text/turtle', jsonld: 'application/ld+json', rdf: 'application/rdf+xml' }
    const blob = new Blob([text], { type: types[format] + ';charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = (props.uri ? localName(props.uri) : 'SoilVoc_skosmos') + '.' + format
    link.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
    menu.value.open = false
    emit('notice', 'Download prepared')
  } catch (error) { emit('notice', error.message) }
}
</script>

<template>
  <details ref="menu" class="download-menu">
    <summary class="button secondary"><Download :size="16" /><span>Download</span><ChevronDown :size="13" /></summary>
    <div class="menu-popover">
      <button @click="download('ttl')">Turtle <small>.ttl</small></button>
      <button @click="download('jsonld')">JSON-LD <small>.jsonld</small></button>
      <button @click="download('rdf')">RDF/XML <small>.rdf</small></button>
    </div>
  </details>
</template>
