<script setup lang="ts">
import { computed } from 'vue'
import { BarChartConfig, YAxisBar } from '../../types/chart.types'
import { ColumnOption, DimensionOption } from '../../types/query.types'
import { hasBarsOnBothAxes } from '../helpers'
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

// The flags stay as saved, and the adapter ignores them while bars sit on both
// axes, so the switches show what is drawn rather than what is saved.
const barsOnBothAxes = computed(() =>
	hasBarsOnBothAxes(config.value.y_axis.series, 'bar', props.chartType === 'Row'),
)
</script>

<template>
	<XAxisConfig v-model="config.x_axis" :dimensions="props.dimensions"></XAxisConfig>

	<YAxisConfig v-model="config.y_axis" :column-options="props.columnOptions" :config="config">
		<template #y-axis-settings="{ y_axis }">
			<Toggle
				:label="__('Stack')"
				:model-value="barsOnBothAxes ? false : (y_axis as YAxisBar).stack"
				@update:model-value="(y_axis as YAxisBar).stack = Boolean($event)"
				:disabled="barsOnBothAxes"
			/>
			<Toggle
				:label="__('Overlap')"
				:model-value="barsOnBothAxes ? false : (y_axis as YAxisBar).overlap"
				@update:model-value="(y_axis as YAxisBar).overlap = Boolean($event)"
				:disabled="barsOnBothAxes"
			/>
			<Toggle
				:label="__('Normalize')"
				:model-value="barsOnBothAxes ? false : (y_axis as YAxisBar).normalize"
				@update:model-value="(y_axis as YAxisBar).normalize = Boolean($event)"
				:disabled="barsOnBothAxes"
			/>
		</template>
	</YAxisConfig>

	<SplitByConfig v-model="config.split_by" :dimensions="props.dimensions" />

	<TooltipConfig v-model="config" :column-options="props.columnOptions" />

	<ReferenceLinesConfig v-model="config" />
</template>
