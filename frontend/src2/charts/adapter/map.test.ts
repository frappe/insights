import { use } from 'echarts/core'
import { registerChartModules } from 'frappe-ui/charts'
import { describe, expect, it } from 'vitest'
import { adaptChart } from './index'
import { mapChart, type MapChartSpec } from './fixtures'

// Everything here asserts on the props the plot is handed, and on the point a
// click resolves to. How the plot draws them is the component's business.

function adapt(spec: MapChartSpec) {
	const filler = adaptChart(mapChart(spec))
	if (!filler) throw new Error('the adapter drew nothing for this Chart')
	return filler
}

const propsOf = (spec: MapChartSpec) => adapt(spec).props

it('registers its series into the same echarts the chart mounts through', () => {
	// Map is the one chart type Insights registers an echarts module for, and
	// echarts keeps that registry in module state. frappe-ui is linked from the
	// framework checkout and carries an echarts of its own, so without the
	// resolver deduping the package the series would be registered into a copy
	// no chart instance reads — and the map would draw a blank plot with no
	// error. The build config is the fix; this is the guard on it.
	expect(registerChartModules).toBe(use)
})

describe('the geography', () => {
	it('names the map, the measure and the regions', () => {
		const props = propsOf({
			title: 'Revenue by country',
			measure: 'revenue',
			regions: [
				{ region: 'India', value: 30 },
				{ region: 'Japan', value: 20 },
			],
		})
		expect(props.title).toBe('Revenue by country')
		expect(props.map).toBe('world')
		expect(props.measure).toBe('revenue')
		expect(props.regions).toEqual([
			{ name: 'India', value: 30 },
			{ name: 'Japan', value: 20 },
		])
	})

	it('draws the India map when the Chart asks for it', () => {
		expect(propsOf({ mapType: 'india', regions: [{ region: 'Goa', value: 1 }] }).map).toBe(
			'india',
		)
	})

	it('draws nothing without both a region column and a measure', () => {
		const input = mapChart({ regions: [{ region: 'India', value: 30 }] })
		input.result.columns = input.result.columns.filter((c) => c.name !== 'revenue')
		expect(adaptChart(input)).toBeUndefined()
	})

	it('reads the biggest region first', () => {
		const props = propsOf({
			regions: [
				{ region: 'Japan', value: 20 },
				{ region: 'India', value: 30 },
			],
		})
		expect(props.regions.map((region: any) => region.name)).toEqual(['India', 'Japan'])
	})

	it('sums the rows that land on one region', () => {
		// A region column is not a group by: two spellings of one country arrive
		// as two rows and the geography can only draw one shape for them.
		const props = propsOf({
			regions: [
				{ region: 'india', value: 30 },
				{ region: 'INDIA', value: 12 },
			],
		})
		expect(props.regions).toEqual([{ name: 'India', value: 42 }])
	})

	it('leaves out a row with no region', () => {
		const props = propsOf({
			regions: [
				{ region: 'India', value: 30 },
				{ region: null, value: 12 },
			],
		})
		expect(props.regions).toEqual([{ name: 'India', value: 30 }])
	})
})

describe('region mappings', () => {
	// The gallery's case: the world GeoJSON says `United States of America` and
	// `Brazil`, the data says `United States` and `Brasil`, and the two are 37
	// percent of the revenue. Without the mappings the map loses both silently.
	const gallery: MapChartSpec = {
		measure: 'revenue',
		regions: [
			{ region: 'United States', value: 500 },
			{ region: 'Brasil', value: 300 },
			{ region: 'India', value: 100 },
		],
		regionMappings: {
			'United States': 'United States of America',
			Brasil: 'Brazil',
		},
	}

	it('draws a mapped region under the name the geography carries', () => {
		expect(propsOf(gallery).regions).toEqual([
			{ name: 'United States of America', value: 500 },
			{ name: 'Brazil', value: 300 },
			{ name: 'India', value: 100 },
		])
	})

	it('resolves a click on a mapped region back to its row', () => {
		const input = mapChart(gallery)
		const filler = adaptChart(input)!
		expect(filler.drillDown!.regionClick('Brazil')).toEqual({
			column: 'revenue',
			row: input.result.rows[1],
		})
		expect(filler.drillDown!.regionClick('United States of America')).toEqual({
			column: 'revenue',
			row: input.result.rows[0],
		})
	})

	it('resolves a click on an unmapped region by its own name', () => {
		const input = mapChart(gallery)
		expect(adaptChart(input)!.drillDown!.regionClick('India')).toEqual({
			column: 'revenue',
			row: input.result.rows[2],
		})
	})

	it('resolves a click whatever case the geography spells it in', () => {
		const input = mapChart({ regions: [{ region: 'india', value: 30 }] })
		expect(adaptChart(input)!.drillDown!.regionClick('INDIA')).toEqual({
			column: 'revenue',
			row: input.result.rows[0],
		})
	})

	it('reports nothing for a region the query returned no rows for', () => {
		const input = mapChart(gallery)
		expect(adaptChart(input)!.drillDown!.regionClick('Chad')).toBeUndefined()
	})
})

describe('the natural-breaks scale', () => {
	const bucketsFor = (values: number[]) =>
		propsOf({
			regions: values.map((value, index) => ({ region: `r${index}`, value })),
		}).buckets

	it('opens the lowest class at zero and closes the highest at the largest value', () => {
		const buckets = bucketsFor([5, 40, 60, 900])
		expect(buckets[0].min).toBe(0)
		expect(buckets[buckets.length - 1].max).toBe(900)
	})

	it('runs low to high with no gap between one class and the next', () => {
		const buckets = bucketsFor([5, 40, 60, 900])
		buckets.forEach((bucket: any, index: number) => {
			expect(bucket.max).toBeGreaterThan(bucket.min)
			if (index) expect(bucket.min).toBe(buckets[index - 1].max)
		})
	})

	it('stops at five classes however many regions there are', () => {
		expect(bucketsFor([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]).length).toBe(5)
	})

	it('cuts where the data parts, so a long tail does not flatten the rest', () => {
		// One outlier and a tight cluster. A scale cut into equal widths would put
		// the whole cluster in one class and leave three empty; the breaks put the
		// outlier on its own and keep the cluster readable.
		const buckets = bucketsFor([5, 6, 7, 8, 1000])
		const top = buckets[buckets.length - 1]
		expect(top.min).toBeGreaterThanOrEqual(8)
		expect(top.max).toBe(1000)
		expect(buckets[0].max).toBeLessThan(1000)
	})

	it('takes one class from one region', () => {
		expect(bucketsFor([42])).toEqual([{ min: 0, max: 42 }])
	})

	it('classifies nothing when no region has a positive value', () => {
		// The regions are still drawn. They fall outside every class, which the
		// plot reads as unvalued rather than as the bottom of the scale.
		const props = propsOf({
			regions: [
				{ region: 'India', value: 0 },
				{ region: 'Japan', value: -5 },
			],
		})
		expect(props.buckets).toEqual([])
		expect(props.regions.length).toBe(2)
	})
})
