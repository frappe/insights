<script setup lang="ts">
import Checkbox from '@/components/Controls/Checkbox.vue'
import { FIELDTYPES } from '@/utils'
import { computed } from 'vue'
import { NumberChartConfig } from '../../types/chart.types'
import { Dimension, Measure } from '../../types/query.types'

const props = defineProps<{
	dimensions: Dimension[]
	measures: Measure[]
}>()

const config = defineModel<NumberChartConfig>({
	required: true,
	default: () => ({
		number_column: '',
		comparison: false,
		sparkline: false,
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
			label="Number"
			:showFooter="true"
			:options="measures"
			:modelValue="config.number_column"
			@update:modelValue="config.number_column = $event?.value"
		/>
		<Autocomplete
			label="Date"
			:showFooter="true"
			:options="date_dimensions"
			:modelValue="config.date_column"
			@update:modelValue="config.date_column = $event?.value"
		/>

		<FormControl v-model="config.prefix" label="Prefix" />
		<FormControl v-model="config.suffix" label="Suffix" />
		<FormControl v-model="config.precision" label="Precision" type="number" />
		<Checkbox v-model="config.shorten_numbers" label="Show short numbers" />

		<Checkbox v-if="config.date_column" v-model="config.comparison" label="Show comparison" />
		<Checkbox
			v-if="config.comparison"
			v-model="config.negative_is_better"
			label="Negative is better"
		/>
		<Checkbox v-if="config.date_column" v-model="config.sparkline" label="Show sparkline" />
	</div>
</template>
