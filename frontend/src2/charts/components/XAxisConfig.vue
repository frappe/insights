<script setup lang="ts">
import { AxisChartConfig } from '../../types/chart.types'
import { Dimension, DimensionOption } from '../../types/query.types'
import CollapsibleSection from './CollapsibleSection.vue'
import DimensionPicker from './DimensionPicker.vue'

const props = defineProps<{ dimensions: DimensionOption[] }>()
const x_axis = defineModel<AxisChartConfig['x_axis']>({
	required: true,
	default: () => ({}),
})

// The slot and its dimension are seeded on load, by `ensureConfigSlots`. Seeding
// them here would write the config on mount, which is one autosave and two
// re-runs of the chart data for opening a chart.
</script>

<template>
	<CollapsibleSection :title="__('X Axis')">
		<div class="flex flex-col gap-3 pt-1">
			<DimensionPicker
				:label="__('Column')"
				:options="props.dimensions"
				:modelValue="x_axis.dimension"
				@update:modelValue="x_axis.dimension = $event || {}"
				@remove="x_axis.dimension = {} as Dimension"
			/>
		</div>
	</CollapsibleSection>
</template>
