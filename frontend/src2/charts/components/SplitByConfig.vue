<script setup lang="ts">
import InlineFormControlLabel from '../../components/InlineFormControlLabel.vue'
import { AxisChartConfig } from '../../types/chart.types'
import { DimensionOption } from './ChartConfigForm.vue'
import CollapsibleSection from './CollapsibleSection.vue'
import DimensionPicker from './DimensionPicker.vue'

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
		<DimensionPicker
			label="Split By"
			:options="props.dimensions"
			:modelValue="split_by || {}"
			@update:modelValue="split_by = $event || {}"
		/>
	</CollapsibleSection>
</template>
