<script setup>
import widgets from '@/widgets/widgets'
import { inject } from 'vue'

const query = inject('query')
const builder = inject('builder')
const chartOptions = [{ label: 'Select a chart type', value: undefined }].concat(
	widgets.getChartOptions()
)
function resetOptions() {
	builder.chart.doc.options = {}
}
</script>

<template>
	<div class="flex h-full flex-col space-y-4 overflow-y-scroll pr-4">
		<!-- Widget Options -->
		<Input
			type="select"
			label="Chart Type"
			class="w-full"
			v-model="builder.chart.doc.chart_type"
			:options="chartOptions"
			@update:modelValue="builder.chart.doc.options = {}"
		/>

		<component
			v-if="builder.chart.doc.chart_type"
			:is="widgets.getOptionComponent(builder.chart.doc.chart_type)"
			:key="builder.chart.doc.chart_type"
			v-model="builder.chart.doc.options"
			:columns="query.resultColumns"
		/>

		<Button variant="subtle" @click="resetOptions"> Reset Options </Button>
	</div>
</template>
