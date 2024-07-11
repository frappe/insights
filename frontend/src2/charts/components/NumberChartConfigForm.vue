<script setup lang="ts">
import Tabs from '@/components/Tabs.vue'
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
		number_columns: [],
		comparison: false,
		sparkline: false,
	}),
})

const date_dimensions = computed(() =>
	props.dimensions
		.filter((d) => FIELDTYPES.DATE.includes(d.data_type))
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
	<InlineFormControlLabel label="Number">
		<Autocomplete
			:multiple="true"
			:showFooter="true"
			:options="measures"
			:modelValue="config.number_columns?.map((c) => c.column_name)"
			@update:modelValue="config.number_columns = $event"
		/>
	</InlineFormControlLabel>

	<InlineFormControlLabel label="Date">
		<Autocomplete
			:showFooter="true"
			:options="date_dimensions"
			:modelValue="config.date_column?.column_name"
			@update:modelValue="config.date_column = $event"
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
	<InlineFormControlLabel label="Show short numbers" class="!w-1/2">
		<Tabs
			v-model="config.shorten_numbers"
			:tabs="[
				{ label: 'Yes', value: true, default: true },
				{ label: 'No', value: false },
			]"
		/>
	</InlineFormControlLabel>

	<InlineFormControlLabel v-if="config.date_column" label="Show comparison" class="!w-1/2">
		<Tabs
			v-model="config.comparison"
			:tabs="[
				{ label: 'Yes', value: true },
				{ label: 'No', value: false, default: true },
			]"
		/>
	</InlineFormControlLabel>

	<InlineFormControlLabel v-if="config.comparison" label="Negative is better" class="!w-1/2">
		<Tabs
			v-model="config.negative_is_better"
			:tabs="[
				{ label: 'Yes', value: true },
				{ label: 'No', value: false, default: true },
			]"
		/>
	</InlineFormControlLabel>

	<InlineFormControlLabel v-if="config.date_column" label="Show sparkline" class="!w-1/2">
		<Tabs
			v-model="config.sparkline"
			:tabs="[
				{ label: 'Yes', value: true },
				{ label: 'No', value: false, default: true },
			]"
		/>
	</InlineFormControlLabel>
</template>
