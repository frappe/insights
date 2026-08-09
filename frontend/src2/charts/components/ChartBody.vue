<script setup lang="ts">
import { Button } from 'frappe-ui'
import { AlertTriangle, RefreshCcw } from 'lucide-vue-next'
import { computed, shallowRef, watch } from 'vue'
import { __ } from '../../translation'
import { titleCase } from '../../helpers'
import { FIELDTYPES } from '../../helpers/constants.ts'
import { EMPTY_RESULT } from '../../query/helpers'
import { Query } from '../../query/query'
import {
	BarChartConfig,
	BubbleChartConfig,
	DonutChartConfig,
	FunnelChartConfig,
	LineChartConfig,
	MapChartConfig,
	NumberChartConfig,
	SankeyChartConfig,
	AXIS_CHARTS,
	AxisChartConfig,
} from '../../types/chart.types'
import { ChartRead } from '../chart_read'
import {
	getBarChartOptions,
	getBubbleChartOptions,
	getDonutChartOptions,
	getFunnelChartOptions,
	getLineChartOptions,
	getMapChartOptions,
	getSankeyChartOptions,
	getAxisChartRowOrder,
} from '../helpers'
import BaseChart from './BaseChart.vue'
import ChartSectionEmptySvg from './ChartSectionEmptySvg.vue'
import ChartTitle from './ChartTitle.vue'
import NumberChart from './NumberChart.vue'
import TableChart from './TableChart.vue'

// The chart itself: the type it is, the data it has, and every state in between.
// One card, one state machine — a surface that draws a chart card draws this,
// and gets the failure, the reload and the empty result along with the picture.
// Segment clicks are reported, never handled — drill-down is a dialog the caller
// offers, so it is the caller that carries it.
//
// `readonly` is for a surface that cannot change the chart. It decides two
// things, and they are the same thing: a table's sort rewrites the chart's config
// and re-runs its query, which a reader holds neither half of, so the control is
// not offered rather than offered and dead — and for the same reason a reader is
// told about the data ("No data") where an author is told about the config.
const props = defineProps<{
	chart: ChartRead
	readonly?: boolean
	// whether filters narrowed the rows, so an empty card can offer to clear them.
	// Only a surface that owns filter state can say, and only it can reset them.
	filtered?: boolean
}>()
const emit = defineEmits<{ drillDown: [query: Query]; resetFilters: [] }>()

const chart_type = computed(() => props.chart.doc.chart_type)
const config = computed(() => props.chart.doc.config)
const result = computed(() => props.chart.result || { ...EMPTY_RESULT })

const builtOptions = computed(() => {
	// the result outlives a chart type switch, so without this the option builders
	// would run against the incoming type's still-empty config
	if (props.chart.configErrors.length) return
	if (!result.value.columns?.length) return
	if (chart_type.value === 'Bar' || chart_type.value === 'Row') {
		return getBarChartOptions(
			config.value as BarChartConfig,
			result.value,
			chart_type.value === 'Row',
		)
	}
	if (chart_type.value === 'Line') {
		return getLineChartOptions(config.value as LineChartConfig, result.value)
	}
	if (chart_type.value === 'Donut') {
		return getDonutChartOptions(config.value as DonutChartConfig, result.value)
	}
	if (chart_type.value === 'Funnel') {
		return getFunnelChartOptions(config.value as FunnelChartConfig, result.value)
	}
	if (chart_type.value === 'Map') {
		return getMapChartOptions(config.value as MapChartConfig, result.value)
	}
	if (chart_type.value === 'Bubble') {
		return getBubbleChartOptions(config.value as BubbleChartConfig, result.value)
	}
	if (chart_type.value === 'Sankey') {
		return getSankeyChartOptions(config.value as SankeyChartConfig, result.value)
	}
})

// The store holds on to the rows when the server answers with config errors, so
// the card goes on showing what it last drew while a slot is being filled — the
// builders cannot run against a config the server refused, but their last output
// is still a true picture of those rows. A type switch is not that case: the
// picture belongs to the type that drew it.
const lastDrawn = shallowRef<{ chart_type: string; options: object }>()
watch(builtOptions, (options) => {
	if (options) lastDrawn.value = { chart_type: chart_type.value, options }
})

const eChartOptions = computed(() => {
	if (!props.chart.configErrors.length) return builtOptions.value
	return lastDrawn.value?.chart_type === chart_type.value ? lastDrawn.value.options : undefined
})

// Number and Table draw themselves straight off the result; every other type
// needs the option builders to have produced something
const drawable = computed(
	() =>
		Boolean(eChartOptions.value) ||
		chart_type.value === 'Number' ||
		chart_type.value === 'Table',
)

// A table that already has rows keeps them while the next run is in flight.
// Every other type blanks, so this is a restoration and not a rule: a table on a
// filtered dashboard would otherwise blank on every filter move, which reads as
// the card breaking rather than the card catching up. The rule the exception
// wants — every type holding its last picture while it reloads — is a bigger
// change than this one, and belongs with the one the config errors already make.
const keepsLastPicture = computed(
	() => chart_type.value === 'Table' && Boolean(result.value.rows?.length),
)

// What the card shows, in the order the store settles it: a failure outranks the
// reload that would replace it, and a reload outranks the rows it is replacing.
// `unconfigured` is the state a chart is born in — nothing has been drawn yet and
// nothing is on its way.
const state = computed(() => {
	if (props.chart.failed) return props.chart.serverBusy ? 'serverBusy' : 'failed'
	if (props.chart.executing && !keepsLastPicture.value) return 'loading'
	if (props.chart.empty) return 'empty'
	return drawable.value ? 'chart' : 'unconfigured'
})

const mapConfig = computed(() => props.chart.doc.config as MapChartConfig)

// If columns don't change we shouldn't search for this on every click
const locationColumn = computed(() => {
	return result.value.columns.find(
		(c) =>
			FIELDTYPES.DIMENSION.includes(c.type) &&
			c.name === mapConfig.value.location_column?.column_name,
	)
})

// Runs only when data changes
const locationRowIndex = computed(() => {
	const index = new Map<string, any>()
	const col = locationColumn.value

	if (!col) return { index, reverseMap: new Map<string, string>() }

	// computed mappings for faster acess
	const mappings = mapConfig.value.region_mappings?.[mapConfig.value.map_type || 'world'] || {}
	const reverseMap = new Map<string, string>()

	for (const [userValue, mappedRegion] of Object.entries(mappings)) {
		reverseMap.set(titleCase(mappedRegion as string), userValue)
	}

	// Index the rows
	result.value.formattedRows.forEach((row) => {
		const rawValue = row[col.name]?.toString()
		if (!rawValue) return

		const normalizedRowValue = titleCase(rawValue)
		//	case 1: Index by Direct Match (Auto-mapped)
		// Key: "United States" -> Row(United States)
		index.set(normalizedRowValue, row)

		//case 2: Index by config mapping
		// If this row is "usa" and config maps == "usa" -> "United States"
		// we also want the key "United States" to point to this row
		const mappedName = mappings[rawValue]
		if (mappedName) {
			index.set(titleCase(mappedName as string), row)
		}
	})

	return { index, reverseMap }
})

function handleMapChartClick(params: any) {
	if (!locationColumn.value) return null

	const clickedLocation = params.name
	const normalizedClick = titleCase(clickedLocation)

	const { index, reverseMap } = locationRowIndex.value
	// Lookup directly
	let matchedRow = index.get(normalizedClick)

	if (!matchedRow) {
		const originalUserVal = reverseMap.get(normalizedClick)
		if (originalUserVal) {
			matchedRow = index.get(titleCase(originalUserVal))
		}
	}

	if (!matchedRow) return null

	return props.chart.getDrillDownQuery(locationColumn.value, matchedRow)
}

function handleGeneralChartClick(params: any) {
	let dataIndex = params.dataIndex

	if (AXIS_CHARTS.includes(chart_type.value)) {
		const rowOrder = getAxisChartRowOrder(
			result.value.rows,
			(config.value as AxisChartConfig).x_axis,
			chart_type.value === 'Row',
		)
		dataIndex = rowOrder[dataIndex]
	}

	const row = result.value.formattedRows[dataIndex]
	const column = result.value.columns.find((c) => c.name === params.seriesName)

	return column ? props.chart.getDrillDownQuery(column, row) : null
}

async function onChartElementClick(params: any) {
	if (params.componentType !== 'series') return

	const query =
		chart_type.value === 'Map'
			? await handleMapChartClick(params)
			: await handleGeneralChartClick(params)

	if (query) emit('drillDown', query)
}

async function onNumberChartDrillDown(column: any, row: any) {
	const query = await props.chart.getDrillDownQuery(column, row)
	if (query) emit('drillDown', query)
}
</script>

<template>
	<div class="flex h-full w-full flex-col">
		<!-- the errors name slots in the config, so only a surface that can fill
		     them has any use for them. It sits above the picture rather than in
		     place of it, because the picture under it is still the last one the
		     server accepted. -->
		<div
			v-if="!props.readonly && chart.configErrors.length"
			class="flex flex-shrink-0 flex-col gap-0.5 rounded-t border border-b-0 border-outline-gray-2 bg-surface-amber-1 px-3 py-1.5"
		>
			<p v-for="error in chart.configErrors" :key="error" class="text-p-sm text-ink-amber-3">
				{{ error }}
			</p>
		</div>

		<div class="min-h-0 w-full flex-1">
			<BaseChart
				v-if="state === 'chart' && eChartOptions"
				class="rounded bg-surface-base py-1 border border-outline-gray-2"
				:class="props.chart.doc.chart_type == 'Map' ? '[&>div:last-child]:p-4' : ''"
				:title="props.chart.doc.title"
				:options="eChartOptions"
				:onClick="onChartElementClick"
			/>
			<NumberChart
				v-else-if="state === 'chart' && chart_type == 'Number'"
				:config="config as NumberChartConfig"
				:result="result"
				@drill-down="onNumberChartDrillDown"
			/>
			<TableChart
				v-else-if="state === 'chart'"
				:chart="props.chart"
				:readonly="props.readonly"
				@drill-down="emit('drillDown', $event)"
			/>

			<!-- a card still filling in is a placeholder to a reader, not a message:
			     a dashboard fills in card by card and the grid should hold its shape -->
			<div
				v-else-if="state === 'loading' && props.readonly"
				class="h-full w-full animate-pulse rounded border border-outline-gray-2 bg-surface-gray-2"
			/>

			<div
				v-else
				class="flex h-full w-full flex-col overflow-hidden rounded border border-outline-gray-2 bg-surface-base"
			>
				<ChartTitle v-if="state === 'empty' && chart.doc.title" :title="chart.doc.title" />
				<div class="flex flex-1 flex-col items-center justify-center gap-2 p-2">
					<template v-if="state === 'loading'">
						<LoadingIndicator class="h-5 w-5 text-ink-gray-4" />
						<p class="text-ink-gray-4">{{ __('Loading data...') }}</p>
					</template>

					<!-- the queue turned this card away rather than queueing it, so
					     asking again is the whole remedy -->
					<template v-else-if="state === 'serverBusy'">
						<Button
							variant="outline"
							:label="__('Server is busy, click to retry')"
							@click="chart.load(true)"
						>
							<template #prefix>
								<RefreshCcw class="h-4 w-4 text-ink-gray-6" stroke-width="1.5" />
							</template>
						</Button>
					</template>

					<template v-else-if="state === 'failed'">
						<AlertTriangle class="h-6 w-6 text-ink-gray-4" stroke-width="1" />
						<p class="text-p-base text-ink-gray-5">
							{{ __('This chart is not available') }}
						</p>
						<Button variant="outline" :label="__('Retry')" @click="chart.load(true)">
							<template #prefix>
								<RefreshCcw class="h-4 w-4 text-ink-gray-6" stroke-width="1.5" />
							</template>
						</Button>
					</template>

					<template v-else-if="state === 'empty'">
						<p class="text-p-base text-ink-gray-5">{{ __('No data') }}</p>
						<Button
							v-if="props.filtered"
							variant="outline"
							:label="__('Reset filters')"
							@click="emit('resetFilters')"
						/>
					</template>

					<template v-else>
						<ChartSectionEmptySvg></ChartSectionEmptySvg>
						<p class="text-ink-gray-4">
							{{
								__('Pick a chart type and configure options to see the chart here')
							}}
						</p>
					</template>
				</div>
			</div>
		</div>
	</div>
</template>
