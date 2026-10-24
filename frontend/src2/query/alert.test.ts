import { describe, expect, it, vi } from 'vitest'
import { createSSRApp, h } from 'vue'
import { renderToString } from 'vue/server-renderer'

const stored = vi.hoisted(() => [] as any[])
vi.mock('frappe-ui', async (importOriginal) => ({
	...(await importOriginal<object>()),
	call: () => Promise.resolve(stored),
}))

import useAlertStore from './alert'
import QueryAlertsDialog from './components/QueryAlertsDialog.vue'

const alert = (title: string, disabled: 0 | 1) => ({
	name: title.toLowerCase().replace(/\W+/g, '-'),
	title,
	disabled,
	owner: 'author@example.com',
	last_execution: '',
})

async function alertsList(alerts: any[]) {
	stored.splice(0, stored.length, ...alerts)
	useAlertStore().alerts = alerts
	const app = createSSRApp({
		render: () =>
			h(QueryAlertsDialog, { modelValue: true, query: { doc: { name: 'query-1' } } as any }),
	})
	// the app registers these globally; a dialog renders through a portal, which
	// a server render leaves empty, so these stubs render the dialog's body in place
	app.component('Dialog', {
		render() {
			return h('div', (this as any).$slots.default?.())
		},
	})
	app.component('FormControl', { render: () => h('input') })
	app.component('Button', {
		render() {
			return h('button', (this as any).$slots.default?.())
		},
	})
	app.config.warnHandler = () => {}
	return renderToString(app)
}

describe('the alerts of a query', () => {
	// @feature alerts.enable
	it('lists a disabled alert as a row that opens, so it can be enabled again', async () => {
		const html = await alertsList([alert('Daily email', 0), alert('Cron email', 1)])

		expect(html).toContain('Cron email')
		expect(html).toContain('Disabled')
		expect(html).not.toContain('aria-disabled="true"')
	})
})
