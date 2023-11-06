<script setup>
import PublicShareDialog from '@/components/PublicShareDialog.vue'
import useDashboards from '@/dashboard/useDashboards'
import widgets from '@/widgets/widgets'
import { computed, inject, ref, watch } from 'vue'
import ChartSectionEmpty from './ChartSectionEmpty.vue'

const query = inject('query')
const builder = inject('builder')
const chartRefreshKey = ref(0)

const hideChart = computed(() => {
	return (
		!builder.chart.doc?.name ||
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
	await builder.chart.addToDashboard(toDashboard.value.value)
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
	<div class="flex flex-1 flex-col gap-4 overflow-hidden">
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
		<div v-else class="flex w-full flex-1 rounded border">
			<component
				v-if="builder.chart.doc.chart_type"
				ref="widget"
				:key="JSON.stringify(builder.chart.doc)"
				:is="widgets.getComponent(builder.chart.doc.chart_type)"
				:data="builder.chart.data"
				:options="builder.chart.doc.options"
			/>
		</div>
	</div>

	<PublicShareDialog
		v-if="builder.chart.doc.doctype && builder.chart.doc.name"
		v-model:show="showShareDialog"
		:resource-type="builder.chart.doc.doctype"
		:resource-name="builder.chart.doc.name"
		:allow-public-access="true"
		:isPublic="Boolean(builder.chart.doc.is_public)"
		@togglePublicAccess="builder.chart.togglePublicAccess"
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
