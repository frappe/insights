import { defineAsyncComponent } from 'vue'
import { toNumber, toTitleCase } from '../../helpers'
import { FIELDTYPES } from '../../helpers/constants'
import type { MapChartConfig } from '../../types/chart.types'
import type { QueryResultRow } from '../../types/query.types'
import { numberFormatter, type NumberFormatter } from '../number_format'
import type { ChartAdapterInput, ChartFiller } from './types'

const MapChart = defineAsyncComponent(() => import('../components/MapChart.vue'))

// Map is filler 2: Insights renders the plot, on v2's `useChart` and inside v2's
// chrome. What keeps it out of the library is the geography layer — a GeoJSON
// file, region names that have to be resolved against it, and a classification
// step. That is data cleaning, and it all lives here, where it can be tested
// without a browser. The component below it holds the theme, the fetch and the
// mount, and nothing else.

export type MapRegion = {
	/** As the geography spells it. This is what echarts matches a shape by. */
	name: string
	/** `null` when no row behind it holds a number: a region with nothing measured, not a zero. */
	value: number | null
}

/** One row drawn as a circle, where its coordinates say. */
export type MapPoint = {
	/** The row's location, which names the point in the tooltip and resolves a click. */
	name: string
	value: number | null
	/** Longitude then latitude, in degrees: the order echarts plots a coordinate in. */
	coord: [number, number]
	/** The circle's diameter in pixels: its area follows the value. */
	size: number
}

/**
 * One class of the natural-breaks scale. Open at `min` and closed at `max`,
 * except the lowest, which holds its own `min` — that is the smallest value
 * there is, and it belongs to the scale like every other.
 */
export type MapBucket = { min: number; max: number }

export type MapChartProps = {
	title?: string
	subtitle?: string
	map: NonNullable<MapChartConfig['map_type']>
	/** Names the measure in the tooltip. */
	measure: string
	/** Descending by value, the way the classification reads them. Empty when the style is points. */
	regions: MapRegion[]
	/** Largest first, so a small circle is drawn over a large one. Empty when the style is regions. */
	points: MapPoint[]
	/** Ascending. Empty when nothing can be classified. */
	buckets: MapBucket[]
	/** Prints every number the map shows: the tooltip, and the scale's ends. */
	format: NumberFormatter
}

const DEFAULT_MAP = 'world'
/** The diameters a circle is drawn between, in pixels: the smallest still takes a click. */
export const POINT_SIZES = { min: 6, max: 36 }

export function adaptMapChart(input: ChartAdapterInput): ChartFiller | undefined {
	const config = input.config as MapChartConfig
	if (config.map_style === 'points') return adaptMapPoints(input, config)

	// The columns the plot reads, not the ones the config names. A
	// Dimension renames its output column, so the config's spelling and the
	// result's need not match — and a drill that indexes a different column
	// from the one it plotted is a click that silently finds nothing.
	const measure = input.result.columns.find((c) => FIELDTYPES.MEASURE.includes(c.type))
	const location = input.result.columns.find((c) => FIELDTYPES.DIMENSION.includes(c.type))
	if (!measure || !location) return

	const map = config.map_type || DEFAULT_MAP
	const mappings = config.region_mappings?.[map] || {}
	const fold = foldRegions(input.result.rows, location.name, measure.name, mappings)
	const regions = regionsOf(fold)

	const props: MapChartProps = {
		title: input.title,
		subtitle: input.description,
		map,
		measure: measure.name,
		regions,
		points: [],
		buckets: naturalBreaks(regions.map((region) => region.value)),
		format: numberFormatter(config, config.value_column, input.result.rows),
	}

	return {
		component: MapChart,
		props,
		drillDown: {
			regionClick: (name: string) => {
				const row = rowForRegion(name, location.name, fold)
				return row ? { column: measure.name, row } : undefined
			},
		},
	}
}

/**
 * One circle per row, at the latitude and longitude its row holds, sized by its
 * value. A point is a row, not a region: two rows at one place are two circles,
 * and nothing is matched against the geography's names, so a point needs no
 * region mapping. A row whose coordinates are missing or off the globe is left
 * out — it has nowhere to be drawn — and so is a row with no location to name it.
 *
 * The columns are found by the names the config gives its Measures, because a
 * points map reads three of them and the result's column types cannot tell the
 * value from the coordinates.
 */
function adaptMapPoints(input: ChartAdapterInput, config: MapChartConfig): ChartFiller | undefined {
	const columns = input.result.columns
	const named = (name?: string) => (name ? columns.find((c) => c.name === name) : undefined)
	const measure = named(config.value_column?.measure_name)
	const latitude = named(config.latitude_column?.measure_name)
	const longitude = named(config.longitude_column?.measure_name)
	const location = columns.find((c) => FIELDTYPES.DIMENSION.includes(c.type))
	if (!measure || !latitude || !longitude || !location) return

	const placed: {
		name: string
		value: number | null
		coord: [number, number]
		row: QueryResultRow
	}[] = []
	for (const row of input.result.rows) {
		const raw = row[location.name]
		const lat = toNumber(row[latitude.name])
		const lon = toNumber(row[longitude.name])
		if (raw === null || raw === undefined || raw === '') continue
		if (lat === null || lon === null || Math.abs(lat) > 90 || Math.abs(lon) > 180) continue
		placed.push({
			name: String(raw),
			value: toNumber(row[measure.name]),
			coord: [lon, lat],
			row,
		})
	}
	const sizes = pointSizes(placed.map((p) => p.value))
	const points: MapPoint[] = placed
		.map(({ name, value, coord }, i) => ({ name, value, coord, size: sizes[i] }))
		.sort((a, b) => b.size - a.size)

	const byName = new Map<string, QueryResultRow[]>()
	for (const { name, row } of placed) byName.set(name, [...(byName.get(name) || []), row])

	const props: MapChartProps = {
		title: input.title,
		subtitle: input.description,
		map: config.map_type || DEFAULT_MAP,
		measure: measure.name,
		regions: [],
		points,
		buckets: [],
		format: numberFormatter(config, config.value_column, input.result.rows),
	}

	return {
		component: MapChart,
		props,
		drillDown: {
			regionClick: (name: string) => {
				const rows = byName.get(name)
				if (!rows) return undefined
				const row =
					rows.length === 1
						? rows[0]
						: { ...rows[0], [location.name]: rows.map((r) => r[location.name]) }
				return { column: measure.name, row }
			},
		},
	}
}

/**
 * Each circle's diameter, scaled so its area follows its value — a circle twice
 * the value covers twice the ground, which a reader compares by eye. Scaled to
 * the largest magnitude, so a loss draws a circle as large as a profit of the
 * same size. A row with no number, or a zero, takes the smallest circle: it is
 * still a place the query returned.
 */
export function pointSizes(values: (number | null)[]): number[] {
	const largest = Math.max(0, ...values.map((v) => (v === null || isNaN(v) ? 0 : Math.abs(v))))
	return values.map((v) => {
		if (!largest || v === null || isNaN(v)) return POINT_SIZES.min
		const share = Math.sqrt(Math.abs(v) / largest)
		return POINT_SIZES.min + share * (POINT_SIZES.max - POINT_SIZES.min)
	})
}

/** A region the geography can plot, its total, and every row behind it. */
type RegionFold = {
	/** As the geography spells it. This is what echarts matches a shape by. */
	name: string
	value: number | null
	rows: QueryResultRow[]
}

/**
 * One entry per region the geography can plot, with the rows behind it summed.
 * A region mapping is the author's answer to a name the geography does not
 * include — the gallery's data says `Brasil` where the GeoJSON says `Brazil` —
 * and it wins over the automatic title-casing.
 *
 * The one fold. What the plot shows and what a click resolves to are the same
 * grouping asked twice: an index built alongside it kept the last row of each
 * region, so a click on a region summed from several drilled into one of them.
 *
 * Keyed by the title-cased name, because a GeoJSON name is cased however its
 * author cased it.
 */
function foldRegions(
	rows: QueryResultRow[],
	location: string,
	measure: string,
	mappings: Record<string, string>,
): Map<string, RegionFold> {
	const fold = new Map<string, RegionFold>()
	for (const row of rows) {
		const raw = row[location]
		if (raw === null || raw === undefined || raw === '') continue
		const name = mappings[raw as string] || toTitleCase(String(raw))
		const region = fold.get(toTitleCase(name)) || { name, value: null, rows: [] }
		const value = toNumber(row[measure])
		if (value !== null) region.value = (region.value ?? 0) + value
		region.rows.push(row)
		fold.set(toTitleCase(name), region)
	}
	return fold
}

/** What the plot shows, descending by value, the way the classification reads them. */
function regionsOf(fold: Map<string, RegionFold>): MapRegion[] {
	return [...fold.values()]
		.sort((a, b) => Number(a.value === null) - Number(b.value === null) || b.value! - a.value!)
		.map(({ name, value }) => ({ name, value }))
}

/**
 * The row a click on a region drills into.
 *
 * A region the geography plots as one shape can be several rows — two spellings
 * of one name, or a mapping that folds them. The drill pins the clicked region,
 * so it is handed every location value behind the shape rather than one of
 * them, and the filter it builds is an `in` over the set.
 */
function rowForRegion(
	name: string,
	location: string,
	fold: Map<string, RegionFold>,
): QueryResultRow | undefined {
	const region = fold.get(toTitleCase(name))
	if (!region) return undefined
	if (region.rows.length === 1) return region.rows[0]
	return { ...region.rows[0], [location]: region.rows.map((row) => row[location]) }
}

/**
 * Jenks natural breaks over the distinct values, capped at five classes: the
 * class boundaries sit where the data already parts, so a choropleth of a long
 * tail does not collapse into one shade.
 *
 * Every number is classified, a loss as much as a profit: a region shown in the
 * "no row here" shade is one the query returned nothing for, and a reader who
 * cannot tell that from a negative reads the map wrong. The scale opens at the
 * smallest value, so the classes span exactly what the data does.
 */
function naturalBreaks(values: (number | null)[]): MapBucket[] {
	const valid = values.filter((v): v is number => typeof v === 'number' && !isNaN(v))
	if (!valid.length) return []

	const distinct = [...new Set(valid)].sort((a, b) => a - b)
	// One class, standing for the one value every region shares.
	if (distinct.length === 1) return [{ min: distinct[0], max: distinct[0] }]

	const breaks = jenks(distinct, Math.min(5, distinct.length))

	const buckets: MapBucket[] = []
	for (let i = 0; i < breaks.length - 1; i++) {
		buckets.push({ min: breaks[i], max: breaks[i + 1] })
	}
	return buckets
}

function jenks(data: number[], nClasses: number) {
	data = data.slice().sort((a, b) => a - b)
	const { mat1, mat2 } = jenksMatrices(data, nClasses)

	jenksBreaks(data, nClasses, mat1, mat2)

	const kClass = Array(nClasses + 1).fill(0)
	kClass[nClasses] = data[data.length - 1]
	let k = data.length,
		countNum = nClasses
	while (countNum >= 2) {
		const idx = mat1[k][countNum] - 2
		kClass[countNum - 1] = data[idx]
		k = mat1[k][countNum] - 1
		countNum--
	}
	kClass[0] = data[0]
	return kClass
}

function jenksMatrices(data: number[], nClasses: number) {
	const mat1 = Array.from({ length: data.length + 1 }, () => Array(nClasses + 1).fill(0))
	const mat2 = Array.from({ length: data.length + 1 }, () => Array(nClasses + 1).fill(0))

	for (let i = 1; i <= nClasses; i++) {
		mat1[1][i] = 1
		mat2[1][i] = 0
		for (let j = 2; j <= data.length; j++) mat2[j][i] = Infinity
	}
	return { mat1, mat2 }
}

function jenksBreaks(data: number[], nClasses: number, mat1: number[][], mat2: number[][]) {
	for (let l = 2; l <= data.length; l++) {
		let s1 = 0,
			s2 = 0,
			w = 0
		for (let m = 1; m <= l; m++) {
			const i3 = l - m + 1
			const val = data[i3 - 1]
			s2 += val * val
			s1 += val
			w++
			const v = s2 - (s1 * s1) / w
			const i4 = i3 - 1
			if (i4 !== 0) {
				for (let j = 2; j <= nClasses; j++) {
					if (mat2[l][j] >= v + mat2[i4][j - 1]) {
						mat1[l][j] = i3
						mat2[l][j] = v + mat2[i4][j - 1]
					}
				}
			}
		}

		mat1[l][1] = 1
		mat2[l][1] = s2 - (s1 * s1) / w
	}
}
