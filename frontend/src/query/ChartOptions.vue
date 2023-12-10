<script setup>
import widgets from '@/widgets/widgets'
import { inject } from 'vue'

const query = inject('query')
const chartOptions = [{ label: 'Select a chart type', value: undefined, disabled: true }].concat(
	widgets.getChartOptions()
)
function resetOptions() {
	query.chart.doc.options = {}
}
</script>

<template>
	<div class="flex h-full flex-col space-y-4 overflow-y-scroll pr-4">
		<!-- Widget Options -->
		<FormControl
			type="select"
			label="Chart Type"
			class="w-full"
			v-model="query.chart.doc.chart_type"
			:options="chartOptions"
			@update:modelValue="query.chart.doc.options = {}"
		/>

		<component
			v-if="query.chart.doc.chart_type"
			:is="widgets.getOptionComponent(query.chart.doc.chart_type)"
			:key="query.chart.doc.chart_type"
			v-model="query.chart.doc.options"
			:columns="query.resultColumns"
		/>

		<Button variant="subtle" @click="resetOptions"> Reset Options </Button>
	</div>
</template>
