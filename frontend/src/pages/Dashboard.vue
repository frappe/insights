<template>
	<BasePage>
		<template #header>
			<div class="flex flex-1 justify-between">
				<h1 v-if="dashboard" class="text-3xl font-medium text-gray-900">
					{{ dashboard.title }}
				</h1>
				<div class="space-x-2">
					<Button
						icon="plus"
						appearance="white"
						title="Add Visualization"
						@click="showAddDialog = true"
					/>
					<Button
						icon="trash-2"
						appearance="white"
						title="Delete Dashboard"
						@click="showDeleteDialog = true"
					/>
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
					@remove="removeVisualization"
				/>
			</div>
		</template>
	</BasePage>

	<Dialog :options="{ title: 'Add Visualization' }" v-model="showAddDialog" :dismissable="true">
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
	<Dialog
		:options="{ title: 'Delete Query', icon: { name: 'trash', appearance: 'danger' } }"
		v-model="showDeleteDialog"
		:dismissable="true"
	>
		<template #body-content>
			<p class="text-base text-gray-600">Are you sure you want to delete this dashboard?</p>
		</template>
		<template #actions>
			<Button appearance="danger" @click="deleteDashboard" :loading="deletingDashboard">
				Yes
			</Button>
		</template>
	</Dialog>
</template>

<script setup>
import BasePage from '@/components/BasePage.vue'
import Autocomplete from '@/components/Autocomplete.vue'
import DashboardCard from '@/components/DashboardCard.vue'

import { useRouter } from 'vue-router'
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
		removeVisualization: 'remove_visualization',
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

const showAddDialog = ref(false)
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
	showAddDialog.value = false
}
const addingVisualization = computed(() => dashboardResource.addVisualization.loading)

const removeVisualization = (visualizationID) => {
	dashboardResource.removeVisualization.submit({
		visualization: visualizationID,
	})
}
const removingVisualization = computed(() => dashboardResource.removeVisualization.loading)

const router = useRouter()
const showDeleteDialog = ref(false)
const deletingDashboard = computed(() => dashboardResource.delete.loading)
const deleteDashboard = () => {
	dashboardResource.delete.submit()
	showDeleteDialog.value = false
	router.push('/dashboard')
}
</script>
