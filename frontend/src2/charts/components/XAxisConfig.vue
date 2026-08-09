<script setup lang="ts">
import { watchEffect } from 'vue'
import { AxisChartConfig } from '../../types/chart.types'
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
				@remove="x_axis.dimension = {} as Dimension"
			/>
			<!-- <Toggle label="Show Axis Title" />
			<InlineFormControlLabel v-if="false" label="Axis Title Text">
				<FormControl />
			</InlineFormControlLabel> -->
		</div>
	</CollapsibleSection>
</template>
