<script setup lang="ts">
import InlineFormControlLabel from '../../components/InlineFormControlLabel.vue'
import { AxisChartConfig } from '../../types/chart.types'
import { DimensionOption, MeasureOption } from './ChartConfigForm.vue'

const props = defineProps<{
	dimensions: DimensionOption[]
	measures: MeasureOption[]
}>()

const config = defineModel<AxisChartConfig>({
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
	<InlineFormControlLabel label="X Axis">
		<Autocomplete
			class="w-full"
			:showFooter="true"
			:options="props.dimensions"
			:modelValue="config.x_axis?.column_name"
			@update:modelValue="config.x_axis = $event"
		/>
	</InlineFormControlLabel>
	<InlineFormControlLabel label="Y Axis">
		<Autocomplete
			:multiple="true"
			:options="props.measures"
			:modelValue="config.y_axis?.map((measure) => measure.measure_name)"
			@update:modelValue="config.y_axis = $event"
		/>
	</InlineFormControlLabel>
	<InlineFormControlLabel label="Split By">
		<Autocomplete
			:showFooter="true"
			:options="props.dimensions"
			:modelValue="config.split_by?.column_name"
			@update:modelValue="config.split_by = $event"
		/>
	</InlineFormControlLabel>
	<InlineFormControlLabel label="Right Y Axis">
		<Autocomplete
			:multiple="true"
			:options="props.measures"
			:modelValue="config.y2_axis?.map((measure) => measure.measure_name)"
			@update:modelValue="config.y2_axis = $event"
		/>
	</InlineFormControlLabel>
	<InlineFormControlLabel v-if="config.y2_axis?.length" label="Right Axis Type" class="!w-1/2">
		<Switch
			v-model="config.y2_axis_type"
			:tabs="[
				{ label: 'Bar', value: 'bar', default: true },
				{ label: 'Line', value: 'line' },
			]"
		/>
	</InlineFormControlLabel>
	<InlineFormControlLabel label="Show Labels" class="!w-1/2">
		<Switch
			v-model="config.show_data_labels"
			:tabs="[
				{ label: 'Yes', value: true },
				{ label: 'No', value: false, default: true },
			]"
		/>
	</InlineFormControlLabel>
</template>
