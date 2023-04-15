<script setup>
import widgets from '@/widgets/widgets'
import { inject } from 'vue'

const query = inject('query')
const chartOptions = [
	{
		label: 'Select a chart type',
		value: undefined,
	},
].concat(widgets.getChartOptions())
</script>

<template>
	<div class="flex h-full w-full flex-col p-3">
		<div class="flex flex-shrink-0 justify-between pb-3 text-base">
			<span class="font-code uppercase text-gray-500"> Options </span>
		</div>
		<div
			v-if="query.chart.doc"
			class="flex w-full flex-1 flex-col gap-4 overflow-y-scroll pt-0 !text-base"
		>
			<!-- Widget Options -->
			<Input
				type="select"
				label="Chart Type"
				class="w-full"
				v-model="query.chart.doc.chart_type"
				:options="chartOptions"
			/>

			<component
				v-if="query.chart.doc.chart_type"
				:is="widgets.getOptionComponent(query.chart.doc.chart_type)"
				:key="query.chart.doc.chart_type"
				v-model="query.chart.doc.options"
				:columns="query.resultColumns"
			/>
		</div>
	</div>
</template>
