<script setup>
import widgets from '@/widgets/widgets'
import { inject } from 'vue'

const props = defineProps({ onClose: Function })
const chart = inject('chart')
const chartOptions = [
	{
		label: 'Select a chart type',
		value: undefined,
	},
].concat(widgets.getChartOptions())
</script>

<template>
	<div class="flex h-full w-full flex-col p-3">
		<div class="relative flex flex-shrink-0 justify-between pb-3 text-base">
			<span class="font-code text-sm uppercase text-gray-600"> Options </span>
			<FeatherIcon
				name="x"
				class="h-4 w-4 cursor-pointer text-gray-500 transition-all hover:text-gray-800"
				@click.prevent.stop="onClose && onClose()"
			></FeatherIcon>
		</div>
		<div
			v-if="chart?.doc.chart_type"
			class="flex w-full flex-1 flex-col gap-4 overflow-y-auto pt-0 !text-base"
		>
			<!-- Widget Options -->
			<Input
				type="select"
				label="Chart Type"
				class="w-full"
				v-model="chart.doc.chart_type"
				:options="chartOptions"
			/>

			<component
				v-if="chart.doc.chart_type"
				:is="widgets.getOptionComponent(chart.doc.chart_type)"
				:key="chart.doc.chart_type"
				v-model="chart.doc.options"
				:columns="chart.columns"
			/>
		</div>
	</div>
</template>
