<script setup>
import Autocomplete from '@/components/Controls/Autocomplete.vue'
import widgets from '@/widgets/widgets'
import { inject } from 'vue'

const query = inject('query')
function resetOptions() {
	query.chart.doc.options = {}
}
</script>

<template>
	<div class="flex h-full flex-col space-y-4 overflow-y-auto p-0.5">
		<div>
			<label class="mb-1.5 block text-xs text-gray-600">Chart type</label>
			<Autocomplete
				:modelValue="query.chart.doc.chart_type"
				:options="widgets.getChartOptions()"
				@update:modelValue="
					(option) => {
						query.chart.doc.chart_type = option.value
						query.chart.doc.options = {}
					}
				"
			>
				<template #prefix>
					<component
						:is="widgets.getIcon(query.chart.doc.chart_type)"
						class="mr-1.5 h-4 w-4 text-gray-600"
						stroke-width="1.5"
					/>
				</template>
				<template #item-prefix="{ option }">
					<component
						:is="widgets.getIcon(option.label)"
						class="h-4 w-4"
						stroke-width="1.5"
					/>
				</template>
			</Autocomplete>
		</div>

		<component
			v-if="query.chart.doc.chart_type"
			:is="widgets.getOptionComponent(query.chart.doc.chart_type)"
			:key="query.chart.doc.chart_type"
			v-model="query.chart.doc.options"
			:columns="query.results.columns"
		/>

		<Button variant="subtle" @click="resetOptions"> Reset Options </Button>
	</div>
</template>
