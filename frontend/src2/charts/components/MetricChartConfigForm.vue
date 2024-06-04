<script setup lang="ts">
import { FIELDTYPES } from '@/utils'
import { computed } from 'vue'
import { MetricChartConfig } from '../helpers'

const props = defineProps<{
	dimensions: Dimension[]
	measures: Measure[]
}>()

const config = defineModel<MetricChartConfig>({
	required: true,
	default: () => ({
		metric_column: '',
		date_column: '',
		target_column: '',
		target_value: undefined,
	}),
})

const date_dimensions = computed(() =>
	props.dimensions
		.filter((d) => FIELDTYPES.DATE.includes(d.data_type))
		.map((dimension) => ({
			label: dimension.column_name,
			value: dimension.column_name,
		}))
)
const measures = computed(() =>
	props.measures.map((measure) => ({
		label: measure.column_name,
		value: measure.column_name,
	}))
)
</script>

<template>
	<div class="flex flex-col gap-3 p-3">
		<Autocomplete
			label="Metric"
			:showFooter="true"
			:options="measures"
			:modelValue="config.metric_column"
			@update:modelValue="config.metric_column = $event?.value"
		/>
		<!-- <Autocomplete
			label="Date"
			:showFooter="true"
			:options="date_dimensions"
			:modelValue="config.date_column"
			@update:modelValue="config.date_column = $event?.value"
		/>
		<Autocomplete
			label="Target"
			:showFooter="true"
			:options="measures"
			:modelValue="config.target_column"
			@update:modelValue="config.target_column = $event?.value"
		/>
		<FormControl v-model="config.target_value" label="Target Value" type="number" /> -->
	</div>
</template>
