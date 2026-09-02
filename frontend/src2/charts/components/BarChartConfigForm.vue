<script setup lang="ts">
import { computed, watchEffect } from 'vue'
import { BarChartConfig, YAxisBar } from '../../types/chart.types'
import { ColumnOption, DimensionOption } from '../../types/query.types'
import ReferenceLinesConfig from './ReferenceLinesConfig.vue'
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

const hasAxisSplit = computed(() => {
	return (
		config.value.y_axis.series?.find((s) => s.align === 'Right') &&
		config.value.y_axis.series?.find((s) => s.align === 'Left')
	)
})

// The slots and the stack default are set on load, by `ensureConfigSlots`. Only
// the rule that answers an edit belongs here: a split axis cannot stack.
watchEffect(() => {
	if (hasAxisSplit.value) {
		config.value.y_axis.stack = false
	}
})
</script>

<template>
	<XAxisConfig v-model="config.x_axis" :dimensions="props.dimensions"></XAxisConfig>

	<YAxisConfig v-model="config.y_axis" :column-options="props.columnOptions">
		<template #y-axis-settings="{ y_axis }">
			<Toggle label="Stack" v-model="(y_axis as YAxisBar).stack" :disabled="hasAxisSplit" />
			<Toggle
				label="Overlap"
				v-model="(y_axis as YAxisBar).overlap"
				:disabled="hasAxisSplit"
			/>
			<Toggle label="Normalize" v-model="(y_axis as YAxisBar).normalize" />
		</template>
	</YAxisConfig>

	<SplitByConfig v-model="config.split_by" :dimensions="props.dimensions" />

	<ReferenceLinesConfig v-model="config.y_axis" />
</template>
