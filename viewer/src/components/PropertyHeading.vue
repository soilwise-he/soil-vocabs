<script setup>
import { computed, ref, useId } from 'vue'
import { CircleHelp } from '@lucide/vue'
const props = defineProps({ label: String, predicate: String, description: String, as: { type: String, default: 'h2' } })
const tooltipId = useId(), open = ref(false), dismissed = ref(false)
// The last word wraps together with the help button, so the button never sits alone on a line.
const head = computed(() => props.label.replace(/\s*\S+$/, ''))
const tail = computed(() => props.label.match(/\S+$/)?.[0] || props.label)
</script>

<template>
  <component :is="as" class="property-heading">{{ head ? head + ' ' : '' }}<span class="heading-tail">{{ tail }} <span class="property-help" :class="{ open, dismissed }" @mouseenter="dismissed = false">
      <button type="button" :aria-label="`About ${label}`" :aria-describedby="tooltipId" @focus="dismissed = false" @click="open = !open; dismissed = !open" @blur="open = false; dismissed = false" @keydown.esc="open = false; dismissed = true"><CircleHelp :size="13" /></button>
      <span :id="tooltipId" role="tooltip" class="property-tooltip">{{ description }}<code v-if="predicate">{{ predicate }}</code></span>
    </span></span></component>
</template>
