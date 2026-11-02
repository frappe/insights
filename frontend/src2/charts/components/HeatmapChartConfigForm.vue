<script setup lang="ts">
import { __ } from '../../translation'
import { HeatmapChartConfig } from '../../types/chart.types'
import { ColumnOption, DimensionOption } from '../../types/query.types'
import CollapsibleSection from './CollapsibleSection.vue'
import InlineFormControlLabel from '../../components/InlineFormControlLabel.vue'
import NumberInput from '../../components/NumberInput.vue'
import DimensionPicker from './DimensionPicker.vue'
import MeasurePicker from './MeasurePicker.vue'
import NumberFormatSection from './NumberFormatSection.vue'

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
	<CollapsibleSection :title="__('Options')">
		<div class="flex flex-col gap-3 pt-1">
			<DimensionPicker
				:label="__('X axis')"
				v-model="config.x_column"
				:options="props.dimensions"
			/>
			<DimensionPicker
				:label="__('Y axis')"
				v-model="config.y_column"
				:options="props.dimensions"
			/>
			<MeasurePicker
				:label="__('Value')"
				v-model="config.value_column"
				:column-options="props.columnOptions"
			/>
			<InlineFormControlLabel :label="__('Color scale')" control-width="7rem">
				<FormControl
					v-model="config.palette"
					type="select"
					:options="[
						{ label: __('Sequential'), value: 'sequential' },
						{ label: __('Diverging'), value: 'diverging' },
					]"
				/>
			</InlineFormControlLabel>
			<InlineFormControlLabel :label="__('Scale floor')" control-width="4rem">
				<NumberInput v-model="config.min" :placeholder="__('Lowest')" />
			</InlineFormControlLabel>
			<InlineFormControlLabel :label="__('Scale ceiling')" control-width="4rem">
				<NumberInput v-model="config.max" :placeholder="__('Highest')" />
			</InlineFormControlLabel>
			<Toggle v-model="config.show_values" :label="__('Values')" />
		</div>
	</CollapsibleSection>

	<NumberFormatSection :config="config" :sole-measure-name="config.value_column?.measure_name" />
</template>
