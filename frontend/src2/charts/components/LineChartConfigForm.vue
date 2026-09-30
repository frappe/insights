<script setup lang="ts">
import { LineChartConfig, SeriesLine, YAxisLine } from '../../types/chart.types'
import { computed } from 'vue'
import { ColumnOption, DimensionOption } from '../../types/query.types'
import { takesTrendLines } from '../adapter/axis'
import ReferenceLinesConfig from './ReferenceLinesConfig.vue'
import SplitByConfig from './SplitByConfig.vue'
import TooltipConfig from './TooltipConfig.vue'
import XAxisConfig from './XAxisConfig.vue'
import YAxisConfig from './YAxisConfig.vue'

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

const trendLines = computed(() => takesTrendLines(config.value, 'line', false))
</script>

<template>
	<XAxisConfig v-model="config.x_axis" :dimensions="props.dimensions"></XAxisConfig>

	<YAxisConfig
		v-model="config.y_axis"
		:column-options="props.columnOptions"
		:config="config"
		:trend-lines="trendLines"
	>
		<template #y-axis-settings="{ y_axis }">
			<Toggle :label="__('Curved lines')" v-model="(y_axis as YAxisLine).smooth" />
			<Toggle :label="__('Area')" v-model="(y_axis as YAxisLine).show_area" />
			<Toggle :label="__('Data points')" v-model="(y_axis as YAxisLine).show_data_points" />
		</template>
		<template #series-settings="{ series }">
			<Toggle :label="__('Curved lines')" v-model="(series as SeriesLine).smooth" />
			<Toggle :label="__('Area')" v-model="(series as SeriesLine).show_area" />
			<Toggle :label="__('Data points')" v-model="(series as SeriesLine).show_data_points" />
		</template>
	</YAxisConfig>

	<SplitByConfig v-model="config.split_by" :dimensions="props.dimensions" />

	<TooltipConfig v-model="config" :column-options="props.columnOptions" />

	<ReferenceLinesConfig v-model="config" />
</template>
