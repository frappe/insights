<script setup lang="ts">
import { BubbleChartConfig } from '../../types/chart.types'
import { ColumnOption, Dimension, DimensionOption, Measure } from '../../types/query.types'
import CollapsibleSection from './CollapsibleSection.vue'
import MeasurePicker from './MeasurePicker.vue'
import DimensionPicker from './DimensionPicker.vue'

const props = defineProps<{
	dimensions: DimensionOption[]
	columnOptions: ColumnOption[]
}>()

const config = defineModel<BubbleChartConfig>({
	required: true,
	default: () => ({
		xAxis: {} as Measure,
		yAxis: {} as Measure,
		size_column: {} as Measure,
		dimension: {} as Dimension,
		quadrant_column: {} as Dimension,
		show_data_labels: false,
		show_quadrants: false,
	}),
})

if (!config.value.xAxis) {
	config.value.xAxis = {} as Measure
}
if (!config.value.yAxis) {
	config.value.yAxis = {} as Measure
}
if (!config.value.size_column) {
	config.value.size_column = {} as Measure
}

</script>

<template>
	<CollapsibleSection title="Setup">
		<div class="flex flex-col gap-3 pt-1">
			<MeasurePicker
				label="X Axis"
				v-model="config.xAxis"
				:column-options="props.columnOptions"
			/>

			<MeasurePicker
				label="Y Axis"
				v-model="config.yAxis"
				:column-options="props.columnOptions"
			/>
			<DimensionPicker
				label="Color by"
				v-model="config.quadrant_column!"
				:options="props.dimensions"
				@remove="config.quadrant_column = {} as Dimension"
			/>
			<MeasurePicker
				label="Size Column"
				v-model="config.size_column!"
				:column-options="props.columnOptions"
				@remove="config.size_column = {} as Measure"
			/>
		</div>
	</CollapsibleSection>

	<CollapsibleSection title="Options">
		<div class="flex flex-col gap-2 pt-1">
			<div class="flex flex-col gap-2">
				<div class="flex flex-col gap-3">
				<DimensionPicker
					label="Name Column"
					v-model="config.dimension!"
					:options="props.dimensions"
					@remove="config.dimension = {} as Dimension"
						/>
					</div>
				<div
					class="group  flex flex-col items-between justify-between rounded py-2"
				>
					<div class=" gap-3">
						<Toggle
							v-model="config.show_data_labels"
							label="Show Data Labels"
						/>
					</div>
				</div>
			</div>
		</div>
	</CollapsibleSection>

</template>
