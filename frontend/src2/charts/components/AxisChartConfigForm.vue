<script setup lang="ts">
import Tabs from '@/components/Tabs.vue'
import { computed } from 'vue'
import InlineFormControlLabel from '../../components/InlineFormControlLabel.vue'
import { AxisChartConfig } from '../../types/chart.types'
import { Dimension, Measure } from '../../types/query.types'

const props = defineProps<{
	dimensions: Dimension[]
	measures: Measure[]
}>()

const config = defineModel<AxisChartConfig>({
	required: true,
	default: () => ({
		x_axis: '',
		y_axis: [],
		y2_axis: [],
		y2_axis_type: 'line',
		split_by: '',
		show_data_labels: false,
	}),
})

const dimensions = computed(() =>
	props.dimensions.map((dimension) => ({
		label: dimension.column_name,
		value: dimension.column_name,
	}))
)
const measures = computed(() =>
	props.measures.map((measure) => ({
		label: measure.column_name,
		value: measure.column_name,
	}))
)
</script>

<template>
	<InlineFormControlLabel label="Bottom">
		<Autocomplete
			class="w-full"
			:showFooter="true"
			:options="dimensions"
			:modelValue="config.x_axis"
			@update:modelValue="config.x_axis = $event?.value"
		/>
	</InlineFormControlLabel>
	<InlineFormControlLabel label="Left">
		<Autocomplete
			:multiple="true"
			:options="measures"
			:modelValue="config.y_axis"
			@update:modelValue="config.y_axis = $event?.map((v: any) => v.value)"
		/>
	</InlineFormControlLabel>
	<InlineFormControlLabel label="Right">
		<Autocomplete
			:multiple="true"
			:options="measures"
			:modelValue="config.y2_axis"
			@update:modelValue="config.y2_axis = $event?.map((v: any) => v.value)"
		/>
	</InlineFormControlLabel>
	<InlineFormControlLabel label="Split By">
		<Autocomplete
			:showFooter="true"
			:options="dimensions"
			:modelValue="config.split_by"
			@update:modelValue="config.split_by = $event?.value"
		/>
	</InlineFormControlLabel>
	<InlineFormControlLabel label="Right Axis Type" class="!w-1/2">
		<Tabs
			v-model="config.y2_axis_type"
			:tabs="[
				{ label: 'Bar', value: 'bar', default: true },
				{ label: 'Line', value: 'line' },
			]"
		/>
	</InlineFormControlLabel>
	<InlineFormControlLabel label="Show Labels" class="!w-1/2">
		<Tabs
			v-model="config.show_data_labels"
			:tabs="[
				{ label: 'Yes', value: true },
				{ label: 'No', value: false, default: true },
			]"
		/>
	</InlineFormControlLabel>
</template>
