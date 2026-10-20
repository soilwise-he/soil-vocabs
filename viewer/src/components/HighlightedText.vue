<script setup>
import { computed } from 'vue'
const props = defineProps({ text: String, ranges: { type: Array, default: () => [] } })
const pieces = computed(() => {
  const result = []
  let cursor = 0
  for (const [start, end] of props.ranges) {
    if (start > cursor) result.push({ text: props.text.slice(cursor, start), match: false })
    result.push({ text: props.text.slice(start, end), match: true })
    cursor = end
  }
  if (cursor < props.text.length) result.push({ text: props.text.slice(cursor), match: false })
  return result
})
</script>

<template><span class="highlighted-text"><template v-for="(piece, i) in pieces" :key="i"><mark v-if="piece.match">{{ piece.text }}</mark><template v-else>{{ piece.text }}</template></template></span></template>
