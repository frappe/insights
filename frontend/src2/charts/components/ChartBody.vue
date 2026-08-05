<script setup lang="ts">
import { Button } from 'frappe-ui'
import { RefreshCcw } from 'lucide-vue-next'
import { computed } from 'vue'
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
import { Chart } from '../chart'
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
import NumberChart from './NumberChart.vue'
import TableChart from './TableChart.vue'

// The chart itself: the type it is, the data it has, and the states in between.
// Segment clicks are reported, never handled — drill-down is a dialog the caller
// offers, so it is the caller that carries it.
const props = defineProps<{ chart: Chart }>()
const emit = defineEmits<{ drillDown: [query: Query] }>()

const chart_type = computed(() => props.chart.doc.chart_type)
const config = computed(() => props.chart.doc.config)
const result = computed(() => props.chart.dataQuery.result || { ...EMPTY_RESULT })
const loading = computed(
	() =>
		!props.chart.isloaded || !props.chart.dataQuery.isloaded || props.chart.dataQuery.executing,
)

const eChartOptions = computed(() => {
	// the result outlives a chart type switch, so without this the option builders
	// would run against the incoming type's still-empty config
	if (!props.chart.isConfigValid) return
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

	return props.chart.dataQuery.getDrillDownQuery(locationColumn.value, matchedRow)
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

	return column ? props.chart.dataQuery.getDrillDownQuery(column, row) : null
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
	const query = await props.chart.dataQuery.getDrillDownQuery(column, row)
	if (query) emit('drillDown', query)
}
</script>

<template>
	<div class="h-full w-full">
		<BaseChart
			v-if="!loading && eChartOptions"
			class="rounded bg-surface-base py-1 border border-outline-gray-2"
			:class="props.chart.doc.chart_type == 'Map' ? '[&>div:last-child]:p-4' : ''"
			:title="props.chart.doc.title"
			:options="eChartOptions"
			:onClick="onChartElementClick"
		/>
		<NumberChart
			v-else-if="!loading && chart_type == 'Number'"
			:config="config as NumberChartConfig"
			:result="result"
			@drill-down="onNumberChartDrillDown"
		/>
		<TableChart
			v-else-if="chart_type == 'Table'"
			:chart="props.chart"
			@drill-down="emit('drillDown', $event)"
		/>

		<div
			v-else
			class="flex h-full flex-1 flex-col items-center justify-center rounded border border-outline-gray-2"
		>
			<template v-if="loading">
				<LoadingIndicator class="h-5 w-5 text-ink-gray-4" />
				<p class="mt-1.5 text-ink-gray-4">Loading data...</p>
			</template>
			<template v-else-if="chart.dataQuery.isServerBusy">
				<Button
					variant="outline"
					@click="chart.refresh(true)"
					label="Server is busy, click to retry"
				>
					<template #prefix>
						<RefreshCcw class="h-4 w-4 text-ink-gray-6" stroke-width="1.5" />
					</template>
				</Button>
			</template>
			<template v-else>
				<ChartSectionEmptySvg></ChartSectionEmptySvg>
				<p class="text-ink-gray-4">
					Pick a chart type and configure options to see the chart here
				</p>
			</template>
		</div>
	</div>
</template>
