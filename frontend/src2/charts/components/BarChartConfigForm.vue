<script setup lang="ts">
import Tabs from '@/components/Tabs.vue'
import { computed } from 'vue'
import InlineFormControlLabel from '../../components/InlineFormControlLabel.vue'
import { BarChartConfig } from '../../types/chart.types'
import { Dimension, Measure } from '../../types/query.types'
import AxisChartConfigForm from './AxisChartConfigForm.vue'

const props = defineProps<{
	dimensions: Dimension[]
	measures: Measure[]
}>()

const config = defineModel<BarChartConfig>({
	required: true,
	default: () => ({
		x_axis: '',
		y_axis: [],
		y2_axis: [],
		y2_axis_type: 'line',
		split_by: '',
		grouping: 'stacked',
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
	<InlineFormControlLabel label="Grouping">
		<Tabs
			v-model="config.grouping"
			:tabs="[
				{ label: 'Stacked', value: 'stacked', default: true },
				{ label: 'Grouped', value: 'grouped' },
			]"
		/>
	</InlineFormControlLabel>
	<InlineFormControlLabel label="Normalize Data" class="!w-1/2">
		<Tabs
			v-model="config.normalize"
			:tabs="[
				{ label: 'Yes', value: true },
				{ label: 'No', value: false, default: true },
			]"
		/>
	</InlineFormControlLabel>
	<InlineFormControlLabel label="Swap X & Y" class="!w-1/2">
		<Tabs
			v-model="config.swap_axes"
			:tabs="[
				{ label: 'Yes', value: true },
				{ label: 'No', value: false, default: true },
			]"
		/>
	</InlineFormControlLabel>
</template>
