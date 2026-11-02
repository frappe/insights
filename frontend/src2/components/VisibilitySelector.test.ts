import { describe, expect, it, vi } from 'vitest'
import { createSSRApp, h } from 'vue'
import { renderToString } from 'vue/server-renderer'
import { MultiSelect } from 'frappe-ui'

vi.mock('../users/roles', () => ({
	default: () => ({ roles: ['Sales User', 'Accounts User'], loading: false }),
}))

import VisibilitySelector from './VisibilitySelector.vue'

async function rendered(roles: string[]) {
	const app = createSSRApp({
		render: () => h(VisibilitySelector, { visibility: 'Roles', roles }),
	})
	app.component('MultiSelect', MultiSelect)
	// the level picker is not under test
	app.component('Combobox', { render: () => h('span') })
	app.config.warnHandler = () => {}
	return renderToString(app)
}

describe('the roles a dashboard or chart is visible to', () => {
	// @feature permissions.visibility
	it('shows the roles picked, as they were saved', async () => {
		expect(await rendered(['Sales User'])).toContain('Sales User')
		expect(await rendered(['Sales User', 'Accounts User'])).toContain(
			'Sales User, Accounts User',
		)
		expect(await rendered([])).toContain('Select roles')
	})
})
