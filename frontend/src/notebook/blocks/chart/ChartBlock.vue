<script setup lang="jsx">
import InputWithPopover from '@/notebook/blocks/query/builder/InputWithPopover.vue'
import { createChart, default as useChart } from '@/query/useChart'
import useQueries from '@/query/useQueries'
import InvalidWidget from '@/widgets/InvalidWidget.vue'
import widgets from '@/widgets/widgets'
import { computed, provide, ref } from 'vue'
import BlockActions from '../BlockActions.vue'
import BlockAction from '../BlockAction.vue'

import ChartOptionsDropdown from './ChartOptionsDropdown.vue'

const emit = defineEmits(['setChartName', 'remove'])
const props = defineProps({ chartName: String })

const blockRef = ref(null)

let chart = null
if (!props.chartName) {
	const chartName = await createChart()
	emit('setChartName', chartName)
	chart = useChart(chartName)
} else {
	chart = useChart(props.chartName)
}
chart.enableAutoSave()
provide('chart', chart)

function removeChart() {
	chart.delete().then(() => emit('remove'))
}

const queries = await useQueries()
await queries.reload()
const queryOptions = queries.list.map((query) => ({
	label: query.title,
	value: query.name,
	description: query.name,
}))
const selectedQuery = computed(() => {
	return queryOptions.find((op) => op.value === chart.doc.query)
})
</script>

<template>
	<div
		ref="blockRef"
		v-if="chart.doc.name"
		class="relative my-6 min-h-[5rem] overflow-hidden rounded border bg-white"
	>
		<div class="group relative flex h-[20rem] max-h-80 flex-col overflow-hidden bg-white">
			<component
				v-if="chart.doc?.chart_type"
				ref="widget"
				:is="widgets.getComponent(chart.doc.chart_type)"
				:chartData="{ data: chart.data }"
				:options="chart.doc.options"
				:key="JSON.stringify(chart.doc.options)"
			>
				<template #placeholder>
					<div class="relative h-full w-full">
						<InvalidWidget
							class="absolute"
							title="Insufficient options"
							message="Please check the options for this chart"
							icon="settings"
							icon-class="text-gray-400"
						/>
					</div>
				</template>
			</component>
			<!-- else -->
			<div
				v-else
				class="absolute right-0 top-0 flex h-full w-full items-center justify-center"
			>
				<InvalidWidget
					class="absolute"
					title="Query not selected"
					message="Please select a query for this chart"
					icon="settings"
					icon-class="text-gray-400"
				/>
			</div>
		</div>
	</div>

	<BlockActions :blockRef="blockRef">
		<BlockAction class="px-0">
			<div class="relative flex items-center text-gray-800 [&>div]:w-full">
				<InputWithPopover
					placeholder="Query"
					:items="queryOptions"
					:value="selectedQuery"
					placement="bottom-end"
					@update:modelValue="(op) => chart.updateQuery(op.value)"
				></InputWithPopover>
				<p class="pointer-events-none absolute right-0 top-0 flex h-full items-center px-2">
					<FeatherIcon name="chevron-down" class="h-4 w-4 text-gray-400" />
				</p>
			</div>
		</BlockAction>

		<BlockAction class="px-0">
			<ChartOptionsDropdown />
		</BlockAction>

		<BlockAction icon="trash" label="Delete" :action="removeChart"> </BlockAction>
	</BlockActions>
</template>
