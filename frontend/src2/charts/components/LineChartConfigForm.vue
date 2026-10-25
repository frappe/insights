<script setup lang="ts">
import { LineChartConfig, Series, SeriesLine, YAxisLine } from '../../types/chart.types'
import { ColumnOption, DimensionOption } from '../../types/query.types'
import { computed } from 'vue'
import { isStacked, plotsStackable, takesTrendLine } from '../adapter/axis'
import { hasBarsOnBothAxes, setStack } from '../helpers'
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

// The switch shows what is plotted rather than what is saved, as the Bar form's does.
const stackable = computed(
	() =>
		plotsStackable(config.value, 'line', false) &&
		!hasBarsOnBothAxes(config.value.y_axis.series, 'line', false),
)

function offersTrendLine(series: Series) {
	return takesTrendLine(config.value, series, 'line', false)
}
</script>

<template>
	<XAxisConfig v-model="config.x_axis" :dimensions="props.dimensions"></XAxisConfig>

	<YAxisConfig
		v-model="config.y_axis"
		:column-options="props.columnOptions"
		:config="config"
		:takes-trend-line="offersTrendLine"
	>
		<template #y-axis-settings="{ y_axis }">
			<Toggle :label="__('Curved lines')" v-model="(y_axis as YAxisLine).smooth" />
			<Toggle :label="__('Area')" v-model="(y_axis as YAxisLine).show_area" />
			<Toggle
				:label="__('Stack')"
				:model-value="stackable && isStacked(config, 'line', false)"
				@update:model-value="setStack(y_axis as YAxisLine, Boolean($event))"
				:disabled="!stackable"
			/>
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
