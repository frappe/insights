<script setup lang="ts">
import { computed } from 'vue'
import { LineChartConfig, SeriesLine, YAxisLine } from '../../types/chart.types'
import { ColumnOption, DimensionOption } from '../../types/query.types'
import SplitByConfig from './SplitByConfig.vue'
import XAxisConfig from './XAxisConfig.vue'
import YAxisConfig from './YAxisConfig.vue'

const props = defineProps<{
	dimensions: DimensionOption[]
	columnOptions: ColumnOption[]
	logScale: boolean
}>()

const config = defineModel<LineChartConfig>({
	required: true,
	default: () => ({
		x_axis: {},
		y_axis: {},
		split_by: {},
	}),
})
const emit = defineEmits(['update:logScale'])

const logScaleModel = computed({
	get: () => props.logScale,
	set: (val: boolean) => emit('update:logScale', val),
})
</script>

<template>
	<XAxisConfig v-model="config.x_axis" :dimensions="props.dimensions"></XAxisConfig>

	<YAxisConfig v-model="config.y_axis" :column-options="props.columnOptions">
		<template #y-axis-settings="{ y_axis }">
			<Toggle label="Curved Lines" v-model="(y_axis as YAxisLine).smooth" />
			<Toggle label="Show Area" v-model="(y_axis as YAxisLine).show_area" />
			<Toggle label="Show Data Points" v-model="(y_axis as YAxisLine).show_data_points" />
			<Toggle v-model="logScaleModel" label="Log Scale" />
		</template>
		<template #series-settings="{ series }">
			<Toggle label="Curved Lines" v-model="(series as SeriesLine).smooth" />
			<Toggle label="Show Area" v-model="(series as SeriesLine).show_area" />
			<Toggle label="Show Data Points" v-model="(series as SeriesLine).show_data_points" />
		</template>
	</YAxisConfig>

	<SplitByConfig v-model="config.split_by" :dimensions="props.dimensions" />
</template>
