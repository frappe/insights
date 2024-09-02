<script setup lang="ts">
import { LineChartConfig } from '../../types/chart.types'
import AxisChartConfigForm from './AxisChartConfigForm.vue'
import { DimensionOption, MeasureOption } from './ChartConfigForm.vue'
import InlineFormControlLabel from '../../components/InlineFormControlLabel.vue'

const props = defineProps<{
	dimensions: DimensionOption[]
	measures: MeasureOption[]
}>()

const config = defineModel<LineChartConfig>({
	required: true,
	default: () => ({
		x_axis: {},
		y_axis: [],
		y2_axis: [],
		y2_axis_type: 'line',
		split_by: {},
		show_data_labels: false,
	}),
})
</script>

<template>
	<AxisChartConfigForm
		v-model="config"
		:dimensions="props.dimensions"
		:measures="props.measures"
	/>

	<InlineFormControlLabel label="Enable Curved Lines" class="!w-1/2">
		<Switch
			v-model="config.smooth"
			:tabs="[
				{ label: 'Yes', value: true },
				{ label: 'No', value: false, default: true },
			]"
		/>
	</InlineFormControlLabel>

	<InlineFormControlLabel label="Show Data Points" class="!w-1/2">
		<Switch
			v-model="config.show_data_points"
			:tabs="[
				{ label: 'Yes', value: true },
				{ label: 'No', value: false, default: true },
			]"
		/>
	</InlineFormControlLabel>

	<InlineFormControlLabel label="Show Area" class="!w-1/2">
		<Switch
			v-model="config.show_area"
			:tabs="[
				{ label: 'Yes', value: true },
				{ label: 'No', value: false, default: true },
			]"
		/>
	</InlineFormControlLabel>
</template>
