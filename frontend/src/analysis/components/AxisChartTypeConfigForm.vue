<script setup lang="ts">
import { Dimension, Measure } from '@/datamodel/useDataModel'
import { ChartType } from '@/widgets/widgets'
import { AxisChartFormData } from '../useAnalysisChart'

const props = defineProps<{
	chartType: ChartType
	dimensions: Dimension[]
	measures: Measure[]
}>()

const axisChartFormData = defineModel<AxisChartFormData>({
	required: true,
	default: () => ({
		x_axis: '',
		y_axis: [],
		split_by: '',
	}),
})

const dimensions = props.dimensions.map((dimension) => ({
	label: dimension.column_name,
	value: dimension.column_name,
}))
const measures = props.measures.map((measure) => ({
	label: measure.column_name,
	value: measure.column_name,
}))
</script>

<template>
	<div class="flex flex-col gap-3 p-3">
		<Autocomplete
			label="X Axis"
			:options="dimensions"
			:modelValue="axisChartFormData.x_axis"
			@update:modelValue="axisChartFormData.x_axis = $event.value"
		/>
		<Autocomplete
			label="Y Axis"
			:multiple="true"
			:options="measures"
			:modelValue="axisChartFormData.y_axis"
			@update:modelValue="axisChartFormData.y_axis = $event.map((v: any) => v.value)"
		/>
		<Autocomplete
			label="Split By"
			:options="dimensions"
			:modelValue="axisChartFormData.split_by"
			@update:modelValue="axisChartFormData.split_by = $event.value"
		/>
	</div>
</template>
