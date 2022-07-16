<template>
	<BasePage>
		<template #header>
			<div class="flex flex-1 justify-between">
				<h1 v-if="dashboard" class="text-3xl font-medium text-gray-900">
					{{ dashboard.title }}
				</h1>
				<div>
					<Button appearance="primary" @click="showDialog = true" :disabled="showDialog">
						+ Add
					</Button>
				</div>
			</div>
		</template>
		<template #main>
			<div
				id="dashboard-container"
				class="relative flex h-full w-full flex-wrap overflow-scroll rounded-md bg-slate-50 shadow-inner"
			>
				<DashboardCard
					v-if="visualizations"
					v-for="visualization in visualizations"
					parentID="dashboard-container"
					:key="visualization.id"
					:visualizationID="visualization.id"
					:queryID="visualization.query"
				/>
			</div>
		</template>
	</BasePage>

	<Dialog :options="{ title: 'Add Visualization' }" v-model="showDialog">
		<template #body-content>
			<div class="space-y-4">
				<Autocomplete
					placeholder="Select a visualization"
					v-model="newVisualization"
					:options="newVisualizations"
				/>
			</div>
		</template>
		<template #actions>
			<Button appearance="primary" @click="addVisualization" :loading="addingVisualization">
				Add
			</Button>
		</template>
	</Dialog>
</template>

<script setup>
import BasePage from '@/components/BasePage.vue'
import Autocomplete from '@/components/Autocomplete.vue'
import DashboardCard from '@/components/DashboardCard.vue'
import { computed, ref, provide } from 'vue'

import { createDocumentResource } from 'frappe-ui'

const props = defineProps({
	name: {
		type: String,
		required: true,
	},
})

const dashboardResource = createDocumentResource({
	doctype: 'Insights Dashboard',
	name: props.name,
	whitelistedMethods: {
		addVisualization: 'add_visualization',
		getVisualizations: 'get_visualizations',
		updateVisualizationLayout: 'update_visualization_layout',
	},
})
provide('dashboard', dashboardResource)
dashboardResource.getVisualizations.submit()
const dashboard = computed(() => dashboardResource.doc)

const visualizations = computed(() =>
	dashboard.value?.visualizations.map((v) => {
		return {
			query: v.query,
			id: v.visualization,
		}
	})
)

const showDialog = ref(false)
const newVisualization = ref({})
const newVisualizations = computed(() =>
	dashboardResource.getVisualizations.data?.message?.map((v) => {
		return {
			value: v.name,
			label: v.title,
			description: v.type,
		}
	})
)
const addVisualization = () => {
	dashboardResource.addVisualization.submit({
		visualization: newVisualization.value.value,
	})
	showDialog.value = false
}
const addingVisualization = computed(() => dashboardResource.addVisualization.loading)
</script>
