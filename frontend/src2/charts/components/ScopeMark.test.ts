import { describe, expect, it } from 'vitest'
import { createSSRApp, h } from 'vue'
import { renderToString } from 'vue/server-renderer'
import ScopeMark from './ScopeMark.vue'

function mark(props: Record<string, unknown>) {
	const app = createSSRApp({ render: () => h(ScopeMark, props) })
	app.config.warnHandler = () => {}
	return renderToString(app)
}

describe('the scope mark', () => {
	// @feature permissions.card-says-it-is-scoped
	it('says the cells were narrowed', async () => {
		expect(await mark({ narrowed: true })).toContain(
			'aria-label="Narrowed by your permissions"',
		)
	})

	// @feature permissions.card-says-it-is-scoped
	it('renders nothing where nothing narrowed the cells', async () => {
		expect(await mark({ applied: [], narrowed: false })).not.toContain('aria-label')
	})
})
