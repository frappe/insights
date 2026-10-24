import { describe, expect, it } from 'vitest'
import { createSSRApp, h } from 'vue'
import { renderToString } from 'vue/server-renderer'
import NumberCards from './NumberCards.vue'

const bordered = /data-slot="chart-card"[^>]*class="[^"]*\bborder\b/
// the size of the host's own number, on the card's root
const hostSized = /data-slot="chart-card"[^>]*class="[^"]*:text-xl-semibold/

// the title row's slots, which stand on the row without its height
const zeroHeight = /class="([^"]* )?h-0[ "]/

const revenue = { column: 'Revenue', title: 'Revenue', value: '₹ 1,200', height: 72 }

function cards(props: Record<string, unknown>) {
	const app = createSSRApp({ render: () => h(NumberCards, { cards: [revenue], ...props }) })
	app.config.warnHandler = () => {}
	return renderToString(app)
}

describe('a Number reading in a card the host draws', () => {
	// @feature desk.number-card-island
	it('draws its own card and title on an Insights surface', async () => {
		const html = await cards({ reading: 'Revenue' })
		expect(html).toMatch(bordered)
		expect(html).toContain('>Revenue</span>')
		expect(html).not.toMatch(hostSized)
	})

	// @feature desk.number-card-island
	it('draws the number alone, at the size of the host number, when the host draws the card', async () => {
		// What `ChartIsland` renders in a desk Number Card.
		const html = await cards({ cards: [{ ...revenue, card: false }] })
		expect(html).not.toMatch(bordered)
		expect(html).not.toContain('>Revenue</span>')
		expect(html).toContain('₹ 1,200')
		expect(html).toMatch(hostSized)
	})

	// @feature desk.number-card-island
	it('keeps the retry and the marks out of the title row the host card cuts', async () => {
		// What `ChartIsland` renders in a desk Number Card. Its title row is empty,
		// zero height, on the top edge of the host's card.
		const failure = { headline: 'Query failed' }
		const marked = { ...revenue, info: 'Paid only', delta: 5, deltaCaption: 'vs last month' }

		const failed = await cards({ cards: [{ ...revenue, card: false }], failure })
		expect(failed).toMatch(/role="status".*title="Retry"/s)
		expect(failed).not.toMatch(zeroHeight)
		const scoped = await cards({ cards: [{ ...marked, card: false }] })
		expect(scoped).toMatch(/vs last month<\/span>.*aria-label="Info"/s)
		expect(scoped).not.toMatch(zeroHeight)

		expect(await cards({ failure })).toMatch(/h-0[^"]*justify-end.*title="Retry"/s)
		expect(await cards({ cards: [marked] })).toMatch(
			/h-0[^"]*">.*aria-label="Info".*vs last month/s,
		)
	})
})

describe('a Number reading with no value', () => {
	// @feature charts.type-number
	it('says No data on the one line its number takes', async () => {
		// A card with no comparison is one line shorter than a dash and a caption.
		const rendered = await cards({ cards: [{ ...revenue, value: null }] })
		const html = rendered.replace(/<!--[\s\S]*?-->/g, '')
		expect(html).toContain('No data')
		// in place of the number line, not under it
		expect(html).not.toMatch(/ text-3xl-semibold tabular-nums/)
	})
})

describe('a Number reading in a narrow card', () => {
	// @feature dashboard.number-card-fits
	it('sizes its number to the card, by how long it prints', async () => {
		const long = { ...revenue, value: 6254980.1, prefix: '₹ ', format: () => '62,54,980.10' }
		const html = await cards({ cards: [long] })

		expect(html).toMatch(/container-type:\s*inline-size/)
		expect(html).toMatch(/--reading-length:\s*14/)
	})

	// @feature dashboard.number-card-fits
	it('gives every reading of a preview the room to print', async () => {
		expect(await cards({ preview: true })).toMatch(/min-w-\[/)
	})
})
