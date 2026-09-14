<script setup lang="ts">
import { computed, watchEffect } from 'vue'
import { BarChartConfig, YAxisBar } from '../../types/chart.types'
import { ColumnOption, DimensionOption } from '../../types/query.types'
import { hasSplitAxis } from '../helpers'
import ReferenceLinesConfig from './ReferenceLinesConfig.vue'
import SplitByConfig from './SplitByConfig.vue'
import TooltipConfig from './TooltipConfig.vue'
import XAxisConfig from './XAxisConfig.vue'
import YAxisConfig from './YAxisConfig.vue'

const props = defineProps<{
	chartType: string
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

const hasAxisSplit = computed(() => hasSplitAxis(config.value.y_axis.series, props.chartType))

// The slots, the stack default and the split-axis rule are settled on load, by
// `ensureConfigSlots`. This answers the edit that splits the axis while the form
// is open, and writes nothing to a chart that arrives already settled.
watchEffect(() => {
	if (!hasAxisSplit.value) return
	if (config.value.y_axis.stack) config.value.y_axis.stack = false
	if (config.value.y_axis.overlap) config.value.y_axis.overlap = false
	if (config.value.y_axis.normalize) config.value.y_axis.normalize = false
})
</script>

<template>
	<XAxisConfig v-model="config.x_axis" :dimensions="props.dimensions"></XAxisConfig>

	<YAxisConfig v-model="config.y_axis" :column-options="props.columnOptions" :config="config">
		<template #y-axis-settings="{ y_axis }">
			<Toggle
				:label="__('Stack')"
				v-model="(y_axis as YAxisBar).stack"
				:disabled="hasAxisSplit"
			/>
			<Toggle
				:label="__('Overlap')"
				v-model="(y_axis as YAxisBar).overlap"
				:disabled="hasAxisSplit"
			/>
			<Toggle
				:label="__('Normalize')"
				v-model="(y_axis as YAxisBar).normalize"
				:disabled="hasAxisSplit"
			/>
		</template>
	</YAxisConfig>

	<SplitByConfig v-model="config.split_by" :dimensions="props.dimensions" />

	<TooltipConfig v-model="config" :column-options="props.columnOptions" />

	<ReferenceLinesConfig v-model="config" />
</template>
