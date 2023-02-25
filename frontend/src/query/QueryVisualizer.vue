<template>
	<div
		class="flex flex-1 flex-col items-start space-y-4 overflow-scroll pt-2 scrollbar-hide lg:flex-row lg:space-y-0 lg:overflow-hidden"
	>
		<div
			class="flex w-full flex-shrink-0 flex-col overflow-hidden lg:h-full lg:w-[18rem] lg:pr-4"
		>
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
			class="flex h-full min-h-[30rem] w-full flex-1 flex-col space-y-3 overflow-hidden lg:w-auto"
		>
			<div class="flex flex-1 flex-col items-center justify-center overflow-hidden">
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
							message="Please check the options for this widget"
							icon="settings"
							icon-class="text-gray-400"
						/>
					</template>
				</component>
			</div>
		</div>
	</div>
</template>

<script setup>
import Autocomplete from '@/components/Controls/Autocomplete.vue'
import InvalidWidget from '@/widgets/InvalidWidget.vue'
import useChartData from '@/widgets/useChartData'
import widgets from '@/widgets/widgets'
import { inject, reactive } from 'vue'

const query = inject('query')
const chartData = useChartData({ query: query.name })
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
