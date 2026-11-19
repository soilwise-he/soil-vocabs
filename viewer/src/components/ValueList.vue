<script setup>
import { computed, ref } from 'vue'
import TermValue from './TermValue.vue'

// Long relationship lists start shortened, as in Skosmos; short lists are shown in full.
const LIMIT = 10, THRESHOLD = 12
const props = defineProps({ values: Array, model: Object, label: String })
const emit = defineEmits(['navigate'])
const expanded = ref(false)
const long = computed(() => props.values.length > THRESHOLD)
const visible = computed(() => long.value && !expanded.value ? props.values.slice(0, LIMIT) : props.values)
</script>

<template>
  <div class="value-list">
    <ul class="values-list"><li v-for="(value, i) in visible" :key="i"><TermValue :model="model" :value="value" @navigate="emit('navigate', $event)" /></li></ul>
    <button v-if="long" type="button" class="text-button show-all" :aria-expanded="expanded"
      :aria-label="expanded ? `Show fewer ${label.toLowerCase()}` : `Show all ${values.length} ${label.toLowerCase()}`" @click="expanded = !expanded">
      {{ expanded ? 'Show fewer' : `Show all ${values.length}` }}
    </button>
  </div>
</template>
