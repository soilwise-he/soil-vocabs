import { test } from 'node:test'
import assert from 'node:assert/strict'
import { conceptHref, followLink, parseRoute } from '../src/navigation.js'
import { NS } from '../src/vocabulary.js'

test('search pagination and filters survive URL round trips', () => {
  const route = parseRoute('?q=soil&type=ObservableProperty&page=2', NS.eusoilvoc)
  assert.equal(route.view, 'search')
  assert.equal(route.page, 1)
  assert.equal(route.q, 'soil')
  assert.equal(route.type, 'ObservableProperty')
  for (const invalid of ['0', '-1', 'NaN', 'Infinity', '2.5', '99999999999999999999999']) {
    assert.equal(parseRoute('?q=soil&page=' + invalid, NS.eusoilvoc).page, 0)
  }
})

test('hierarchy link targets preserve the exact selected branch in another tab', () => {
  const uri = NS.eusoilvoc + 'SoilHydraulicConductivity'
  const path = [NS.eusoilvoc + 'SoilIndicators', NS.eusoilvoc + 'SoilStructureIndex', uri]
  const route = parseRoute(conceptHref(uri, path), NS.eusoilvoc)
  assert.equal(route.uri, uri)
  assert.deepEqual(route.path, path)
  assert.equal(parseRoute('?uri=BaseSaturation', NS.eusoilvoc).uri, NS.eusoilvoc + 'BaseSaturation')
  assert.equal(parseRoute('?uri=BaseSaturation&path=broken', NS.eusoilvoc).path, null)
})

test('only ordinary same-tab left clicks are intercepted', () => {
  function dispatch(overrides = {}, anchor = {}) {
    let prevented = false, navigated = false
    const event = { button: 0, currentTarget: { hasAttribute: () => false, ...anchor }, preventDefault: () => { prevented = true }, ...overrides }
    followLink(event, () => { navigated = true })
    return { prevented, navigated }
  }
  assert.deepEqual(dispatch(), { prevented: true, navigated: true })
  for (const modifier of ['ctrlKey', 'metaKey', 'shiftKey', 'altKey']) {
    assert.deepEqual(dispatch({ [modifier]: true }), { prevented: false, navigated: false })
  }
  for (const button of [1, 2]) assert.deepEqual(dispatch({ button }), { prevented: false, navigated: false })
  assert.deepEqual(dispatch({ defaultPrevented: true }), { prevented: false, navigated: false })
  assert.deepEqual(dispatch({}, { target: '_blank' }), { prevented: false, navigated: false })
  assert.deepEqual(dispatch({}, { hasAttribute: () => true }), { prevented: false, navigated: false })
})
