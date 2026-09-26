import { describe, expect, it } from 'vitest'
import { createSSRApp, h } from 'vue'
import { renderToString } from 'vue/server-renderer'
import { numberChart } from '../adapter/fixtures'
import { makeChartRead } from '../chart_view'
import { scopeText } from '../scoped_by'
import ChartBody from './ChartBody.vue'

// A Number chart has the least space. A reading is one line tall, so any line
// the chrome adds is taken from the number.

const spec = numberChart({ values: [{ name: 'Revenue', readings: [12300] }], reading: 'Revenue' })

function cardAnswering(answer: Record<string, any>) {
	const read = makeChartRead({
		doc: {
			name: 'chart-1',
			title: 'Revenue',
			chart_type: 'Number',
			config: spec.config,
			can_write: false,
		} as any,
		requestKey: () => 'the same question',
		fetchData: () => Promise.resolve(answer),
		fetchDrillData: () => Promise.reject(new Error('not asked')),
	})
	return read
}

async function renderCard(answer: Record<string, any>) {
	const read = cardAnswering(answer)
	await read.load()
	const app = createSSRApp({
		render: () => h(ChartBody, { chart: read, title: 'Revenue', reading: 'Revenue' }),
	})
	// The app registers frappe-ui components globally. This test does not, so it
	// silences the warnings for unresolved components.
	app.config.warnHandler = () => {}
	return renderToString(app)
}

const rows = { columns: spec.result.columns, rows: spec.result.rows }

describe('a card whose rows the reader User Permissions narrowed', () => {
	// @feature permissions.card-says-it-is-scoped
	it('sets the mark against the title and leaves the reading its whole card', async () => {
		const html = await renderCard({
			...rows,
			user_permissions: [{ doctype: 'Territory', documents: ['Karnataka'] }],
		})

		// The sentence is only the mark's label. A line under the plot would take
		// a line of card height, and on a Number chart that line is the reading.
		expect(html.match(/Filtered by your User Permissions/g)).toHaveLength(1)
		expect(html).toContain('Filtered by your User Permissions: Territory: Karnataka')
		expect(html).toContain('12,300')

		// The mark is in the title's element, not in `#actions` at the end of the
		// row. That element sets the title's font size, so the mark's `em` size
		// matches the title.
		const between = html.slice(
			html.indexOf('>Revenue<'),
			html.indexOf('aria-label="Filtered by your User Permissions'),
		)
		expect(between).not.toContain('</div>')
		expect(html).toContain('size-[0.85em]')
	})

	// @feature permissions.card-says-it-is-scoped
	it('sets the same mark when a restriction that names nothing narrowed it', async () => {
		const html = await renderCard({ ...rows, narrowed_by_permissions: true })

		expect(html).toContain('aria-label="Narrowed by your permissions"')
		expect(html).toContain('12,300')
	})

	// @feature permissions.card-says-it-is-scoped
	it('is the card it was when no User Permission narrowed it', async () => {
		const html = await renderCard(rows)
		expect(html).not.toContain('Filtered by your User Permissions')
		expect(html).toContain('12,300')
	})
})

// The tooltip is a portal that opens on hover, so a card render cannot reach
// it. Its text is tested here.
describe('what the mark says', () => {
	// @feature permissions.card-says-it-is-scoped
	it('gives the bubble a line per doctype, by name', () => {
		const said = scopeText([
			{ doctype: 'Territory', documents: ['Karnataka', 'Kerala'] },
			{ doctype: 'Company', documents: ['Summit Supply'] },
		])

		expect(said?.heading).toBe('Filtered by your User Permissions')
		expect(said?.lines).toEqual(['Company: Summit Supply', 'Territory: Karnataka, Kerala'])
		// screen readers read the label, so it holds all the lines in one sentence
		expect(said?.sentence).toBe(
			'Filtered by your User Permissions: Company: Summit Supply; Territory: Karnataka, Kerala',
		)
	})

	// @feature permissions.card-says-it-is-scoped
	it('counts the documents it does not name', () => {
		const said = scopeText([
			{ doctype: 'Territory', documents: ['A', 'B', 'C', 'D', 'E', 'F', 'G'] },
		])

		expect(said?.lines).toEqual(['Territory: A, B, C, D, E and 2 more'])
	})

	// @feature permissions.card-says-it-is-scoped
	it('says the rows were narrowed when nothing can be named', () => {
		expect(scopeText([], true)).toEqual({
			heading: 'Narrowed by your permissions',
			lines: [],
			sentence: 'Narrowed by your permissions',
		})
		expect(scopeText([{ doctype: 'Territory', documents: ['Kerala'] }], true)?.sentence).toBe(
			'Filtered by your User Permissions: Territory: Kerala; Narrowed by your permissions',
		)
	})

	// @feature permissions.card-says-it-is-scoped
	it('says nothing when no User Permission narrowed the rows', () => {
		expect(scopeText([])).toBeNull()
		expect(scopeText(undefined)).toBeNull()
	})
})

describe('a card the reader may not read the data behind', () => {
	// @feature permissions.not-permitted-chart
	it('keeps the card a reading renders and says what it needs inside it', async () => {
		const html = await renderCard({ not_permitted: { doctypes: ['Sales Invoice'] } })

		expect(html).toContain('Not Permitted')
		expect(html).toContain('Needs read access to Sales Invoice')
		expect(html).toContain('data-slot="chart-card"')
		expect(html).toContain('Revenue')
		expect(html).not.toContain('12,300')
		// a retry cannot help, because the reader cannot change their permissions
		expect(html).not.toContain('Retry')
	})
})
