<script setup lang="jsx">
import useDashboards from '@/dashboard/useDashboards'
import { createChart, default as useChartOld } from '@/query/useChart'
import useQueryStore from '@/stores/queryStore'
import InvalidWidget from '@/widgets/InvalidWidget.vue'
import widgets from '@/widgets/widgets'
import { computed, inject, provide, ref, watch } from 'vue'
import BlockAction from '../BlockAction.vue'
import BlockActions from '../BlockActions.vue'

import ChartOptionsDropdown from './ChartOptionsDropdown.vue'

const emit = defineEmits(['setChartName', 'remove'])
const props = defineProps({ chartName: String })

const blockRef = ref(null)

let chart = null
if (!props.chartName) {
	const chartName = await createChart()
	emit('setChartName', chartName)
	chart = useChartOld(chartName)
} else {
	chart = useChartOld(props.chartName)
}
chart.enableAutoSave()
provide('chart', chart)

function removeChart() {
	chart.delete().then(() => emit('remove'))
}

const queries = useQueryStore()
const queryOptions = queries.list.map((query) => ({
	label: query.title,
	value: query.name,
	description: query.name,
}))
const selectedQuery = computed(() => {
	return queryOptions.find((op) => op.value === chart.doc.query)
})

const QuerySelector = (props) => {
	return (
		<div class="relative flex w-full items-center text-gray-800 [&>div]:w-full">
			<Autocomplete
				placeholder="Query"
				options={queryOptions}
				modelValue={selectedQuery.value}
				placement="bottom"
				onUpdate:modelValue={(op) => chart.updateQuery(op.value)}
			></Autocomplete>
			<p class="pointer-events-none absolute right-0 top-0 flex h-full items-center px-2">
				<FeatherIcon name="chevron-down" class="h-4 w-4 text-gray-500" />
			</p>
		</div>
	)
}

const showDashboardDialog = ref(false)
const dashboards = useDashboards()
dashboards.reload()
const toDashboard = ref(null)
const addingToDashboard = ref(false)
const dashboardOptions = computed(() => {
	// sort alphabetically
	return dashboards.list
		.sort((a, b) => {
			return a.title.toLowerCase() < b.title.toLowerCase() ? -1 : 1
		})
		.map((d) => ({ label: d.title, value: d.name }))
})
const $notify = inject('$notify')
const addToDashboard = async () => {
	if (!toDashboard.value) return
	await chart.addToDashboard(toDashboard.value.value)
	showDashboardDialog.value = false
	$notify({
		variant: 'success',
		title: 'Success',
		message: 'Chart added to dashboard',
	})
}

const dashboardInput = ref(null)
watch(
	() => showDashboardDialog.value,
	(val) => {
		if (val) {
			setTimeout(() => {
				dashboardInput.value.input?.$el?.blur()
				dashboardInput.value.input?.$el?.focus()
			}, 500)
		}
	},
	{ immediate: true }
)
</script>

<template>
	<div
		ref="blockRef"
		v-if="chart.doc.name"
		class="group relative my-6 h-[20rem] overflow-hidden rounded border bg-white"
	>
		<component
			v-if="chart.doc?.chart_type"
			ref="widget"
			:is="widgets.getComponent(chart.doc.chart_type)"
			:data="chart.data"
			:options="chart.doc.options"
			:key="JSON.stringify([chart.data, chart.doc.options])"
		>
			<template #placeholder>
				<div class="relative h-full w-full">
					<InvalidWidget
						class="absolute"
						title="Insufficient options"
						message="Please check the options for this chart"
						icon="settings"
						icon-class="text-gray-500"
					/>
				</div>
			</template>
		</component>
		<!-- else -->
		<div
			v-else
			class="absolute right-0 top-0 flex h-full w-full flex-col items-center justify-center"
		>
			<div class="mb-1 w-[10rem] text-gray-500">Select a query</div>
			<div class="w-[10rem] rounded border border-dashed border-gray-300">
				<QuerySelector />
			</div>
		</div>
	</div>

	<BlockActions :blockRef="blockRef">
		<BlockAction class="!px-0">
			<QuerySelector />
		</BlockAction>

		<BlockAction class="!px-0" v-if="chart.doc.query">
			<ChartOptionsDropdown />
		</BlockAction>

		<BlockAction
			label="Add to dashboard"
			icon="plus"
			:action="() => (showDashboardDialog = true)"
		/>
		<BlockAction icon="trash" label="Delete" :action="removeChart" :loading="chart.deleting" />
	</BlockActions>

	<Dialog :options="{ title: 'Add to Dashboard' }" v-model="showDashboardDialog">
		<template #body-content>
			<div class="text-base">
				<span class="mb-2 block text-sm leading-4 text-gray-700">Dashboard</span>
				<Autocomplete
					ref="dashboardInput"
					:options="dashboardOptions"
					v-model="toDashboard"
				/>
			</div>
		</template>
		<template #actions>
			<Button variant="solid" @click="addToDashboard" :loading="addingToDashboard">
				Add
			</Button>
		</template>
	</Dialog>
</template>
