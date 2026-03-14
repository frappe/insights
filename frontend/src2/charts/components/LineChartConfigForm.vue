<script setup lang="ts">
import { LineChartConfig, SeriesLine, YAxisLine } from '../../types/chart.types'
import { ColumnOption, DimensionOption } from '../../types/query.types'
import SplitByConfig from './SplitByConfig.vue'
import XAxisConfig from './XAxisConfig.vue'
import YAxisConfig from './YAxisConfig.vue'
import { __ } from '../../translation'

const props = defineProps<{
	dimensions: DimensionOption[]
	columnOptions: ColumnOption[]
}>()

const config = defineModel<LineChartConfig>({
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

	<YAxisConfig v-model="config.y_axis" :column-options="props.columnOptions">
		<template #y-axis-settings="{ y_axis }">
			<Toggle :label="__('Curved Lines')" v-model="(y_axis as YAxisLine).smooth" />
			<Toggle :label="__('Show Area')" v-model="(y_axis as YAxisLine).show_area" />
			<Toggle :label="__('Show Data Points')" v-model="(y_axis as YAxisLine).show_data_points" />
		</template>
		<template #series-settings="{ series }">
			<Toggle :label="__('Curved Lines')" v-model="(series as SeriesLine).smooth" />
			<Toggle :label="__('Show Area')" v-model="(series as SeriesLine).show_area" />
			<Toggle :label="__('Show Data Points')" v-model="(series as SeriesLine).show_data_points" />
		</template>
	</YAxisConfig>

	<SplitByConfig v-model="config.split_by" :dimensions="props.dimensions" />
</template>
