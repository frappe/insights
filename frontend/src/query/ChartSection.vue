<script setup>
import PublicShareDialog from '@/components/PublicShareDialog.vue'
import useDashboards from '@/dashboard/useDashboards'
import widgets from '@/widgets/widgets'
import { computed, inject, ref, watch } from 'vue'
import ChartSectionEmpty from './ChartSectionEmpty.vue'

const query = inject('query')

const hideChart = computed(() => {
	return (
		!query.chart.doc?.name ||
		!query.formattedResults?.length ||
		query.doc.status == 'Pending Execution'
	)
})

const emptyMessage = computed(() => {
	if (query.doc.status == 'Pending Execution') {
		return 'Execute the query to see the chart'
	}
	if (!query.formattedResults?.length) {
		return 'No results found'
	}
	return 'Pick a chart type to get started'
})

const showShareDialog = ref(false)
const showDashboardDialog = ref(false)
const dashboards = useDashboards()
dashboards.reload()
const toDashboard = ref(null)
const addingToDashboard = ref(false)
const dashboardOptions = computed(() => {
	return dashboards.list.map((d) => {
		return { label: d.title, value: d.name }
	})
})
const $notify = inject('$notify')
const addChartToDashboard = async () => {
	if (!toDashboard.value) return
	await query.chart.addToDashboard(toDashboard.value.value)
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
	<div v-if="query.chart.doc?.name" class="flex flex-1 flex-col gap-4 overflow-hidden">
		<div class="flex flex-shrink-0 space-x-2">
			<Button variant="outline" :disabled="hideChart" @click="showDashboardDialog = true">
				Add to Dashboard
			</Button>
			<Button variant="outline" :disabled="hideChart" @click="showShareDialog = true">
				Share
			</Button>
		</div>

		<div
			v-if="hideChart"
			class="flex flex-1 flex-col items-center justify-center rounded border"
		>
			<ChartSectionEmpty></ChartSectionEmpty>
			<span class="text-gray-500">{{ emptyMessage }}</span>
		</div>
		<div v-else class="flex w-full flex-1 overflow-hidden rounded border">
			<component
				v-if="query.chart.doc.chart_type"
				ref="widget"
				:key="JSON.stringify(query.chart.doc)"
				:is="widgets.getComponent(query.chart.doc.chart_type)"
				:data="query.chart.data"
				:options="query.chart.doc.options"
			/>
		</div>
	</div>

	<PublicShareDialog
		v-if="query.chart.doc?.doctype && query.chart.doc?.name"
		v-model:show="showShareDialog"
		:resource-type="query.chart.doc.doctype"
		:resource-name="query.chart.doc.name"
		:allow-public-access="true"
		:isPublic="Boolean(query.chart.doc.is_public)"
		@togglePublicAccess="query.chart.togglePublicAccess"
	/>

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
			<Button variant="solid" @click="addChartToDashboard" :loading="addingToDashboard">
				Add
			</Button>
		</template>
	</Dialog>
</template>
