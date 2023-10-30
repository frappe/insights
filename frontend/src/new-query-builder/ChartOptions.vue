<script setup>
import widgets from '@/widgets/widgets'
import { inject } from 'vue'

const query = inject('query')
const builder = inject('builder')
const chartOptions = [{ label: 'Select a chart type', value: undefined }].concat(
	widgets.getChartOptions()
)
function resetOptions() {
	builder.chart.chartDoc.options = {}
}
</script>

<template>
	<div class="flex flex-col space-y-4 overflow-y-scroll pr-4">
		<!-- Widget Options -->
		<Input
			type="select"
			label="Chart Type"
			class="w-full"
			v-model="builder.chart.chartDoc.chart_type"
			:options="chartOptions"
			@update:modelValue="builder.chart.chartDoc.options = {}"
		/>

		<component
			v-if="builder.chart.chartDoc.chart_type"
			:is="widgets.getOptionComponent(builder.chart.chartDoc.chart_type)"
			:key="builder.chart.chartDoc.chart_type"
			v-model="builder.chart.chartDoc.options"
			:columns="query.resultColumns"
		/>

		<Button variant="subtle" @click="resetOptions"> Reset Options </Button>
	</div>
</template>
