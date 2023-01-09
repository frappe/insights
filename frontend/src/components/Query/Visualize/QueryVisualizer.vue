<template>
	<div
		class="flex flex-1 flex-col items-start space-y-4 overflow-scroll pt-2 scrollbar-hide lg:flex-row lg:space-y-0 lg:overflow-hidden"
	>
		<div
			class="flex w-full flex-shrink-0 flex-col overflow-hidden lg:h-full lg:w-[18rem] lg:pr-4"
		>
			<div class="mb-3 flex-shrink-0">
				<div class="mb-2 text-sm tracking-wide text-gray-600">CHART TYPE</div>
				<ChartSelector
					v-if="types?.length > 0"
					:chartTypes="types"
					:invalidTypes="invalidTypes"
					:currentType="chart.type"
					@chartTypeChange="setVizType"
				/>
			</div>

			<div class="flex flex-1 flex-col overflow-hidden">
				<div class="mb-2 text-sm tracking-wide text-gray-600">CHART OPTIONS</div>
				<ChartOptions :chartType="chart.type" />
			</div>
		</div>

		<div
			class="flex h-full min-h-[30rem] w-full flex-1 flex-col space-y-3 overflow-hidden lg:w-auto"
			v-if="chart.component && chart.componentProps"
		>
			<div class="flex flex-shrink-0 space-x-2">
				<Button
					appearance="white"
					@click="showDashboardDialog = true"
					iconLeft="bookmark"
					:disabled="chart.isDirty"
				>
					Add to Dashboard
				</Button>
				<Button
					v-if="canDownload"
					appearance="white"
					iconLeft="download"
					:disabled="chart.isDirty"
					@click="downloadChart()"
				>
					Download
				</Button>

				<Button
					appearance="primary"
					@click="saveChart"
					:loading="chart.savingDoc"
					:disabled="!chart.isDirty"
				>
					Save
				</Button>
			</div>
			<div class="flex flex-1 flex-col items-center justify-center overflow-hidden">
				<component
					ref="eChart"
					:is="chart.component"
					v-bind="chart.componentProps"
				></component>
			</div>
		</div>

		<div v-else class="flex h-full w-full flex-1 flex-col items-center justify-center">
			<div class="text-sm text-gray-500">No chart to display</div>
		</div>
	</div>

	<Dialog
		:options="{ title: 'Add to Dashboard' }"
		v-model="showDashboardDialog"
		:dismissable="true"
	>
		<template #body-content>
			<div class="space-y-2 text-gray-600">
				<div class="text-sm font-light text-gray-500">Select a Dashboard</div>
				<Autocomplete
					ref="$autocomplete"
					placeholder="Select a dashboard"
					v-model="toDashboard"
					:options="dashboardOptions"
					:allowCreate="true"
					@createOption="(option) => _createDashboard(option)"
				/>
			</div>
		</template>
		<template #actions>
			<Button appearance="primary" @click="addToDashboard" :loading="addingToDashboard">
				Add
			</Button>
		</template>
	</Dialog>
</template>

<script setup>
import ChartSelector from '@/components/Query/Visualize/ChartSelector.vue'
import ChartOptions from '@/components/Query/Visualize/ChartOptions.vue'

import { computed, inject, nextTick, provide, ref, watch } from 'vue'
import { useChart, types } from '@/utils/charts'
import { useRouter } from 'vue-router'

import Autocomplete from '@/components/Controls/Autocomplete.vue'
import { getDashboardOptions, createDashboard } from '@/utils/dashboard.js'

const query = inject('query')
const chartName = query.charts[0]
const chart = useChart({
	chartID: chartName,
	data: query.results.formattedResult,
})
provide('chart', chart)

const invalidTypes = computed(() => {
	// TODO: change based on data
	return ['Funnel', 'Row']
})
const setVizType = (type) => {
	if (!invalidTypes.value.includes(type)) {
		chart.setType(type)
	}
}

const $notify = inject('$notify')
const saveChart = () => {
	const onSuccess = () => {
		$notify({
			title: 'Chart Saved',
			appearance: 'success',
		})
	}
	chart.updateDoc({ onSuccess })
}

const showDashboardDialog = ref(false)
const toDashboard = ref({})
const dashboardOptions = ref([])
const $autocomplete = ref(null)
watch(showDashboardDialog, async (val) => {
	if (val) {
		await nextTick()
		getDashboardOptions(chartName).then((options) => {
			dashboardOptions.value = options
			setTimeout(() => {
				$autocomplete.value.input.$el.blur()
				$autocomplete.value.input.$el.focus()
			}, 500)
		})
	}
})
const addingToDashboard = computed(() => chart.addToDashboard?.loading)
function addToDashboard() {
	const dashboardName = toDashboard.value.value
	chart.addToDashboard(dashboardName).then(() => {
		$notify({
			title: 'Chart Added to Dashboard',
			appearance: 'success',
		})
		showDashboardDialog.value = false
	})
}

const router = useRouter()
function _createDashboard(newDashboardName) {
	if (!newDashboardName) return router.push('/dashboard')
	createDashboard(newDashboardName).then(({ name, title }) => {
		if (name && title) {
			$notify({
				title: 'Dashboard Created',
				appearance: 'success',
			})
			showDashboardDialog.value = false
			toDashboard.value = {
				value: name,
				label: title,
			}
			addToDashboard()
		}
	})
}

const eChart = ref(null)
const canDownload = computed(() => {
	return eChart.value?.$refs?.eChart?.downloadChart
})
function downloadChart() {
	if (canDownload.value) {
		eChart.value.$refs.eChart.downloadChart()
	}
}
</script>
