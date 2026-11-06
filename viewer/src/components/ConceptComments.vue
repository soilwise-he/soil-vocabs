<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, shallowRef } from 'vue'
import { ArrowUpRight, RotateCw } from '@lucide/vue'
import { COMMENTS_CONFIG, GISCUS_HOST, commentLocation, discussionSearchUrl, isConceptDiscussionUrl } from '../comments.js'

const props = defineProps({ uri: { type: String, required: true } })
const section = ref(null), widget = shallowRef(null)
const status = ref('idle'), failure = ref(''), discussionUrl = ref(discussionSearchUrl(props.uri))
let observer, timeout, backlink, disposed = false

function fail(message) {
  clearTimeout(timeout)
  failure.value = message
  status.value = 'error'
}

function handleMessage(event) {
  const frame = section.value?.querySelector('giscus-widget')?.iframeRef
  if (event.origin !== GISCUS_HOST || !frame || event.source !== frame.contentWindow) return
  const data = event.data?.giscus
  if (!data || typeof data !== 'object') return
  if (data.error && !String(data.error).includes('Discussion not found')) {
    fail(String(data.error).includes('not installed') ? 'Comments are not enabled yet.' : 'Comments could not be loaded.')
    return
  }
  if (data.resizeHeight || data.discussion || String(data.error || '').includes('Discussion not found')) {
    clearTimeout(timeout)
    if (status.value !== 'error') status.value = 'ready'
  }
  if (isConceptDiscussionUrl(data.discussion?.url)) discussionUrl.value = data.discussion.url
}

async function load() {
  observer?.disconnect()
  clearTimeout(timeout)
  widget.value = null
  failure.value = ''
  status.value = 'loading'
  try {
    const { default: Giscus } = await import('@giscus/vue')
    if (disposed) return
    // Preserve the selected concept across GitHub's OAuth return, including W3ID links.
    window.history.replaceState(window.history.state, '', commentLocation(window.location.href, props.uri))
    backlink ||= document.createElement('meta')
    backlink.name = 'giscus:backlink'
    backlink.content = props.uri
    document.head.append(backlink)
    widget.value = Giscus
    timeout = setTimeout(() => fail('Comments are taking too long to load.'), 20000)
  } catch {
    if (!disposed) fail('Comments could not be loaded.')
  }
}

onMounted(() => {
  window.addEventListener('message', handleMessage)
  if (new URL(window.location.href).searchParams.has('giscus')) {
    load()
    nextTick(() => section.value?.scrollIntoView({ block: 'start' }))
    return
  }
  if (!('IntersectionObserver' in window)) { load(); return }
  observer = new IntersectionObserver(entries => {
    if (entries.some(entry => entry.isIntersecting)) load()
  }, { root: section.value.closest('.reading-pane'), rootMargin: '200px 0px' })
  observer.observe(section.value)
})

onBeforeUnmount(() => {
  disposed = true
  observer?.disconnect()
  clearTimeout(timeout)
  backlink?.remove()
  window.removeEventListener('message', handleMessage)
})
</script>

<template>
  <section ref="section" class="concept-comments" aria-labelledby="comments-heading" :data-concept-uri="uri">
    <div class="comments-heading">
      <h2 id="comments-heading">Comments</h2>
      <a :href="discussionUrl" target="_blank" rel="noopener noreferrer">GitHub Discussions<ArrowUpRight :size="14" /></a>
    </div>
    <div class="comments-body" :aria-busy="status === 'loading'">
      <p v-if="status === 'loading'" class="comments-status" role="status">Loading comments...</p>
      <div v-if="status === 'error'" class="comments-status" role="status">
        <p>{{ failure }}</p>
        <button class="button secondary" type="button" @click="load"><RotateCw :size="15" />Retry comments</button>
      </div>
      <div v-show="status !== 'error'">
        <component :is="widget" v-if="widget" id="concept-comments" v-bind="COMMENTS_CONFIG" mapping="specific" :term="uri"
          strict="1" reactions-enabled="1" emit-metadata="1" input-position="top" theme="light" lang="en" loading="eager" />
      </div>
    </div>
  </section>
</template>
