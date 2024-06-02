<script setup lang="ts">
import { AxisChartConfig, AxisChartType } from '../helpers'

const props = defineProps<{
	chartType: AxisChartType
	dimensions: Dimension[]
	measures: Measure[]
}>()

const config = defineModel<AxisChartConfig>({
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
			:showFooter="true"
			:options="dimensions"
			:modelValue="config.x_axis"
			@update:modelValue="config.x_axis = $event?.value"
		/>
		<Autocomplete
			label="Y Axis"
			:multiple="true"
			:options="measures"
			:modelValue="config.y_axis"
			@update:modelValue="config.y_axis = $event?.map((v: any) => v.value)"
		/>
		<Autocomplete
			label="Split By"
			:showFooter="true"
			:options="dimensions"
			:modelValue="config.split_by"
			@update:modelValue="config.split_by = $event?.value"
		/>
	</div>
</template>
