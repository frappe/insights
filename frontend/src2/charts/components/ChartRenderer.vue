<script setup lang="ts">
import ChartSectionEmptySvg from '@/query/ChartSectionEmptySvg.vue'
import { computed, ref } from 'vue'
import { EMPTY_RESULT, Query } from '../../query/query'
import {
	BarChartConfig,
	DonutChartConfig,
	FunnelChartConfig,
	LineChartConfig,
	MapChartConfig,
	NumberChartConfig,
	BubbleChartConfig,
} from '../../types/chart.types'
import { Chart } from '../chart'
import {
	getBarChartOptions,
	getDonutChartOptions,
	getFunnelChartOptions,
	getLineChartOptions,
	getMapChartOptions,
	getBubbleChartOptions,
} from '../helpers'
import { FIELDTYPES } from '../../helpers/constants.ts'
import { titleCase } from '../../helpers'
import BaseChart from './BaseChart.vue'
import DrillDown from './DrillDown.vue'
import NumberChart from './NumberChart.vue'
import TableChart from './TableChart.vue'

const props = defineProps<{ chart: Chart }>()

const chart_type = computed(() => props.chart.doc.chart_type)
const config = computed(() => props.chart.doc.config)
const result = computed(() => props.chart.dataQuery.result || { ...EMPTY_RESULT })
const loading = computed(
	() =>
		!props.chart.isloaded || !props.chart.dataQuery.isloaded || props.chart.dataQuery.executing,
)

const eChartOptions = computed(() => {
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
})

const showDrillDown = ref(false)
const drillDownQuery = ref<Query>()

const mapConfig = computed(() => props.chart.doc.config as MapChartConfig)

// If columns don't change we shouldn't search for this on every click
const locationColumn = computed(() => {
	return result.value.columns.find(
		(c) =>
			FIELDTYPES.DIMENSION.includes(c.type) &&
			c.name === mapConfig.value.location_column?.column_name
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

function handleMapChartClick(params:any) {
	if (!locationColumn.value) return null

	const clickedLocation = params.name
	const formattedRow = result.value.formattedRows.find(
		(r) => titleCase(r[locationColumn.name]?.toString()) === titleCase(clickedLocation),
	)

	return formattedRow
		? props.chart.dataQuery.getDrillDownQuery(locationColumn, formattedRow)
		: null
}

function handleGeneralChartClick(params: any) {
	let dataIndex = params.dataIndex

	// Adjust index for Row charts (they're displayed in reverse order)
	if (chart_type.value === 'Row') {
		dataIndex = result.value.formattedRows.length - 1 - dataIndex
	}

	const row = result.value.formattedRows[dataIndex]
	const column = result.value.columns.find((c) => c.name === params.seriesName)

	return column ? props.chart.dataQuery.getDrillDownQuery(column, row) : null
}

function onChartElementClick(params: any) {
	if (params.componentType !== 'series') return

	const query =
		chart_type.value === 'Map' ? handleMapChartClick(params) : handleGeneralChartClick(params)

	if (query) {
		drillDownQuery.value = query
		showDrillDown.value = true
	}
}

function onNumberChartDrillDown(column: any, row: any) {
	drillDownQuery.value = props.chart.dataQuery.getDrillDownQuery(column, row)
	if (drillDownQuery.value) {
		showDrillDown.value = true
	}
}
</script>

<template>
	<div class="relative h-full w-full">
		<BaseChart
			v-if="!loading && eChartOptions"
			class="rounded bg-white py-1 shadow"
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
		<TableChart v-else-if="!loading && chart_type == 'Table'" :chart="props.chart" />

		<div v-else class="flex h-full flex-1 flex-col items-center justify-center rounded border">
			<template v-if="loading">
				<LoadingIndicator class="h-5 w-5 text-gray-500" />
				<p class="mt-1.5 text-gray-500">Loading data...</p>
			</template>
			<template v-else>
				<ChartSectionEmptySvg></ChartSectionEmptySvg>
				<p class="text-gray-500">
					Pick a chart type and configure options to see the chart here
				</p>
			</template>
		</div>
	</div>
	<DrillDown
		v-if="drillDownQuery"
		v-model="showDrillDown"
		@update:modelValue="!$event ? (drillDownQuery = undefined) : undefined"
		:query="drillDownQuery"
	>
	</DrillDown>
</template>
