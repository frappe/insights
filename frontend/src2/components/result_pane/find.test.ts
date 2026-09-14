import { describe, expect, it } from 'vitest'
import type { QueryResultColumn, QueryResultRow } from '../../types/query.types'
import { findColumns, findRows } from './find'

const rows: QueryResultRow[] = [
	{ customer: 'Acme', amount: 120, paid_on: null },
	{ customer: 'Bakery', amount: 12, paid_on: '2026-01-02' },
	{ customer: 'Cement Co', amount: 3, paid_on: '2026-02-03' },
]

const columns: QueryResultColumn[] = [
	{ name: 'customer', type: 'String' },
	{ name: 'amount', type: 'Integer' },
	{ name: 'paid_on', type: 'Date' },
]

describe('findRows', () => {
	// @feature query.result-find
	it('returns every row for an empty or blank term', () => {
		expect(findRows(rows, '')).toBe(rows)
		expect(findRows(rows, '   ')).toBe(rows)
	})

	// @feature query.result-find dashboard.card-find
	it('matches any column, case-insensitively', () => {
		expect(findRows(rows, 'acme')).toEqual([rows[0]])
		expect(findRows(rows, 'CEMENT')).toEqual([rows[2]])
	})

	// @feature query.result-find
	it('matches a substring of a printed number', () => {
		expect(findRows(rows, '12')).toEqual([rows[0], rows[1]])
	})

	// @feature query.result-find
	it('treats a null cell as empty rather than as "null"', () => {
		expect(findRows(rows, 'null')).toEqual([])
	})
})

describe('findColumns', () => {
	// @feature query.result-find
	it('matches nothing for an empty term', () => {
		expect(findColumns(columns, '')).toEqual([])
	})

	// @feature query.result-find
	it('matches column names case-insensitively, in result order', () => {
		expect(findColumns(columns, 'M').map((c) => c.name)).toEqual(['customer', 'amount'])
		expect(findColumns(columns, 'ON').map((c) => c.name)).toEqual(['paid_on'])
	})
})
