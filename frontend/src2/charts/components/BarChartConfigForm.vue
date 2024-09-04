<script setup lang="ts">
import InlineFormControlLabel from '../../components/InlineFormControlLabel.vue'
import { BarChartConfig } from '../../types/chart.types'
import AxisChartConfigForm from './AxisChartConfigForm.vue'
import { DimensionOption, MeasureOption } from './ChartConfigForm.vue'

const props = defineProps<{
	dimensions: DimensionOption[]
	measures: MeasureOption[]
}>()

const config = defineModel<BarChartConfig>({
	required: true,
	default: () => ({
		x_axis: '',
		y_axis: [],
		y2_axis: [],
		y2_axis_type: 'line',
		split_by: '',
		stack: true,
		show_data_labels: false,
		swap_axes: false,
		normalize: false,
	}),
})
</script>

<template>
	<AxisChartConfigForm
		v-model="config"
		:dimensions="props.dimensions"
		:measures="props.measures"
	/>
	<InlineFormControlLabel label="Stack" class="!w-1/2">
		<Switch
			v-model="config.stack"
			:tabs="[
				{ label: 'Yes', value: true },
				{ label: 'No', value: false, default: true },
			]"
		/>
	</InlineFormControlLabel>
	<InlineFormControlLabel label="Normalize Data" class="!w-1/2">
		<Switch
			v-model="config.normalize"
			:tabs="[
				{ label: 'Yes', value: true },
				{ label: 'No', value: false, default: true },
			]"
		/>
	</InlineFormControlLabel>
	<InlineFormControlLabel label="Swap X & Y" class="!w-1/2">
		<Switch
			v-model="config.swap_axes"
			:tabs="[
				{ label: 'Yes', value: true },
				{ label: 'No', value: false, default: true },
			]"
		/>
	</InlineFormControlLabel>
</template>
