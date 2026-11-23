import { describe, expect, it, vi } from 'vitest'
import { createSSRApp, h, reactive } from 'vue'
import { renderToString } from 'vue/server-renderer'

vi.mock('../components/UserSelector.vue', () => ({ default: { render: () => null } }))
vi.mock('../components/VisibilitySelector.vue', () => ({ default: { render: () => null } }))
vi.mock('../users/users', () => ({
	default: () => ({ getName: () => '', getImage: () => '', getUser: () => undefined }),
}))

import session from '../session'
import DashboardShareDialog from './DashboardShareDialog.vue'

async function shareDialog(owner: string) {
	const app = createSSRApp({ render: () => h(DashboardShareDialog as any, { modelValue: true }) })
	app.provide(
		'dashboard',
		reactive({
			doc: { owner, visibility: 'Private', visible_to_roles: [], people_with_access: [] },
			getShareLink: () => '',
		}),
	)
	// a dialog renders through a portal, which a server render leaves empty
	app.component('Dialog', {
		props: ['actions'],
		render() {
			const self = this as any
			return h('div', [
				self.$slots.default?.(),
				...self.actions.map((action: any) => h('span', action.label)),
			])
		},
	})
	app.component('Button', {
		props: ['label'],
		render() {
			return h('span', (this as any).label)
		},
	})
	app.config.warnHandler = () => {}
	return (await renderToString(app)).replace(/<!--[\s\S]*?-->/g, '')
}

describe('the dashboard share dialog', () => {
	// @feature permissions.share-dashboard
	it('saves with Save and names its owner, as the workbook share dialog does', async () => {
		session.user.email = 'reader@example.com'
		session.user.first_name = 'Rea'
		const html = await shareDialog('owner@example.com')

		expect(html).toMatch(/>\s*Save\s*</)
		expect(html).not.toMatch(/>\s*Done\s*</)
		expect(html).toContain('owner@example.com')
		expect(html).not.toMatch(/>\s*You\s*</)
	})
})
