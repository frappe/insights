<script setup lang="ts">
import InlineFormControlLabel from '../../components/InlineFormControlLabel.vue'
import { TableChartConfig } from '../../types/chart.types'
import { DimensionOption, MeasureOption } from './ChartConfigForm.vue'
import CollapsibleSection from './CollapsibleSection.vue'

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
</script>

<template>
	<CollapsibleSection title="Options">
		<div class="flex flex-col gap-3 pt-1">
			<InlineFormControlLabel label="Rows">
				<Autocomplete
					:multiple="true"
					:options="props.dimensions"
					:modelValue="config.rows"
					@update:modelValue="config.rows = $event"
				/>
			</InlineFormControlLabel>
			<InlineFormControlLabel label="Columns">
				<Autocomplete
					:multiple="true"
					:options="props.dimensions"
					:modelValue="config.columns"
					@update:modelValue="config.columns = $event"
				/>
			</InlineFormControlLabel>
			<InlineFormControlLabel label="Values">
				<Autocomplete
					:multiple="true"
					:options="props.measures"
					:modelValue="config.values"
					@update:modelValue="config.values = $event"
				/>
			</InlineFormControlLabel>
		</div>
	</CollapsibleSection>
</template>
