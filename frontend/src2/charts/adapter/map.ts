import { toTitleCase } from '../../helpers'
import { FIELDTYPES } from '../../helpers/constants'
import type { MapChartConfig } from '../../types/chart.types'
import type { QueryResultRow } from '../../types/query.types'
import MapChart from '../components/MapChart.vue'
import { numberFormatter, type NumberFormatter } from '../number_format'
import type { ChartAdapterInput, ChartFiller } from './types'

// Map is filler 2: Insights draws the plot, on v2's `useChart` and inside v2's
// chrome. What keeps it out of the library is the geography layer — a GeoJSON
// file, region names that have to be resolved against it, and a classification
// step. That is data cleaning, and it all lives here, where it can be tested
// without a browser. The component below it holds the theme, the fetch and the
// mount, and nothing else.

export type MapRegion = {
	/** As the geography spells it. This is what echarts matches a shape by. */
	name: string
	value: number
}

/**
 * One class of the natural-breaks scale. Open at `min` and closed at `max`,
 * except the lowest, which holds its own `min` — that is the smallest value
 * there is, and it belongs to the scale like every other.
 */
export type MapBucket = { min: number; max: number }

export type MapChartProps = {
	title?: string
	map: NonNullable<MapChartConfig['map_type']>
	/** Names the measure in the tooltip. */
	measure: string
	/** Descending by value, the way the classification reads them. */
	regions: MapRegion[]
	/** Ascending. Empty when nothing can be classified. */
	buckets: MapBucket[]
	/** Prints every number the map shows: the tooltip, and the scale's ends. */
	format: NumberFormatter
}

const DEFAULT_MAP = 'world'

export function adaptMapChart(input: ChartAdapterInput): ChartFiller | undefined {
	const config = input.config as MapChartConfig

	// The columns the plot is drawn from, not the ones the config names. A
	// Dimension renames its output column, so the config's spelling and the
	// result's need not match — and a drill that indexes a different column
	// from the one it drew is a click that silently finds nothing.
	const measure = input.result.columns.find((c) => FIELDTYPES.MEASURE.includes(c.type))
	const location = input.result.columns.find((c) => FIELDTYPES.DIMENSION.includes(c.type))
	if (!measure || !location) return

	const map = config.map_type || DEFAULT_MAP
	const mappings = config.region_mappings?.[map] || {}
	const fold = foldRegions(input.result.rows, location.name, measure.name, mappings)
	const regions = regionsOf(fold)

	const props: MapChartProps = {
		title: input.title,
		map,
		measure: measure.name,
		regions,
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

/** A region the geography can draw, its total, and every row that fed it. */
type RegionFold = {
	/** As the geography spells it. This is what echarts matches a shape by. */
	name: string
	value: number
	rows: QueryResultRow[]
}

/**
 * One entry per region the geography can draw, with the rows behind it summed.
 * A region mapping is the author's answer to a name the geography does not
 * carry — the gallery's data says `Brasil` where the GeoJSON says `Brazil` —
 * and it wins over the automatic title-casing.
 *
 * The one fold. What the plot draws and what a click resolves to are the same
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
		const region = fold.get(toTitleCase(name)) || { name, value: 0, rows: [] }
		region.value += Number(row[measure]) || 0
		region.rows.push(row)
		fold.set(toTitleCase(name), region)
	}
	return fold
}

/** What the plot draws, descending by value, the way the classification reads them. */
function regionsOf(fold: Map<string, RegionFold>): MapRegion[] {
	return [...fold.values()]
		.sort((a, b) => b.value - a.value)
		.map(({ name, value }) => ({ name, value }))
}

/**
 * The row a click on a region drills into.
 *
 * A region the geography draws as one shape can be several rows — two spellings
 * of one name, or a mapping that folds them. The drill pins the clicked region,
 * so it is handed every location value that fed the shape rather than one of
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
 * Every number is classified, a loss as much as a profit: a region drawn in the
 * "no row here" shade is one the query returned nothing for, and a reader who
 * cannot tell that from a negative reads the map wrong. The scale opens at the
 * smallest value, so the classes span exactly what the data does.
 */
function naturalBreaks(values: number[]): MapBucket[] {
	const valid = values.filter((v) => typeof v === 'number' && !isNaN(v))
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
