<script setup lang="ts">
import { watchEffect } from 'vue'
import { __ } from '../../translation'
import { SankeyChartConfig } from '../../types/chart.types'
import { ColumnOption, Dimension, DimensionOption, Measure } from '../../types/query.types'
import CollapsibleSection from './CollapsibleSection.vue'
import DimensionPicker from './DimensionPicker.vue'
import MeasurePicker from './MeasurePicker.vue'

const props = defineProps<{
	dimensions: DimensionOption[]
	columnOptions: ColumnOption[]
}>()

const config = defineModel<SankeyChartConfig>({
	required: true,
	default: () => ({
		source_column: {},
		target_column: {},
		value_column: {},
	}),
})

watchEffect(() => {
	if (!config.value.source_column) {
		config.value.source_column = {} as Dimension
	}
	if (!config.value.target_column) {
		config.value.target_column = {} as Dimension
	}
	if (!config.value.value_column) {
		config.value.value_column = {} as Measure
	}
})
</script>

<template>
	<CollapsibleSection title="Options">
		<div class="flex flex-col gap-3 pt-1">
			<DimensionPicker
				label="Source"
				v-model="config.source_column"
				:options="props.dimensions"
			/>
			<DimensionPicker
				label="Target"
				v-model="config.target_column"
				:options="props.dimensions"
			/>
			<MeasurePicker
				label="Value"
				v-model="config.value_column"
				:column-options="props.columnOptions"
			/>
			<FormControl
				v-model="config.orient"
				label="Orientation"
				type="select"
				:options="[
					{ label: __('Horizontal'), value: 'horizontal' },
					{ label: __('Vertical'), value: 'vertical' },
				]"
			/>
			<FormControl
				v-model="config.node_align"
				label="Node Alignment"
				type="select"
				:options="[
					{ label: __('Justify'), value: 'justify' },
					{ label: __('Left'), value: 'left' },
					{ label: __('Right'), value: 'right' },
				]"
			/>
		</div>
	</CollapsibleSection>
</template>
