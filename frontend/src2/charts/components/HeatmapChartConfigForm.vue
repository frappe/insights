<script setup lang="ts">
import { __ } from '../../translation'
import { HeatmapChartConfig } from '../../types/chart.types'
import { ColumnOption, DimensionOption } from '../../types/query.types'
import CollapsibleSection from './CollapsibleSection.vue'
import DimensionPicker from './DimensionPicker.vue'
import MeasurePicker from './MeasurePicker.vue'
import NumberFormatFields from './NumberFormatFields.vue'

const props = defineProps<{
	dimensions: DimensionOption[]
	columnOptions: ColumnOption[]
}>()

const config = defineModel<HeatmapChartConfig>({
	required: true,
	default: () => ({
		x_column: {},
		y_column: {},
		value_column: {},
	}),
})
</script>

<template>
	<CollapsibleSection title="Options">
		<div class="flex flex-col gap-3 pt-1">
			<DimensionPicker label="X Axis" v-model="config.x_column" :options="props.dimensions" />
			<DimensionPicker label="Y Axis" v-model="config.y_column" :options="props.dimensions" />
			<MeasurePicker
				label="Value"
				v-model="config.value_column"
				:column-options="props.columnOptions"
			>
				<template #config-fields>
					<NumberFormatFields
						:config="config"
						:measure-name="config.value_column?.measure_name"
					/>
				</template>
			</MeasurePicker>
			<FormControl
				v-model="config.palette"
				label="Color Scale"
				type="select"
				:options="[
					{ label: __('Sequential'), value: 'sequential' },
					{ label: __('Diverging'), value: 'diverging' },
				]"
			/>
			<Toggle v-model="config.show_values" label="Show Values" />
		</div>
	</CollapsibleSection>
</template>
