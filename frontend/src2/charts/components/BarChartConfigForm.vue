<script setup lang="ts">
import { computed, watchEffect } from 'vue'
import { BarChartConfig, YAxisBar } from '../../types/chart.types'
import { ColumnOption, Dimension, DimensionOption } from '../../types/query.types'
import SplitByConfig from './SplitByConfig.vue'
import XAxisConfig from './XAxisConfig.vue'
import YAxisConfig from './YAxisConfig.vue'

const props = defineProps<{
	dimensions: DimensionOption[]
	columnOptions: ColumnOption[]
}>()

const config = defineModel<BarChartConfig>({
	required: true,
	default: () => ({
		x_axis: {},
		y_axis: {},
		split_by: {},
	}),
})

watchEffect(() => {
	if (!config.value.x_axis) {
		config.value.x_axis = {} as Dimension
	}
	if (!config.value.y_axis) {
		config.value.y_axis = {} as YAxisBar
	}
	if (config.value.y_axis?.stack === undefined) {
		config.value.y_axis.stack = true
	}
	if (hasAxisSplit.value) {
		config.value.y_axis.stack = false
	}
})

const hasAxisSplit = computed(() => {
	return (
		config.value.y_axis.series.find((s) => s.align === 'Right') &&
		config.value.y_axis.series.find((s) => s.align === 'Left')
	)
})
</script>

<template>
	<XAxisConfig v-model="config.x_axis" :dimensions="props.dimensions"></XAxisConfig>

	<YAxisConfig v-model="config.y_axis" :column-options="props.columnOptions">
		<template #y-axis-settings="{ y_axis }">
			<Checkbox label="Stack" v-model="(y_axis as YAxisBar).stack" :disabled="hasAxisSplit" />
			<Checkbox label="Normalize" v-model="(y_axis as YAxisBar).normalize" />
		</template>
	</YAxisConfig>

	<SplitByConfig v-model="config.split_by" :dimensions="props.dimensions" />
</template>
