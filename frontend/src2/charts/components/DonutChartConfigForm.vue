<script setup lang="ts">
import { FIELDTYPES } from '@/utils'
import { computed } from 'vue'
import InlineFormControlLabel from '../../components/InlineFormControlLabel.vue'
import { DountChartConfig } from '../../types/chart.types'
import { Dimension, Measure } from '../../types/query.types'

const props = defineProps<{
	dimensions: Dimension[]
	measures: Measure[]
}>()

const config = defineModel<DountChartConfig>({
	required: true,
	default: () => ({
		label_column: {},
		value_column: {},
	}),
})

const discrete_dimensions = computed(() =>
	props.dimensions
		.filter((d) => FIELDTYPES.DISCRETE.includes(d.data_type))
		.map((dimension) => ({
			...dimension,
			label: dimension.column_name,
			value: dimension.column_name,
		}))
)
const measures = computed(() =>
	props.measures.map((measure) => ({
		...measure,
		label: measure.column_name,
		value: measure.column_name,
	}))
)
</script>

<template>
	<InlineFormControlLabel label="Label">
		<Autocomplete
			:showFooter="true"
			:options="discrete_dimensions"
			:modelValue="config.label_column?.column_name"
			@update:modelValue="config.label_column = $event"
		/>
	</InlineFormControlLabel>
	<InlineFormControlLabel label="Value">
		<Autocomplete
			:showFooter="true"
			:options="measures"
			:modelValue="config.value_column?.column_name"
			@update:modelValue="config.value_column = $event"
		/>
	</InlineFormControlLabel>
</template>
