<script setup lang="ts">
import Checkbox from '@/components/Controls/Checkbox.vue'
import { FIELDTYPES } from '@/utils'
import { computed } from 'vue'
import InlineFormControlLabel from '../../components/InlineFormControlLabel.vue'
import { NumberChartConfig } from '../../types/chart.types'
import { Dimension, Measure } from '../../types/query.types'

const props = defineProps<{
	dimensions: Dimension[]
	measures: Measure[]
}>()

const config = defineModel<NumberChartConfig>({
	required: true,
	default: () => ({
		number_columns: '',
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
	<InlineFormControlLabel label="Number">
		<Autocomplete
			:multiple="true"
			:showFooter="true"
			:options="measures"
			:modelValue="config.number_columns"
			@update:modelValue="config.number_columns = $event?.map((v: any) => v.value)"
		/>
	</InlineFormControlLabel>

	<InlineFormControlLabel label="Date">
		<Autocomplete
			:showFooter="true"
			:options="date_dimensions"
			:modelValue="config.date_column"
			@update:modelValue="config.date_column = $event?.value"
		/>
	</InlineFormControlLabel>

	<InlineFormControlLabel label="Prefix">
		<FormControl v-model="config.prefix" />
	</InlineFormControlLabel>
	<InlineFormControlLabel label="Suffix">
		<FormControl v-model="config.suffix" />
	</InlineFormControlLabel>
	<InlineFormControlLabel label="Decimal">
		<FormControl v-model="config.decimal" type="number" />
	</InlineFormControlLabel>
	<InlineFormControlLabel label="Show short numbers" class="w-2/3">
		<Checkbox v-model="config.shorten_numbers" />
	</InlineFormControlLabel>

	<InlineFormControlLabel v-if="config.date_column" label="Show comparison" class="w-2/3">
		<Checkbox v-model="config.comparison" />
	</InlineFormControlLabel>

	<InlineFormControlLabel v-if="config.comparison" label="Negative is better" class="w-2/3">
		<Checkbox v-model="config.negative_is_better" />
	</InlineFormControlLabel>

	<InlineFormControlLabel v-if="config.date_column" label="Show sparkline" class="w-2/3">
		<Checkbox v-model="config.sparkline" />
	</InlineFormControlLabel>
</template>
