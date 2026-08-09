import { describe, expect, it } from 'vitest'
import TableChart from '../components/TableChart.vue'
import { tableChart, type TableChartSpec } from './fixtures'
import { adaptChart } from './index'
import type { ChartAdapterInput } from './types'

// A Table has no plot, so what is asserted here is the table it is handed: the
// rows, the affordances, and which of them the surface may offer at all.

function adapt(input: ChartAdapterInput) {
	const filler = adaptChart(input)
	if (!filler) throw new Error('the adapter drew nothing for this Chart')
	return filler
}

const propsOf = (spec: TableChartSpec) => adapt(tableChart(spec)).props

describe('the grid', () => {
	it('draws the result as it stands, formatted for reading', () => {
		const input = tableChart({ rows: ['region'], values: ['revenue'] })
		const { component, props } = adapt(input)

		expect(component).toBe(TableChart)
		expect(props.columns).toBe(input.result.columns)
		expect(props.rows).toBe(input.result.formattedRows)
	})

	it('takes a pivot as the columns the server sent back', () => {
		// The pivot happens in SQL, so a split value reaches the table as a column
		// like any other. Nothing here re-shapes the rows.
		const props = propsOf({
			rows: ['category'],
			pivot: { dimension: 'department', into: ['Men', 'Women'] },
			values: ['revenue'],
		})
		expect(props.columns.map((column: any) => column.name)).toEqual([
			'category',
			'Men',
			'Women',
		])
	})

	it('draws nothing until the result holds a column', () => {
		const input = tableChart({ values: ['revenue'] })
		expect(adaptChart({ ...input, result: { ...input.result, columns: [] } })).toBeUndefined()
	})
})

describe('what the author put on the table', () => {
	it('asks for the totals, the filter row and the reading options it was set', () => {
		const props = propsOf({
			rows: ['category'],
			values: ['revenue'],
			filterRow: true,
			rowTotals: true,
			columnTotals: true,
			compactNumbers: true,
			colorScale: true,
			stickyColumns: ['category'],
			columnWidths: { category: 240 },
			textWrap: { category: true },
		})

		expect(props.showFilterRow).toBe(true)
		expect(props.showRowTotals).toBe(true)
		expect(props.showColumnTotals).toBe(true)
		expect(props.compactNumbers).toBe(true)
		expect(props.enableColorScale).toBe(true)
		expect(props.stickyColumns).toEqual(['category'])
		expect(props.columnWidths).toEqual({ category: 240 })
		expect(props.textWrap).toEqual({ category: true })
	})

	it('asks for nothing the Chart did not set', () => {
		const props = propsOf({ rows: ['category'], values: ['revenue'] })
		expect(props.showFilterRow).toBeUndefined()
		expect(props.showRowTotals).toBeUndefined()
		expect(props.showColumnTotals).toBeUndefined()
		expect(props.compactNumbers).toBeUndefined()
		expect(props.enableColorScale).toBeUndefined()
		expect(props.formatGroup).toBeUndefined()
		expect(props.columnFormats).toBeUndefined()
	})

	it('carries a conditional format to the column it was set on', () => {
		const props = propsOf({
			rows: ['category'],
			values: ['revenue'],
			highlight: { column: 'revenue', below: 100, color: 'red' },
		})
		expect(props.formatGroup.columns.map((column: any) => column.column_name)).toEqual([
			'revenue',
		])
	})

	it('tells the table which Measure holds a rate, so it prints one', () => {
		const props = propsOf({
			rows: ['category'],
			values: ['revenue', { name: 'margin_rate', format: 'percent' }],
		})
		expect(props.columnFormats).toEqual({ margin_rate: 'percent' })
	})
})

describe('the sort', () => {
	it('draws the arrows the Chart is ordered by', () => {
		const props = propsOf({
			rows: ['category'],
			values: ['revenue'],
			sortedBy: [{ column: 'revenue', direction: 'desc' }],
		})
		expect(props.sortOrder).toEqual({ revenue: 'desc' })
	})

	it('writes a sort back to the Chart, which is what the next run reads', () => {
		const input = tableChart({ rows: ['category'], values: ['revenue'] })

		adapt(input).props.onSortChange('revenue', 'asc')
		expect(adapt(input).props.sortOrder).toEqual({ revenue: 'asc' })

		adapt(input).props.onSortChange('revenue', 'desc')
		expect(adapt(input).props.sortOrder).toEqual({ revenue: 'desc' })

		adapt(input).props.onSortChange('revenue', '')
		expect(adapt(input).props.sortOrder).toEqual({})
	})

	it('offers a reader no sort at all', () => {
		// A sort re-runs the query off a rewritten config, and a reader holds
		// neither half, so the arrow is left out rather than drawn dead.
		const input = tableChart({
			rows: ['category'],
			values: ['revenue'],
			sortedBy: [{ column: 'revenue', direction: 'desc' }],
		})
		const props = adapt({ ...input, readonly: true }).props

		expect(props.onSortChange).toBeUndefined()
		expect(props.sortOrder).toEqual({ revenue: 'desc' })
	})
})

describe('a run in flight', () => {
	it('says so over the rows it is keeping', () => {
		const input = tableChart({ rows: ['category'], values: ['revenue'] })
		expect(adapt({ ...input, executing: true }).props.loading).toBe(true)
		expect(adapt(input).props.loading).toBeUndefined()
	})
})

describe('drilling into a cell', () => {
	it('names the column and the row behind it', () => {
		const input = tableChart({ rows: ['category'], values: ['revenue'] })
		const filler = adapt(input)

		expect(filler.props.drillable).toBe(true)
		// The table draws the formatted rows and a drill-down names a raw one.
		expect(
			filler.drillDown!.cellClick({
				column: input.result.columns[1],
				row: input.result.formattedRows[1],
			}),
		).toEqual({ column: 'revenue', row: input.result.rows[1] })
	})

	// Only the rows the table was handed have a raw row behind them. A row from
	// anywhere else drills into nothing — and `rawRowOf` says so out loud, because
	// there is no reading of the data under which this is a click on empty space.
	it('drills into nothing from a row the result does not carry', () => {
		const input = tableChart({ rows: ['category'], values: ['revenue'] })
		const filler = adapt(input)

		expect(
			filler.drillDown!.cellClick({
				column: input.result.columns[1],
				row: { category: 'Total', revenue: 999 },
			}),
		).toBeUndefined()
	})

	// Inspecting a cell changes nothing about the Chart, so it is offered wherever
	// the Chart is drawn — unlike the sort beside it, which rewrites the config.
	it('is offered to a reader too, who inspects without rewriting anything', () => {
		const props = adapt({ ...tableChart({ values: ['revenue'] }), readonly: true }).props
		expect(props.drillable).toBe(true)
		expect(props.onSortChange).toBeUndefined()
	})
})
