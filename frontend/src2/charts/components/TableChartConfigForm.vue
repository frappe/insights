<script setup lang="ts">
import { XIcon } from 'lucide-vue-next'
import { TableChartConfig } from '../../types/chart.types'
import { DimensionOption, MeasureOption } from './ChartConfigForm.vue'
import CollapsibleSection from './CollapsibleSection.vue'
import { watchEffect } from 'vue'
import DimensionPicker from './DimensionPicker.vue'
import MeasurePicker from './MeasurePicker.vue'

const props = defineProps<{
	dimensions: DimensionOption[]
	measures: MeasureOption[]
}>()

const config = defineModel<TableChartConfig>({
	required: true,
	default: () => ({
		rows: [],
		columns: [],
		values: [],
	}),
})
watchEffect(() => {
	if (!config.value.rows?.length) {
		config.value.rows = [{} as any]
	}
	if (!config.value.columns?.length) {
		config.value.columns = [{} as any]
	}
	if (!config.value.values?.length) {
		config.value.values = [{} as any]
	}
})
</script>

<template>
	<CollapsibleSection title="Rows">
		<DimensionPicker v-model="config.rows" :options="props.dimensions" />
	</CollapsibleSection>
	<CollapsibleSection title="Columns">
		<DimensionPicker v-model="config.columns" :options="props.dimensions" />
	</CollapsibleSection>
	<CollapsibleSection title="Values">
		<div class="flex flex-col gap-3">
			<MeasurePicker v-model="config.values" :options="props.measures" />
			<Checkbox label="Show Filters" v-model="config.show_filter_row" />
			<Checkbox label="Show Row Totals" v-model="config.show_row_totals" />
			<Checkbox label="Show Column Totals" v-model="config.show_column_totals" />
			<!-- <Checkbox label="Conditional Formatting" v-model="config.conditional_formatting" /> -->
		</div>
	</CollapsibleSection>
</template>
