<script setup lang="ts">
import InlineFormControlLabel from '../../components/InlineFormControlLabel.vue'
import { AxisChartConfig } from '../../types/chart.types'
import { DimensionOption } from './ChartConfigForm.vue'
import CollapsibleSection from './CollapsibleSection.vue'
import DimensionPicker from './DimensionPicker.vue'

const props = defineProps<{ dimensions: DimensionOption[] }>()
const x_axis = defineModel<AxisChartConfig['x_axis']>({
	required: true,
	default: () => ({}),
})
</script>

<template>
	<CollapsibleSection title="X Axis">
		<div class="flex flex-col gap-3 pt-1">
			<DimensionPicker
				label="Column"
				:options="props.dimensions"
				:modelValue="x_axis"
				@update:modelValue="x_axis = $event || {}"
			/>
			<Checkbox label="Show Axis Label" />
			<InlineFormControlLabel v-if="false" label="Axis Label">
				<FormControl />
			</InlineFormControlLabel>
		</div>
	</CollapsibleSection>
</template>
