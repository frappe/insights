<template>
	<div class="flex flex-1 overflow-scroll p-2 pt-3">
		<div class="flex w-full flex-shrink-0 flex-col lg:h-full lg:w-[18rem] lg:pr-4">
			<div class="space-y-4">
				<!-- Widget Options -->
				<Input
					type="select"
					label="Chart Type"
					class="w-full"
					v-model="chart.chart_type"
					:options="chartOptions"
				/>

				<component
					v-if="chart.chart_type"
					:is="widgets.getOptionComponent(chart.chart_type)"
					:key="chart.chart_type"
					v-model="chart.options"
				/>
			</div>
		</div>

		<div
			class="relative flex h-full min-h-[30rem] w-full flex-1 flex-col space-y-3 overflow-hidden lg:w-auto"
		>
			<component
				v-if="chart.chart_type"
				ref="widget"
				:is="widgets.getComponent(chart.chart_type)"
				:chartData="chartData"
				:options="chart.options"
				:key="JSON.stringify(chart.options)"
			>
				<template #placeholder>
					<InvalidWidget
						class="absolute"
						title="Insufficient options"
						message="Please check the options for this chart"
						icon="settings"
						icon-class="text-gray-400"
					/>
				</template>
			</component>
		</div>
	</div>
</template>

<script setup>
import InvalidWidget from '@/widgets/InvalidWidget.vue'
import useChartData from '@/widgets/useChartData'
import widgets from '@/widgets/widgets'
import { inject, reactive } from 'vue'

const query = inject('query')
const chartData = useChartData()
chartData.load(query.name)
const chart = reactive({
	chart_type: undefined,
	options: {
		query: query.name,
	},
})
const chartOptions = [
	{
		label: 'Select a chart type',
		value: undefined,
	},
].concat(widgets.getChartOptions())
</script>
