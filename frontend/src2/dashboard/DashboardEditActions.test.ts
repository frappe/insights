import { describe, expect, it, vi } from 'vitest'
import { createSSRApp, h, reactive } from 'vue'
import { renderToString } from 'vue/server-renderer'

// the router needs a mounted page
vi.mock('../router', () => ({ default: { push() {}, resolve: () => ({ href: '/' }) } }))

import DashboardEditActions from './DashboardEditActions.vue'

async function actions(doc: Record<string, any>) {
	const app = createSSRApp({ render: () => h(DashboardEditActions) })
	app.provide('dashboard', reactive({ editing: false, doc: { items: [], ...doc } }))
	// the app registers frappe-ui's Button globally; this stub renders its label
	app.component('Button', {
		props: ['label'],
		render() {
			return h('span', (this as any).label)
		},
	})
	app.config.warnHandler = () => {}
	return renderToString(app)
}

describe('the dashboard builder actions', () => {
	// @feature shared.publish-needs-share
	it('offers Share where the server says the caller may share, and nowhere else', async () => {
		expect(await actions({ read_only: false, can_share: true })).toContain('Share')
		expect(await actions({ read_only: false, can_share: false })).not.toContain('Share')
		expect(await actions({ read_only: false, can_share: false })).toContain('Edit')
	})
})
