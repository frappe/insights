<script setup lang="ts">
import { BarChartConfig, YAxisBar } from '../../types/chart.types'
import { DimensionOption, MeasureOption } from './ChartConfigForm.vue'
import SplitByConfig from './SplitByConfig.vue'
import XAxisConfig from './XAxisConfig.vue'
import YAxisConfig from './YAxisConfig.vue'

const props = defineProps<{
	dimensions: DimensionOption[]
	measures: MeasureOption[]
}>()

const config = defineModel<BarChartConfig>({
	required: true,
	default: () => ({
		x_axis: {},
		y_axis: {},
		split_by: {},
	}),
})
</script>

<template>
	<XAxisConfig v-model="config.x_axis" :dimensions="props.dimensions"></XAxisConfig>

	<YAxisConfig v-model="config.y_axis" :measures="props.measures">
		<template #y-axis-settings="{ y_axis }">
			<Checkbox label="Stack" v-model="(y_axis as YAxisBar).stack" />
			<Checkbox label="Normalize" v-model="(y_axis as YAxisBar).normalize" />
			<Checkbox label="Show Data Labels" v-model="(y_axis as YAxisBar).show_data_labels" />
		</template>
	</YAxisConfig>

	<SplitByConfig v-model="config.split_by" :dimensions="props.dimensions" />
</template>
