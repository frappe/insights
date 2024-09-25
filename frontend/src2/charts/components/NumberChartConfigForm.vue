<script setup lang="ts">
import { FIELDTYPES } from '../../helpers/constants'
import { computed } from 'vue'
import InlineFormControlLabel from '../../components/InlineFormControlLabel.vue'
import { NumberChartConfig } from '../../types/chart.types'
import { DimensionOption, MeasureOption } from './ChartConfigForm.vue'
import CollapsibleSection from './CollapsibleSection.vue'

const props = defineProps<{
	dimensions: DimensionOption[]
	measures: MeasureOption[]
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
	props.dimensions.filter((d) => FIELDTYPES.DATE.includes(d.data_type))
)
</script>

<template>
	<CollapsibleSection title="Options">
		<div class="flex flex-col gap-3 pt-1">
			<InlineFormControlLabel label="Number">
				<Autocomplete
					:multiple="true"
					:showFooter="true"
					:options="props.measures"
					:modelValue="config.number_columns?.map((c) => c.measure_name)"
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
				<Switch
					v-model="config.shorten_numbers"
					:tabs="[
						{ label: 'Yes', value: true, default: true },
						{ label: 'No', value: false },
					]"
				/>
			</InlineFormControlLabel>

			<InlineFormControlLabel
				v-if="config.date_column"
				label="Show comparison"
				class="!w-1/2"
			>
				<Switch
					v-model="config.comparison"
					:tabs="[
						{ label: 'Yes', value: true },
						{ label: 'No', value: false, default: true },
					]"
				/>
			</InlineFormControlLabel>

			<InlineFormControlLabel
				v-if="config.comparison"
				label="Negative is better"
				class="!w-1/2"
			>
				<Switch
					v-model="config.negative_is_better"
					:tabs="[
						{ label: 'Yes', value: true },
						{ label: 'No', value: false, default: true },
					]"
				/>
			</InlineFormControlLabel>

			<InlineFormControlLabel v-if="config.date_column" label="Show sparkline" class="!w-1/2">
				<Switch
					v-model="config.sparkline"
					:tabs="[
						{ label: 'Yes', value: true },
						{ label: 'No', value: false, default: true },
					]"
				/>
			</InlineFormControlLabel>
		</div>
	</CollapsibleSection>
</template>
