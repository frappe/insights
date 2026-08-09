import { describe, expect, it } from 'vitest'
import type { ChartConfig } from '../../types/chart.types'
import type { Dimension } from '../../types/query.types'
import {
	axisChart,
	donutChart,
	numberChart,
	sankeyChart,
	tableChart,
	type AxisChartSpec,
} from '../adapter/fixtures'
import {
	breakdownCandidates,
	declaredDimensionColumns,
	drillGranularity,
	grainsFor,
	makeDrillStack,
	queryResultChart,
	segmentOf,
	type DrillChart,
	type DrillDimension,
	type DrillEntry,
} from './drill_stack'

// Everything here asserts on the descriptor a click produces and on the trail
// the reader ends up reading. What the dialog draws from either is the dialog's
// business, and it stays on manual verification.

/** Clicks a value column on the row the given category came back on. */
function click(input: { config: ChartConfig; chart_type: string; result: any }, column: string, category?: any) {
	const chart = { chart_type: input.chart_type, config: input.config } as DrillChart
	const rows = input.result.rows
	const row =
		category === undefined
			? rows[0]
			: rows.find((candidate: any) => Object.values(candidate).includes(category))
	return segmentOf(chart, { column, row })
}

describe('what a segment click pins', () => {
	it('pins the Dimension the bar stands at, as an equality on a literal', () => {
		const segment = click(
			axisChart({ type: 'Bar', dimension: 'region', measures: ['revenue'] }),
			'revenue',
			'South',
		)
		expect(segment.filters).toEqual([{ column: 'region', operator: '=', value: 'South' }])
		expect(segment.pins).toEqual(['region'])
		expect(segment.label).toBe('South')
		expect(segment.measure).toBe('revenue')
	})

	it('files the pin under the column the query has, and reads the value off the column the result has', () => {
		// A summarize names its output after the Dimension; the drill is validated
		// against the surface *before* it, which still calls the column its own name.
		const dimension: Dimension = {
			dimension_name: 'Status',
			column_name: 'workflow_status',
			data_type: 'String',
		}
		const chart: DrillChart = {
			chart_type: 'Bar',
			config: {
				x_axis: { dimension },
				y_axis: { series: [{ measure: { measure_name: 'count' } }] },
			} as unknown as ChartConfig,
		}
		expect(segmentOf(chart, { column: 'count', row: { Status: 'Overdue' } }).filters).toEqual([
			{ column: 'workflow_status', operator: '=', value: 'Overdue' },
		])
	})

	it('pins nothing at all for a number card, which is the whole of the reading', () => {
		const segment = click(numberChart({ values: [{ name: 'revenue', readings: [100] }] }), 'revenue')
		expect(segment.filters).toEqual([])
		expect(segment.pins).toEqual([])
		expect(segment.label).toBe('')
		expect(segment.measure).toBe('revenue')
	})

	it('pins the slice a donut was clicked on', () => {
		const segment = click(donutChart({ category: 'status', measure: 'count' }), 'count', 'South')
		expect(segment.filters).toEqual([{ column: 'status', operator: '=', value: 'South' }])
	})

	it('pins the absence itself when the segment stands for the rows with no value', () => {
		const chart: DrillChart = {
			chart_type: 'Donut',
			config: {
				label_column: { dimension_name: 'owner', column_name: 'owner', data_type: 'String' },
				value_column: { measure_name: 'count' },
			} as unknown as ChartConfig,
		}
		expect(segmentOf(chart, { column: 'count', row: { owner: null } }).filters).toEqual([
			{ column: 'owner', operator: 'is_not_set', value: '' },
		])
	})

	it('pins both ends of a Sankey flow', () => {
		const segment = click(
			sankeyChart({ source: 'channel', target: 'category', measure: 'orders' }),
			'orders',
		)
		expect(segment.filters).toEqual([
			{ column: 'channel', operator: '=', value: 'Search' },
			{ column: 'category', operator: '=', value: 'Tops' },
		])
		expect(segment.label).toBe('Search · Tops')
	})
})

describe('a segment a split or a pivot drew', () => {
	const split: AxisChartSpec = {
		type: 'Bar',
		dimension: 'month',
		measures: ['revenue', 'profit'],
		splitBy: { dimension: 'department', into: ['Men', 'Women'] },
	}

	it('pins the axis value and the series value, and re-measures the Measure behind the segment', () => {
		// The clicked column is a pivoted one — the split's value is in its name and
		// nowhere else. Sending it as the Measure would name a column the
		// pre-summarize surface has never heard of.
		const segment = click(axisChart(split), 'profit___Women')
		expect(segment.filters).toEqual([
			{ column: 'month', operator: '=', value: 'North' },
			{ column: 'department', operator: '=', value: 'Women' },
		])
		expect(segment.pins).toEqual(['month', 'department'])
		expect(segment.measure).toBe('profit')
	})

	it('reads the Measure off the config when a lone Measure left the column unnamed', () => {
		const segment = click(
			axisChart({ ...split, measures: ['revenue'] }),
			'Women',
		)
		expect(segment.filters).toContainEqual({
			column: 'department',
			operator: '=',
			value: 'Women',
		})
		expect(segment.measure).toBe('revenue')
	})

	it('pins the row Dimensions and the column value of a pivot-table cell', () => {
		const segment = click(
			tableChart({
				rows: ['region'],
				pivot: { dimension: 'department', into: ['Men', 'Women'] },
				values: ['revenue', 'profit'],
			}),
			'revenue___Men',
			'North',
		)
		expect(segment.filters).toEqual([
			{ column: 'region', operator: '=', value: 'North' },
			{ column: 'department', operator: '=', value: 'Men' },
		])
		expect(segment.measure).toBe('revenue')
	})
})

describe('a segment on a date', () => {
	const dated = (granularity?: string, category?: any) =>
		click(
			axisChart({
				type: 'Line',
				dimension: { name: 'order_date', type: 'Date', ...(granularity ? { granularity } : {}) } as any,
				measures: ['revenue'],
				categories: [category ?? '2026-03-01'],
			}),
			'revenue',
		)

	// A bar grouped by month covers a span, but working the span out needs the
	// grain, and the grain lives in the pipeline the server slices. The client
	// says which bucket was clicked and nothing about how to match it.
	it('pins the bucket the bar stands for, and leaves the span to the pipeline', () => {
		expect(dated('month').filters).toEqual([
			{ column: 'order_date', operator: '=', value: '2026-03-01' },
		])
	})

	it('says the same for a grain a plain calendar has no name for', () => {
		expect(dated('fiscal_year').filters).toEqual([
			{ column: 'order_date', operator: '=', value: '2026-03-01' },
		])
	})

	it('reads the crumb at the grain the bar was grouped by', () => {
		expect(dated('month').label).toBe('March, 2026')
	})
})

describe('what "break down by" offers', () => {
	const available: DrillDimension[] = [
		{ name: 'region', type: 'String' },
		{ name: 'owner', type: 'String' },
		{ name: 'status', type: 'String' },
		{ name: 'priority', type: 'String' },
	]

	it('drops the columns the click already pins', () => {
		const segment = click(axisChart({ type: 'Bar', dimension: 'status', measures: ['count'] }), 'count')
		expect(breakdownCandidates(available, segment.pins, []).map((d) => d.name)).not.toContain(
			'status',
		)
	})

	it('drops a column a level further up already fixed', () => {
		expect(
			breakdownCandidates(available, ['status', 'region'], []).map((d) => d.name),
		).toEqual(['owner', 'priority'])
	})

	it('offers the Chart’s own other Dimensions first, in the order it declares them', () => {
		// A number card pins nothing, and the Dimension its readings are grouped by
		// is still one the chart talks about.
		const card = numberChart({
			values: [{ name: 'count', readings: [1] }],
			period: 'priority',
		})
		const chart = card as DrillChart
		expect(
			breakdownCandidates(available, click(card, 'count').pins, declaredDimensionColumns(chart)).map(
				(d) => d.name,
			),
		).toEqual(['priority', 'owner', 'region', 'status'])
	})

	it('sorts everything the Chart never named alphabetically', () => {
		const segment = segmentOf(
			{ chart_type: 'Number', config: { number_columns: [] } as unknown as ChartConfig },
			{ column: 'count', row: {} },
		)
		expect(breakdownCandidates(available, segment.pins, []).map((d) => d.name)).toEqual([
			'owner',
			'priority',
			'region',
			'status',
		])
	})
})

// The path the ticket wrote down, one entry per level.
const overdue: DrillEntry = {
	level: {
		segment_filters: [{ column: 'status', operator: '=', value: 'Overdue' }],
		action: { breakdown: 'region', measure: 'count' },
	},
	segmentLabel: 'Overdue',
	actionLabel: 'by Region',
}
const west: DrillEntry = {
	level: {
		segment_filters: [
			{ column: 'status', operator: '=', value: 'Overdue' },
			{ column: 'region', operator: '=', value: 'West' },
		],
		action: { records: true },
	},
	segmentLabel: 'West',
	actionLabel: 'Records',
}

describe('the trail', () => {
	it('reads as the path the reader took', () => {
		const stack = makeDrillStack()
		stack.push(overdue)
		stack.push(west)
		expect(stack.crumbs.map((crumb) => crumb.label)).toEqual([
			'Overdue',
			'by Region',
			'West',
			'Records',
		])
	})

	it('sends the levels and nothing else', () => {
		const stack = makeDrillStack()
		stack.push(overdue)
		expect(stack.levels).toEqual([overdue.level])
	})

	it('leaves out a crumb for a segment that pins nothing, as a number card does', () => {
		const stack = makeDrillStack()
		stack.push({ ...overdue, segmentLabel: '' })
		expect(stack.crumbs).toEqual([{ label: 'by Region', depth: 1 }])
	})

	it('points both of a level’s crumbs at the level they read', () => {
		const stack = makeDrillStack()
		stack.push(overdue)
		stack.push(west)
		expect(stack.crumbs.map((crumb) => crumb.depth)).toEqual([1, 1, 2, 2])
	})

	it('collects every column the path has fixed, so the menu stops offering them', () => {
		const stack = makeDrillStack()
		stack.push(overdue)
		stack.push(west)
		expect(stack.pinned).toEqual(['status', 'region'])
	})
})

describe('retracing', () => {
	it('pops to the level a crumb stands for', () => {
		const stack = makeDrillStack()
		stack.push(overdue)
		stack.push(west)
		stack.popTo(1)
		expect(stack.depth).toBe(1)
		expect(stack.current).toBe(overdue)
		expect(stack.crumbs.map((crumb) => crumb.label)).toEqual(['Overdue', 'by Region'])
	})

	it('pops back out of the dialog altogether', () => {
		const stack = makeDrillStack()
		stack.push(overdue)
		stack.pop()
		expect(stack.depth).toBe(0)
		expect(stack.current).toBeUndefined()
		expect(stack.levels).toEqual([])
	})
})

describe('what the dialog has already been told', () => {
	const rows = { columns: [{ name: 'name', type: 'String' as const }], rows: [{ name: 'TODO-1' }] }

	it('serves a level it has already asked for, so a pop costs nothing', () => {
		const stack = makeDrillStack()
		stack.push(overdue)
		stack.remember(rows)
		stack.push(west)
		expect(stack.answer()).toBeUndefined()

		stack.popTo(1)
		expect(stack.answer()).toEqual(rows)
	})

	it('holds an answer against the whole path, not against how deep it was', () => {
		// Pop and drill somewhere else and the depth is the same. Serving the old
		// level's rows there would be the wrong rows under the right crumb.
		const stack = makeDrillStack()
		stack.push(overdue)
		stack.remember(rows)
		stack.popTo(0)
		stack.push({ ...overdue, level: { ...overdue.level, action: { records: true } } })
		expect(stack.answer()).toBeUndefined()
	})
})

describe('reading a level at another grain', () => {
	// A breakdown by a date comes back in that date's own order, at a grain the
	// server picked from the span. Asking for another is the same level, asked
	// again — the ladder is unchanged and the reader has not gone anywhere.
	const byDate: DrillEntry = {
		level: {
			segment_filters: [{ column: 'status', operator: '=', value: 'Overdue' }],
			action: { breakdown: 'due_date', measure: 'count' },
		},
		segmentLabel: 'Overdue',
		actionLabel: 'by Due Date',
	}

	it('says the grain on the level itself, so the server is told what to group by', () => {
		const stack = makeDrillStack()
		stack.push(byDate)
		stack.regrain('week')
		expect(stack.levels).toEqual([
			{
				segment_filters: [{ column: 'status', operator: '=', value: 'Overdue' }],
				action: { breakdown: 'due_date', measure: 'count', granularity: 'week' },
			},
		])
	})

	it('replaces the level instead of descending, so back still goes where it went', () => {
		const stack = makeDrillStack()
		stack.push(overdue)
		stack.push(byDate)
		stack.regrain('quarter')
		expect(stack.depth).toBe(2)
		expect(stack.crumbs.map((crumb) => crumb.label)).toEqual([
			'Overdue',
			'by Region',
			'Overdue',
			'by Due Date',
		])
		stack.pop()
		expect(stack.levels).toEqual([overdue.level])
	})

	it('says nothing about a level that groups nothing', () => {
		const stack = makeDrillStack()
		stack.push(west)
		stack.regrain('week')
		expect(stack.levels).toEqual([west.level])
	})

	it('holds an answer against the grain it was asked at', () => {
		// The same level at another grain is another question, so the rows already
		// held are not an answer to it — and going back to a grain already asked
		// for costs nothing, exactly as retracing does.
		const weekly = { columns: [], rows: [{ due_date: '2026-03-02', count: 4 }] }
		const stack = makeDrillStack()
		stack.push(byDate)
		stack.remember({ columns: [], rows: [{ due_date: '2026-03-01', count: 30 }] })

		stack.regrain('week')
		expect(stack.answer()).toBeUndefined()
		stack.remember(weekly)

		stack.regrain('quarter')
		expect(stack.answer()).toBeUndefined()

		stack.regrain('week')
		expect(stack.answer()).toEqual(weekly)
	})
})

describe('the grains a breakdown can be read at', () => {
	const dimensions: DrillDimension[] = [
		{ name: 'due_date', type: 'Date' },
		{ name: 'creation', type: 'Datetime' },
		{ name: 'status', type: 'String' },
	]

	it('offers the calendar grains for a date', () => {
		expect(grainsFor(dimensions, 'due_date').map((grain) => grain.value)).toContain('month')
		expect(grainsFor(dimensions, 'creation').map((grain) => grain.value)).toContain('fiscal_year')
	})

	it('offers none for a column with no order of its own', () => {
		expect(grainsFor(dimensions, 'status')).toEqual([])
	})

	it('offers none for a column the response never carried', () => {
		expect(grainsFor(dimensions, 'owner')).toEqual([])
	})
})

describe('a query result read as a chart', () => {
	const status = { dimension_name: 'status', column_name: 'status', data_type: 'String' as const }
	const priority = {
		dimension_name: 'priority',
		column_name: 'priority',
		data_type: 'String' as const,
	}
	const todos = {
		measure_name: 'Todos',
		column_name: 'name',
		aggregation: 'count' as const,
		data_type: 'Integer' as const,
	}
	const source = {
		type: 'source' as const,
		table: { type: 'table' as const, data_source: 'Site DB', table_name: 'tabToDo' },
	}

	it('reads nothing out of a pipeline that aggregates nothing', () => {
		// a raw result has no numbers with rows behind them, so there is no
		// segment for a click to pin
		expect(queryResultChart([source])).toBeUndefined()
	})

	it('reads a summarize as the rows and values a Table declares', () => {
		const chart = queryResultChart([
			source,
			{ type: 'summarize', dimensions: [status], measures: [todos] },
		])!
		expect(chart.chart_type).toBe('Table')
		expect(declaredDimensionColumns(chart)).toEqual(['status'])
		// a cell click pins what the step grouped by, exactly as it would on a card
		expect(segmentOf(chart, { column: 'Todos', row: { status: 'Open' } }).filters).toEqual([
			{ column: 'status', operator: '=', value: 'Open' },
		])
	})

	it('reads a pivot as the rows and the columns it spread the values across', () => {
		const chart = queryResultChart([
			source,
			{ type: 'pivot_wider', rows: [status], columns: [priority], values: [todos] },
		])!
		expect(declaredDimensionColumns(chart)).toEqual(['status', 'priority'])
		// the split's value stands in the clicked column's name, nowhere else
		expect(
			segmentOf(chart, { column: 'Todos___High', row: { status: 'Open' } }).filters,
		).toEqual([
			{ column: 'status', operator: '=', value: 'Open' },
			{ column: 'priority', operator: '=', value: 'High' },
		])
	})

	it('reads the last step that aggregated, which is the one the result came off', () => {
		const chart = queryResultChart([
			source,
			{ type: 'summarize', dimensions: [status, priority], measures: [todos] },
			{ type: 'summarize', dimensions: [status], measures: [todos] },
		])!
		expect(declaredDimensionColumns(chart)).toEqual(['status'])
	})
})

describe('the grain a records level prints its dates at', () => {
	const columns = [
		{ name: 'creation', type: 'Datetime' as const },
		{ name: 'due_date', type: 'Date' as const },
		{ name: 'description', type: 'String' as const },
	]

	it('reads what the column type honestly is, so a records date reads as a date', () => {
		const granularity = drillGranularity(columns)
		expect(granularity.creation).toBe('second')
		expect(granularity.due_date).toBe('day')
	})

	it('says nothing about a column that is not a date', () => {
		expect(drillGranularity(columns).description).toBeUndefined()
	})
})
