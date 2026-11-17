import { describe, expect, it } from 'vitest'
import { CHARTS } from '../../types/chart.types'
import type { QueryResult } from '../../types/query.types'
import { adversarialChart, RESHAPES_ROWS } from './fixtures'
import { adaptChart } from './index'

// Every chart type over the one result that holds what has reached a screen
// wrong before. Whatever a filler hands the renderer, it must have read off the
// result: a "null" label, a null drawn as 0 or a dropped row is a value the
// result never held.

const MADE_UP_TEXT = /^(null|undefined|NaN|Infinity|Invalid Date|\[object Object\])$/

type Leaf = { path: string; value: unknown; inArray: boolean }

function leavesOf(value: unknown, path = 'props', inArray = false, seen = new Set()): Leaf[] {
	if (typeof value === 'function') return []
	if (value === null || typeof value !== 'object') return [{ path, value, inArray }]
	if (seen.has(value)) return []
	seen.add(value)
	return Object.entries(value).flatMap(([key, child]) =>
		leavesOf(child, `${path}.${key}`, inArray || Array.isArray(value), seen),
	)
}

function rowArraysOf(value: unknown, result: QueryResult, found: unknown[][] = []): unknown[][] {
	if (value === null || typeof value !== 'object') return found
	const keys = result.columns
		.map((column) => column.name)
		.sort()
		.join()
	if (
		Array.isArray(value) &&
		value.length &&
		value.every((row) => row && Object.keys(row).sort().join() === keys)
	) {
		found.push(value)
	}
	Object.values(value).forEach((child) => rowArraysOf(child, result, found))
	return found
}

/** Every value the result holds, and the number a numeric one reads as. */
function heldBy(result: QueryResult): Set<unknown> {
	const held = new Set<unknown>()
	for (const row of [...result.rows, ...result.formattedRows]) {
		for (const cell of Object.values(row)) {
			held.add(cell)
			if (typeof cell === 'string' && cell.trim() !== '' && !isNaN(Number(cell))) {
				held.add(Number(cell))
			}
		}
	}
	result.columns.forEach((column) => held.add(column.name).add(column.type))
	return held
}

describe.each(CHARTS)('a %s chart over nulls, text numbers and boundary dates', (chart_type) => {
	const input = adversarialChart(chart_type)
	const filler = adaptChart(input)

	// @feature charts.every-type-draws-what-the-result-holds
	it('renders', () => {
		expect(filler).toBeDefined()
	})

	// @feature charts.every-type-draws-what-the-result-holds
	it('prints no text the result did not hold', () => {
		const made = leavesOf(filler?.props).filter(
			(leaf) =>
				(typeof leaf.value === 'string' && MADE_UP_TEXT.test(leaf.value)) ||
				(typeof leaf.value === 'number' && !Number.isFinite(leaf.value)),
		)
		expect(made).toEqual([])
	})

	// A number may be summed or laid out from the result, so it is not asked to be
	// held. It is asked not to be zero: the result holds none, so a zero is a null
	// or a text drawn as one.
	// @feature charts.every-type-draws-what-the-result-holds
	it('plots no label the result did not hold and no null as zero', () => {
		const held = heldBy(input.result)
		const made = leavesOf(filler?.props).filter(
			(leaf) =>
				leaf.inArray &&
				((typeof leaf.value === 'string' && !held.has(leaf.value)) || leaf.value === 0),
		)
		expect(made).toEqual([])
	})

	// @feature charts.every-type-draws-what-the-result-holds
	it('drops no row and merges no two values of a column', () => {
		const found = rowArraysOf(filler?.props, input.result)
		// a type that reshapes its rows says so in the fixture, and is held to it
		if (RESHAPES_ROWS.includes(chart_type)) expect(found).toHaveLength(0)
		else expect(found).not.toHaveLength(0)
		for (const rows of found) {
			expect(rows).toHaveLength(input.result.rows.length)
			for (const { name } of input.result.columns) {
				const distinct = (list: any[]) =>
					new Set(
						list.map((row) => row[name]).filter((cell) => cell !== null && cell !== ''),
					).size
				expect(distinct(rows), name).toBe(distinct(input.result.rows))
			}
		}
	})
})
