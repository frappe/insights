<script setup lang="ts">
import { MapChart as MapSeries } from 'echarts/charts'
import { getMap, registerMap } from 'echarts/core'
import {
	ChartContainer,
	ChartTooltip,
	registerChartModules,
	useChart,
	useChartTokens,
} from 'frappe-ui/charts'
import type { ChartTooltipItem } from 'frappe-ui/charts'
import { computed, reactive, ref, watch } from 'vue'
import { getShortNumber } from '../../helpers'
import { __ } from '../../translation'
import type { MapChartProps } from '../adapter/map'

// The choropleth Insights draws itself. Everything around the plot is v2's, so
// a Map card on a dashboard reads as one of the family; only the geography is
// ours. The arithmetic behind it — which region a row belongs to and which
// class its value falls in — is `adapter/map.ts`, and this file holds what
// needs a DOM: the tokens, the GeoJSON, and the mount.

registerChartModules([MapSeries])

const props = defineProps<MapChartProps>()

const emit = defineEmits<{ regionClick: [name: string] }>()

const plotEl = ref<HTMLElement>()

const { tokens } = useChartTokens(plotEl)

/**
 * The GeoJSON, fetched once. `registerMap` writes into echarts' own registry,
 * which outlives every chart, so the registry is also the cache: a second Map
 * card reads the first card's geography instead of asking for the file again.
 */
async function loadGeography(name: string) {
	if (getMap(name)) return true
	try {
		const file = name === 'india' ? 'india' : 'world_map'
		registerMap(name, await (await fetch(`/assets/insights/maps/${file}.json`)).json())
		return true
	} catch (error) {
		console.error(`Could not load the ${name} map`, error)
		return false
	}
}

// Which geography echarts can already draw. The option below is withheld until
// this catches up with the one the chart asks for, which is what makes the
// order right rather than lucky: `useChart` skips an undefined option and
// re-runs the getter when this ref lands.
const registered = ref<string>()
const failed = ref(false)

watch(
	() => props.map,
	async (name) => {
		const loaded = await loadGeography(name)
		// A second geography may have been asked for while this one was in flight.
		if (props.map !== name) return
		failed.value = !loaded
		if (loaded) registered.value = name
	},
	{ immediate: true },
)

/** Pale for the lowest class, deep for the highest. */
const bucketColors = computed(() => {
	const ramp = tokens.value.sequential
	const count = props.buckets.length
	return props.buckets.map((_, index) => {
		const position = count === 1 ? 1 : index / (count - 1)
		return ramp[Math.round((1 - position) * (ramp.length - 1))]
	})
})

function colorOf(value: number) {
	const bucket = props.buckets.findIndex((b) => value > b.min && value <= b.max)
	return bucket === -1 ? tokens.value.splitLine : bucketColors.value[bucket]
}

const option = computed(() => {
	if (registered.value !== props.map) return undefined
	return {
		animation: true,
		animationDuration: 300,
		series: [
			{
				type: 'map',
				name: props.measure,
				map: props.map,
				// Web Mercator. The GeoJSON carries plain degrees, and echarts
				// plots them as-is unless it is told how to project them.
				projection: {
					project: (point: [number, number]) => [
						(point[0] / 180) * Math.PI,
						-Math.log(Math.tan((Math.PI / 2 + (point[1] / 180) * Math.PI) / 2)),
					],
					unproject: (point: [number, number]) => [
						(point[0] * 180) / Math.PI,
						((2 * 180) / Math.PI) * Math.atan(Math.exp(point[1])) - 90,
					],
				},
				data: props.regions.map((region) => ({
					name: region.name,
					value: region.value,
					itemStyle: { areaColor: colorOf(region.value) },
				})),
				itemStyle: {
					areaColor: tokens.value.splitLine,
					// Regions are parted by the surface behind the plot, the way a
					// heatmap parts its cells. A grey border reads as a second scale.
					borderColor: tokens.value.cellGap,
					borderWidth: 0.5,
				},
				// The tooltip is the feedback. A highlight fill on top of the class
				// colour would say the region changed class.
				emphasis: { disabled: true },
				selectedMode: false,
			},
		],
	}
})

const pointer = reactive({ x: 0, y: 0 })
const tooltip = reactive({
	open: false,
	x: 0,
	y: 0,
	label: undefined as string | undefined,
	items: [] as ChartTooltipItem[],
})

useChart({
	container: plotEl,
	option: () => option.value,
	events: {
		mouseover: (params: any) => showTooltip(params.name, params.value),
		mouseout: () => (tooltip.open = false),
		click: (params: any) => emit('regionClick', params.name),
	},
	onZrEvents: {
		mousemove: (e: any) => {
			pointer.x = e.event?.clientX ?? pointer.x
			pointer.y = e.event?.clientY ?? pointer.y
			if (tooltip.open) {
				tooltip.x = pointer.x
				tooltip.y = pointer.y
			}
		},
		globalout: () => (tooltip.open = false),
	},
})

function showTooltip(name: string, value: number) {
	// A region the query returned no rows for is drawn, and hovering it should
	// say nothing rather than say zero.
	if (value === undefined || value === null || isNaN(value)) {
		tooltip.open = false
		return
	}

	tooltip.label = name
	tooltip.items = [
		{
			name,
			label: props.measure,
			color: colorOf(value),
			value,
			formattedValue: getShortNumber(value, 2),
		},
	]
	tooltip.x = pointer.x
	tooltip.y = pointer.y
	tooltip.open = true
}
</script>

<template>
	<ChartContainer
		:title="props.title"
		:error="failed ? __('Could not load the map') : null"
		:empty="!props.regions.length"
	>
		<template #default>
			<div
				ref="plotEl"
				class="h-full w-full"
				role="img"
				:aria-label="props.title || props.measure"
			/>

			<ChartTooltip
				:open="tooltip.open"
				:x="tooltip.x"
				:y="tooltip.y"
				:label="tooltip.label"
				:items="tooltip.items"
			/>
		</template>

		<!-- The classes stand in for a legend. They are ranges of one measure and
		     not series, so there is nothing to switch on and off. -->
		<template #legend>
			<div
				v-if="props.buckets.length"
				class="flex flex-wrap items-center justify-center gap-x-3 gap-y-0.5"
			>
				<span
					v-for="(bucket, index) in props.buckets"
					:key="index"
					class="flex items-center gap-1.5"
				>
					<span
						class="size-2 shrink-0 rounded-1"
						:style="{ backgroundColor: bucketColors[index] }"
					/>
					<span class="text-p-xs tabular-nums text-ink-gray-5">
						{{ getShortNumber(bucket.max, 1) }}
					</span>
				</span>
			</div>
		</template>
	</ChartContainer>
</template>
