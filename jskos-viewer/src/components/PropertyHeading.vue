<script setup>
import { ref, useId } from 'vue'
import { CircleHelp } from '@lucide/vue'
defineProps({ label: String, predicate: String, description: String, as: { type: String, default: 'h2' } })
const tooltipId = useId(), open = ref(false), dismissed = ref(false)
</script>

<template>
  <component :is="as" class="property-heading">
    {{ label }}
    <span class="property-help" :class="{ open, dismissed }" @mouseenter="dismissed = false">
      <button type="button" :aria-label="`About ${label}`" :aria-describedby="tooltipId" @focus="dismissed = false" @click="open = !open; dismissed = !open" @blur="open = false; dismissed = false" @keydown.esc="open = false; dismissed = true"><CircleHelp :size="13" /></button>
      <span :id="tooltipId" role="tooltip" class="property-tooltip">{{ description }}<code>{{ predicate }}</code></span>
    </span>
  </component>
</template>
