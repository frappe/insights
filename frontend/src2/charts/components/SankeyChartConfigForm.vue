<script setup lang="ts">
import { __ } from '../../translation'
import { SankeyChartConfig } from '../../types/chart.types'
import { ColumnOption, DimensionOption } from '../../types/query.types'
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
