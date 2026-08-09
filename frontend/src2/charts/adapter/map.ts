import { toTitleCase } from '../../helpers'
import { FIELDTYPES } from '../../helpers/constants'
import type { MapChartConfig } from '../../types/chart.types'
import type { QueryResultRow } from '../../types/query.types'
import MapChart from '../components/MapChart.vue'
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

/** One class of the natural-breaks scale. Open at `min`, closed at `max`. */
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
}

const DEFAULT_MAP = 'world'

export function adaptMapChart(input: ChartAdapterInput): ChartFiller | undefined {
	const config = input.config as MapChartConfig

	// The columns the plot is drawn from, not the ones the config names. A
	// Dimension renames its output column, so the config's spelling and the
	// result's need not match — and a drill-down that indexes a different column
	// from the one it drew is a click that silently finds nothing.
	const measure = input.result.columns.find((c) => FIELDTYPES.MEASURE.includes(c.type))
	const location = input.result.columns.find((c) => FIELDTYPES.DIMENSION.includes(c.type))
	if (!measure || !location) return

	const map = config.map_type || DEFAULT_MAP
	const mappings = config.region_mappings?.[map] || {}
	const regions = regionsOf(input.result.rows, location.name, measure.name, mappings)

	const props: MapChartProps = {
		title: input.title,
		map,
		measure: measure.name,
		regions,
		buckets: naturalBreaks(regions.map((region) => region.value)),
	}

	const index = regionIndex(input.result.rows, location.name, mappings)
	return {
		component: MapChart,
		props,
		drillDown: {
			regionClick: (name: string) => {
				const row = rowForRegion(name, index)
				return row ? { column: measure.name, row } : undefined
			},
		},
	}
}

/**
 * One entry per region the geography can draw, with the rows behind it summed.
 * A region mapping is the author's answer to a name the geography does not
 * carry — the gallery's data says `Brasil` where the GeoJSON says `Brazil` —
 * and it wins over the automatic title-casing.
 */
function regionsOf(
	rows: QueryResultRow[],
	location: string,
	measure: string,
	mappings: Record<string, string>,
): MapRegion[] {
	const totals = new Map<string, number>()
	for (const row of rows) {
		const raw = row[location]
		if (raw === null || raw === undefined || raw === '') continue
		const name = mappings[raw as string] || toTitleCase(String(raw))
		totals.set(name, (totals.get(name) || 0) + (Number(row[measure]) || 0))
	}
	return [...totals.entries()]
		.sort((a, b) => b[1] - a[1])
		.map(([name, value]) => ({ name, value }))
}

/**
 * The rows a clicked region can resolve to, under every spelling that region
 * reaches the plot by. Title case is the one form both sides are folded into,
 * because a GeoJSON name is cased however its author cased it.
 */
type RegionIndex = {
	/** Title-cased region name to the row behind it. */
	rows: Map<string, QueryResultRow>
	/** Title-cased mapped region back to the value the data spells it with. */
	sources: Map<string, string>
}

function regionIndex(
	rows: QueryResultRow[],
	location: string,
	mappings: Record<string, string>,
): RegionIndex {
	const index: RegionIndex = { rows: new Map(), sources: new Map() }

	for (const [source, region] of Object.entries(mappings)) {
		index.sources.set(toTitleCase(region), source)
	}

	for (const row of rows) {
		const raw = row[location]?.toString()
		if (!raw) continue
		index.rows.set(toTitleCase(raw), row)
		// The same row under the name the author mapped it to, so a click on the
		// geography's spelling lands without a second lookup.
		const mapped = mappings[raw]
		if (mapped) index.rows.set(toTitleCase(mapped), row)
	}

	return index
}

function rowForRegion(name: string, index: RegionIndex): QueryResultRow | undefined {
	const key = toTitleCase(name)
	const direct = index.rows.get(key)
	if (direct) return direct
	const source = index.sources.get(key)
	return source ? index.rows.get(toTitleCase(source)) : undefined
}

/**
 * Jenks natural breaks over the distinct values, capped at five classes: the
 * class boundaries sit where the data already parts, so a choropleth of a long
 * tail does not collapse into one shade.
 *
 * Only positive values are classified. A zero or a negative leaves its region
 * outside every class, drawn as unvalued rather than as the palest shade.
 */
function naturalBreaks(values: number[]): MapBucket[] {
	const valid = values.filter((v) => typeof v === 'number' && !isNaN(v) && v > 0)
	if (!valid.length) return []
	if (valid.length === 1) return [{ min: 0, max: valid[0] }]

	const distinct = [...new Set(valid)].sort((a, b) => a - b)
	const breaks = jenks(distinct, Math.min(5, distinct.length))

	const buckets: MapBucket[] = []
	for (let i = 0; i < breaks.length - 1; i++) {
		// The lowest class opens at zero rather than at the smallest value, so the
		// smallest value itself falls inside it.
		buckets.push({ min: i === 0 ? 0 : breaks[i], max: breaks[i + 1] })
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
