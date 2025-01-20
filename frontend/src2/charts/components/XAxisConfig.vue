<script setup lang="ts">
import { watchEffect } from 'vue'
import InlineFormControlLabel from '../../components/InlineFormControlLabel.vue'
import { AxisChartConfig, XAxis } from '../../types/chart.types'
import { Dimension, DimensionOption } from '../../types/query.types'
import CollapsibleSection from './CollapsibleSection.vue'
import DimensionPicker from './DimensionPicker.vue'

const props = defineProps<{ dimensions: DimensionOption[] }>()
const x_axis = defineModel<AxisChartConfig['x_axis']>({
	required: true,
	default: () => ({}),
})

watchEffect(() => {
	if (!x_axis.value) {
		x_axis.value = {
			dimension: {} as Dimension,
		}
	}
	if (!x_axis.value.dimension) {
		x_axis.value.dimension = {} as Dimension
	}
})
</script>

<template>
	<CollapsibleSection title="X Axis">
		<div class="flex flex-col gap-3 pt-1">
			<DimensionPicker
				label="Column"
				:options="props.dimensions"
				:modelValue="x_axis.dimension"
				@update:modelValue="x_axis.dimension = $event || {}"
			/>
			<Checkbox label="Show Axis Label" />
			<InlineFormControlLabel v-if="false" label="Axis Label">
				<FormControl />
			</InlineFormControlLabel>
		</div>
	</CollapsibleSection>
</template>
