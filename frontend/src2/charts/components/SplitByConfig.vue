<script setup lang="ts">
import InlineFormControlLabel from '../../components/InlineFormControlLabel.vue'
import { AxisChartConfig } from '../../types/chart.types'
import { DimensionOption } from './ChartConfigForm.vue'
import CollapsibleSection from './CollapsibleSection.vue'

const props = defineProps<{
	dimensions: DimensionOption[]
}>()

const split_by = defineModel<AxisChartConfig['split_by']>({
	required: true,
	default: () => ({}),
})
</script>

<template>
	<CollapsibleSection title="Split Series">
		<InlineFormControlLabel label="Split By">
			<Autocomplete
				placeholder="Select a column"
				:showFooter="true"
				:options="props.dimensions"
				:modelValue="split_by?.column_name"
				@update:modelValue="split_by = $event"
			/>
		</InlineFormControlLabel>
	</CollapsibleSection>
</template>
