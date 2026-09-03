import { describe, expect, it } from 'vitest'
import { mergeWriteAnswer } from './write_answer'

// The three inputs a write settles from: what is on screen, what the write
// carried, and what the server sent back.
function saved(current: Record<string, any>, answer: Record<string, any>) {
	// nothing moved while the write was in flight, so what was sent is what is on
	// screen
	const sent = JSON.parse(JSON.stringify(current))
	return mergeWriteAnswer(current, answer, sent)
}

describe('mergeWriteAnswer', () => {
	it('keeps the object it already holds when the answer repeats it', () => {
		const config = { x_axis: { column_name: 'creation' } }
		const merged = saved(
			{ title: 'Chart 1', config },
			{ title: 'Chart 1', config: copyOf(config) },
		)
		expect(merged.config).toBe(config)
	})

	it('keeps it even when the server sorted the keys on the way back', () => {
		const config = { x_axis: { column_name: 'creation', granularity: 'month' } }
		const sorted = { x_axis: { granularity: 'month', column_name: 'creation' } }
		const merged = saved({ config }, { config: sorted })
		expect(merged.config).toBe(config)
	})

	it('takes a field the server changed', () => {
		const merged = saved({ title: 'Chart 1', is_public: 0 }, { title: 'Chart 1', is_public: 1 })
		expect(merged.is_public).toBe(1)
	})

	it('keeps an edit made while the write was in flight', () => {
		const current = { title: 'Chart 2' }
		const sent = { title: 'Chart 1' }
		const answer = { title: 'Chart 1' }
		expect(mergeWriteAnswer(current, answer, sent).title).toBe('Chart 2')
	})

	it('lets the answer win where the document holds undefined', () => {
		// `copy` drops an undefined value, so holding on to one would leave the
		// document dirty for good
		const merged = mergeWriteAnswer({ folder: undefined }, { folder: null }, {})
		expect(merged.folder).toBe(null)
	})
})

function copyOf<T>(value: T): T {
	return JSON.parse(JSON.stringify(value))
}
