import { use } from 'echarts/core'
import { registerChartModules } from 'frappe-ui/charts'
import { describe, expect, it } from 'vitest'
import { adaptChart } from './index'
import { mapChart, type MapChartSpec } from './fixtures'

// Everything here asserts on the props the plot is handed, and on the point a
// click resolves to. How the plot draws them is the component's concern.

function adapt(spec: MapChartSpec) {
	const filler = adaptChart(mapChart(spec))
	if (!filler) throw new Error('the adapter drew nothing for this Chart')
	return filler
}

const propsOf = (spec: MapChartSpec) => adapt(spec).props

// @feature charts.type-map
it('registers its series into the same echarts the chart mounts through', () => {
	// Map is the one chart type Insights registers an echarts module for, and
	// echarts keeps that registry in module state. frappe-ui is linked from the
	// framework checkout and carries an echarts of its own, so without the
	// resolver deduping the package the series would be registered into a copy
	// no chart instance reads — and the map would draw a blank plot with no
	// error. The build config is the fix. This is the guard on it.
	expect(registerChartModules).toBe(use)
})

describe('the geography', () => {
	// @feature charts.type-map
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

	// @feature charts.map-type
	it('draws the India map when the Chart asks for it', () => {
		expect(propsOf({ mapType: 'india', regions: [{ region: 'Goa', value: 1 }] }).map).toBe(
			'india',
		)
	})

	// @feature charts.type-map
	it('draws nothing without both a region column and a measure', () => {
		const input = mapChart({ regions: [{ region: 'India', value: 30 }] })
		input.result.columns = input.result.columns.filter((c) => c.name !== 'revenue')
		expect(adaptChart(input)).toBeUndefined()
	})

	// @feature charts.type-map
	it('reads the biggest region first', () => {
		const props = propsOf({
			regions: [
				{ region: 'Japan', value: 20 },
				{ region: 'India', value: 30 },
			],
		})
		expect(props.regions.map((region: any) => region.name)).toEqual(['India', 'Japan'])
	})

	// @feature charts.type-map
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

	// @feature charts.type-map
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

	// @feature charts.map-region-mapping
	it('draws a mapped region under the name the geography carries', () => {
		expect(propsOf(gallery).regions).toEqual([
			{ name: 'United States of America', value: 500 },
			{ name: 'Brazil', value: 300 },
			{ name: 'India', value: 100 },
		])
	})

	// @feature charts.map-region-mapping
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

	// @feature charts.map-region-mapping
	it('resolves a click on an unmapped region by its own name', () => {
		const input = mapChart(gallery)
		expect(adaptChart(input)!.drillDown!.regionClick('India')).toEqual({
			column: 'revenue',
			row: input.result.rows[2],
		})
	})

	// @feature charts.map-region-mapping
	it('resolves a click whatever case the geography spells it in', () => {
		const input = mapChart({ regions: [{ region: 'india', value: 30 }] })
		expect(adaptChart(input)!.drillDown!.regionClick('INDIA')).toEqual({
			column: 'revenue',
			row: input.result.rows[0],
		})
	})

	// @feature charts.map-region-mapping
	it('drills into every row a folded region was summed from', () => {
		// Two spellings the mapping folds into one shape. The click stands for the
		// shape, so it carries both spellings and not the last row that fed it.
		const input = mapChart({
			regions: [
				{ region: 'Brasil', value: 300 },
				{ region: 'brazil', value: 200 },
			],
			regionMappings: { Brasil: 'Brazil', brazil: 'Brazil' },
		})
		expect(adaptChart(input)!.props.regions).toEqual([{ name: 'Brazil', value: 500 }])
		expect(adaptChart(input)!.drillDown!.regionClick('Brazil')).toEqual({
			column: 'revenue',
			row: { ...input.result.rows[0], country: ['Brasil', 'brazil'] },
		})
	})

	// @feature charts.map-region-mapping
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

	// @feature charts.map-color-scale
	it('spans exactly what the data does, smallest value to largest', () => {
		const buckets = bucketsFor([5, 40, 60, 900])
		expect(buckets[0].min).toBe(5)
		expect(buckets[buckets.length - 1].max).toBe(900)
	})

	// @feature charts.map-color-scale
	it('runs low to high with no gap between one class and the next', () => {
		// A class standing for one value is as wide as that value: four regions
		// cut into four classes gives each one a class of its own.
		const buckets = bucketsFor([5, 40, 60, 900])
		buckets.forEach((bucket: any, index: number) => {
			expect(bucket.max).toBeGreaterThanOrEqual(bucket.min)
			if (index) expect(bucket.min).toBe(buckets[index - 1].max)
		})
	})

	// @feature charts.map-color-scale
	it('stops at five classes however many regions there are', () => {
		expect(bucketsFor([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]).length).toBe(5)
	})

	// @feature charts.map-color-scale
	it('cuts where the data parts, so a long tail does not flatten the rest', () => {
		// One outlier and a tight cluster. A scale cut into equal widths would put
		// the whole cluster in one class and leave three empty. The breaks put the
		// outlier on its own and keep the cluster readable.
		const buckets = bucketsFor([5, 6, 7, 8, 1000])
		const top = buckets[buckets.length - 1]
		expect(top.min).toBeGreaterThanOrEqual(8)
		expect(top.max).toBe(1000)
		expect(buckets[0].max).toBeLessThan(1000)
	})

	// @feature charts.map-color-scale
	it('takes one class from one region', () => {
		expect(bucketsFor([42])).toEqual([{ min: 42, max: 42 }])
	})

	// @feature charts.map-color-scale
	it('classifies a loss too, so it is not drawn as a region with no row', () => {
		// The unvalued shade is what a region the query returned nothing for gets.
		// A profit measure is negative wherever the business lost money, and a
		// reader who cannot tell the two apart reads the map wrong.
		const buckets = bucketsFor([-500, -20, 30, 900])
		expect(buckets[0].min).toBe(-500)
		expect(buckets[buckets.length - 1].max).toBe(900)
	})

	// @feature charts.map-color-scale
	it('classifies nothing when the query returned no region at all', () => {
		expect(bucketsFor([])).toEqual([])
	})
})
