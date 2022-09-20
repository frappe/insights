<template>
	<div class="flex h-full items-start pt-2">
		<div class="flex h-full w-[18rem] flex-col pr-4">
			<div class="mb-3">
				<div class="mb-2 text-sm tracking-wide text-gray-600">CHART TYPE</div>
				<ChartSelector
					v-if="types?.length > 0"
					:chartTypes="types"
					:invalidTypes="invalidTypes"
					:currentType="visualization.type"
					@chartTypeChange="setVizType"
				/>
			</div>

			<div class="flex-1 space-y-3 overflow-y-scroll">
				<div class="mb-2 text-sm tracking-wide text-gray-600">CHART OPTIONS</div>
				<ChartOptions :chartType="visualization.type" />
			</div>
		</div>
		<div class="flex h-full w-[calc(100%-18rem)] flex-col space-y-4">
			<div class="flex space-x-2">
				<Button
					appearance="white"
					@click="showDashboardDialog = true"
					:disabled="visualization.isDirty"
				>
					Add to Dashboard
				</Button>
				<Button
					appearance="primary"
					@click="saveVisualization"
					:loading="visualization.savingDoc"
					:disabled="!visualization.isDirty"
				>
					Save
				</Button>
			</div>
			<div class="max-h-[30rem] flex-1 rounded-md border p-4">
				<component
					v-if="visualization.component && visualization.componentProps"
					:is="visualization.component"
					v-bind="visualization.componentProps"
				></component>
			</div>
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
import ChartSelector from '@/components/Query/Visualization/ChartSelector.vue'
import ChartOptions from '@/components/Query/Visualization/ChartOptions.vue'

import { computed, inject, nextTick, provide, ref, watch } from 'vue'
import { useVisualization, types } from '@/utils/visualizations'

import Autocomplete from '@/components/Controls/Autocomplete.vue'
import { getDashboardOptions, createDashboard } from '@/utils/dashboard.js'

const query = inject('query')
const visualizationID = query.visualizations[0]
const visualization = useVisualization({ visualizationID, query })
provide('visualization', visualization)

const invalidTypes = computed(() => {
	// TODO: change based on data
	return ['Funnel', 'Row']
})
const setVizType = (type) => {
	if (!invalidTypes.value.includes(type)) {
		visualization.setType(type)
	}
}

const $notify = inject('$notify')
const saveVisualization = () => {
	const onSuccess = () => {
		$notify({
			title: 'Visualization Saved',
			appearance: 'success',
		})
	}
	visualization.updateDoc({ onSuccess })
}

const showDashboardDialog = ref(false)
const toDashboard = ref(null)
const dashboardOptions = ref([])
const $autocomplete = ref(null)
watch(showDashboardDialog, async (val) => {
	if (val) {
		await nextTick()
		getDashboardOptions(visualizationID).then((options) => {
			dashboardOptions.value = options
			setTimeout(() => {
				$autocomplete.value.input.$el.blur()
				$autocomplete.value.input.$el.focus()
			}, 500)
		})
	}
})
const addingToDashboard = computed(() => visualization.addToDashboard?.loading)
function addToDashboard() {
	const onSuccess = () => {
		$notify({
			title: 'Visualization Added to Dashboard',
			appearance: 'success',
		})
		showDashboardDialog.value = false
	}
	// TODO: move default dimensions to insights_dashboard.py
	const defaultDimensions = visualization.type == 'Number' ? { w: 4, h: 4 } : { w: 8, h: 8 }
	const dashboardName = toDashboard.value.value
	visualization.addToDashboard(dashboardName, defaultDimensions, { onSuccess })
}

function _createDashboard(newDashboardName) {
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
</script>
