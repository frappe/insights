<template>
	<div v-if="chart.doc" class="flex flex-1 p-2 pt-3">
		<div
			class="-ml-1 flex w-full flex-shrink-0 flex-col space-y-4 overflow-y-scroll pl-1 lg:h-full lg:w-[18rem] lg:pr-4"
		>
			<!-- Widget Options -->
			<Input
				type="select"
				label="Chart Type"
				class="w-full"
				v-model="chart.doc.chart_type"
				:options="chartOptions"
			/>

			<component
				v-if="chart.doc.chart_type"
				:is="widgets.getOptionComponent(chart.doc.chart_type)"
				:key="chart.doc.chart_type"
				v-model="chart.doc.options"
				:columns="query.resultColumns"
			/>

			<Button variant="subtle" @click="chart.resetOptions()">Reset Options</Button>
		</div>

		<div
			class="relative flex h-full min-h-[30rem] w-full flex-1 flex-col space-y-3 overflow-hidden lg:w-auto"
		>
			<div class="ml-4 flex flex-shrink-0 space-x-2">
				<Button variant="outline" @click="showDashboardDialog = true">
					Add to Dashboard
				</Button>
				<Button variant="outline" @click="showShareDialog = true"> Share </Button>
			</div>
			<div class="flex-1">
				<component
					v-if="chart.doc.chart_type"
					ref="widget"
					:is="widgets.getComponent(chart.doc.chart_type)"
					:data="chart.data"
					:options="chart.doc.options"
					:key="JSON.stringify(chart.doc.options)"
				>
					<template #placeholder>
						<InvalidWidget
							class="absolute"
							title="Insufficient options"
							message="Please check the options for this chart"
							icon="settings"
							icon-class="text-gray-500"
						/>
					</template>
				</component>
			</div>
		</div>

		<PublicShareDialog
			v-if="chart.doc.doctype && chart.doc.name"
			v-model:show="showShareDialog"
			:resource-type="chart.doc.doctype"
			:resource-name="chart.doc.name"
			:allow-public-access="true"
			:isPublic="Boolean(chart.doc.is_public)"
			@togglePublicAccess="chart.togglePublicAccess"
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
	</div>
</template>

<script setup>
import PublicShareDialog from '@/components/PublicShareDialog.vue'
import useDashboards from '@/dashboard/useDashboards'
import InvalidWidget from '@/widgets/InvalidWidget.vue'
import widgets from '@/widgets/widgets'
import { computed, inject, ref, watch } from 'vue'
import useChart from './useChart'

const query = inject('query')
const showShareDialog = ref(false)
const chartOptions = [
	{
		label: 'Select a chart type',
		value: undefined,
	},
].concat(widgets.getChartOptions())

let chart = ref({})
query.get_chart_name.submit().then((res) => {
	chart.value = useChart(res.message)
	chart.value.enableAutoSave()
})

const showDashboardDialog = ref(false)
const dashboards = useDashboards()
dashboards.reload()
const toDashboard = ref(null)
const addingToDashboard = ref(false)
const dashboardOptions = computed(() => {
	// sort alphabetically
	return dashboards.list.map((d) => ({ label: d.title, value: d.name }))
})
const $notify = inject('$notify')
const addChartToDashboard = async () => {
	if (!toDashboard.value) return
	await chart.value.addToDashboard(toDashboard.value.value)
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
