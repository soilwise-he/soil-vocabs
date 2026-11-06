export const GISCUS_HOST = 'https://giscus.app'
export const COMMENTS_REPO = 'soilwise-he/soil-vocabs'
export const COMMENTS_CATEGORY = 'Announcements'
export const COMMENTS_CONFIG = Object.freeze({
  repo: COMMENTS_REPO,
  repoId: 'R_kgDOPJs3OQ',
  category: COMMENTS_CATEGORY,
  categoryId: 'DIC_kwDOPJs3Oc4C1dY0',
})

export function discussionSearchUrl(uri) {
  const url = new URL(`https://github.com/${COMMENTS_REPO}/discussions`)
  url.searchParams.set('discussions_q', `category:"${COMMENTS_CATEGORY}" in:title "${uri}"`)
  return url.href
}

export function isConceptDiscussionUrl(value) {
  return typeof value === 'string' && /^https:\/\/github\.com\/soilwise-he\/soil-vocabs\/discussions\/\d+$/.test(value)
}

export function commentLocation(href, uri) {
  // giscus removes URL fragments during sign-in; retain hash-only concept routes.
  const url = new URL(href)
  url.searchParams.set('uri', uri)
  url.hash = ''
  return url.href
}

