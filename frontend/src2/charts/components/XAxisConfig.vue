<script setup lang="ts">
import { watchEffect } from 'vue'
import InlineFormControlLabel from '../../components/InlineFormControlLabel.vue'
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
			<FormControl
				label="Rotate Values"
				type="select"
				v-model="x_axis.label_rotation"
				:options="[
					{ label: '0°', value: 0 },
					{ label: '30°', value: 30 },
					{ label: '45°', value: 45 },
					{ label: '60°', value: 60 },
					{ label: '75°', value: 75 },
					{ label: '90°', value: 90 },
				]"
			/>
			<!-- <Toggle label="Show Axis Title" />
			<InlineFormControlLabel v-if="false" label="Axis Title Text">
				<FormControl />
			</InlineFormControlLabel> -->
		</div>
	</CollapsibleSection>
</template>
