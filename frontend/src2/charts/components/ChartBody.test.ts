import { describe, expect, it } from 'vitest'
import { createSSRApp, h } from 'vue'
import { renderToString } from 'vue/server-renderer'
import { numberChart } from '../adapter/fixtures'
import { makeChartRead } from '../chart_view'
import { scopeText } from '../scoped_by'
import ChartBody from './ChartBody.vue'

// What the card says about the reader's own permissions, drawn. The state
// itself is settled in `chart_view.test.ts`; these cases are about the room it
// takes on a card, which only a render can answer.
//
// A Number Chart is the card the room is tightest on: a reading is one line
// tall, so a line the chrome adds is a line taken off the number.

const spec = numberChart({ values: [{ name: 'Revenue', readings: [12300] }], reading: 'Revenue' })

/** The card as a reader gets it, with the answer the server gave it. */
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

async function draw(answer: Record<string, any>) {
	const read = cardAnswering(answer)
	await read.load()
	const app = createSSRApp({
		render: () => h(ChartBody, { chart: read, title: 'Revenue', reading: 'Revenue' }),
	})
	// the app registers frappe-ui's components globally; this render is one
	// component and does not need them resolved
	app.config.warnHandler = () => {}
	return renderToString(app)
}

const rows = { columns: spec.result.columns, rows: spec.result.rows }

describe('a card whose rows the reader User Permissions narrowed', () => {
	// @feature permissions.card-says-it-is-scoped
	it('sets the mark against the title and leaves the reading its whole card', async () => {
		const html = await draw({
			...rows,
			user_permissions: [{ doctype: 'Territory', documents: ['Karnataka'] }],
		})

		// the sentence is the mark's label and nothing else: a line under the
		// plot cost the card a line of its height, and on a Number Chart that
		// line is the reading
		expect(html.match(/Filtered by your User Permissions/g)).toHaveLength(1)
		expect(html).toContain('Filtered by your User Permissions: Territory: Karnataka')
		expect(html).toContain('12,300')

		// Beside the title itself, not in `#actions` at the far end of the row:
		// between the title text and the mark the card closes no element, so the
		// two are in the one box — the box that carries the title's font size,
		// which is what makes an `em` the size of the title it sits on.
		const between = html.slice(
			html.indexOf('>Revenue<'),
			html.indexOf('aria-label="Filtered by your User Permissions'),
		)
		expect(between).not.toContain('</div>')
		expect(html).toContain('size-[0.85em]')
	})

	// @feature permissions.card-says-it-is-scoped
	it('sets the same mark when a restriction that names nothing narrowed it', async () => {
		const html = await draw({ ...rows, narrowed_by_permissions: true })

		expect(html).toContain('aria-label="Narrowed by your permissions"')
		expect(html).toContain('12,300')
	})

	// @feature permissions.card-says-it-is-scoped
	it('is the card it was when no User Permission narrowed it', async () => {
		const html = await draw(rows)
		expect(html).not.toContain('Filtered by your User Permissions')
		expect(html).toContain('12,300')
	})
})

// The bubble itself is a portal that opens on hover, so what it says is settled
// here, where the card's own render cannot reach it.
describe('what the mark says', () => {
	// @feature permissions.card-says-it-is-scoped
	it('gives the bubble a line per doctype, by name', () => {
		const said = scopeText([
			{ doctype: 'Territory', documents: ['Karnataka', 'Kerala'] },
			{ doctype: 'Company', documents: ['Summit Supply'] },
		])

		expect(said?.heading).toBe('Filtered by your User Permissions')
		expect(said?.lines).toEqual(['Company: Summit Supply', 'Territory: Karnataka, Kerala'])
		// the label is the same fact in one go, which is how it is read out
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
	it('keeps the card a reading draws and says what it needs inside it', async () => {
		const html = await draw({ not_permitted: { doctypes: ['Sales Invoice'] } })

		expect(html).toContain('Not Permitted')
		expect(html).toContain('Needs read access to Sales Invoice')
		// the card every other state gets: the reading's own surface, headed by
		// the reading's own title, with the message where the number stood
		expect(html).toContain('data-slot="chart-card"')
		expect(html).toContain('Revenue')
		expect(html).not.toContain('12,300')
		// there is no permission the reader could change
		expect(html).not.toContain('Retry')
	})
})
