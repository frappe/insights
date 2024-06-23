<script setup lang="ts">
import { computed } from 'vue'
import InlineFormControlLabel from '../../components/InlineFormControlLabel.vue'
import { TableChartConfig } from '../../types/chart.types'
import { Dimension, Measure } from '../../types/query.types'

const props = defineProps<{
	dimensions: Dimension[]
	measures: Measure[]
}>()

const config = defineModel<TableChartConfig>({
	required: true,
	default: () => ({
		rows: [],
		columns: [],
		values: [],
	}),
})

const dimensions = computed(() =>
	props.dimensions.map((dimension) => ({
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
	<InlineFormControlLabel label="Rows">
		<Autocomplete
			:multiple="true"
			:options="dimensions"
			:modelValue="config.rows"
			@update:modelValue="config.rows = $event?.map((v: any) => v.value)"
		/>
	</InlineFormControlLabel>
	<InlineFormControlLabel label="Columns">
		<Autocomplete
			:multiple="true"
			:options="dimensions"
			:modelValue="config.columns"
			@update:modelValue="config.columns = $event?.map((v: any) => v.value)"
		/>
	</InlineFormControlLabel>
	<InlineFormControlLabel label="Values">
		<Autocomplete
			:multiple="true"
			:options="measures"
			:modelValue="config.values"
			@update:modelValue="config.values = $event?.map((v: any) => v.value)"
		/>
	</InlineFormControlLabel>
</template>
