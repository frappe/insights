<template>
	<BasePage>
		<template #header>
			<div class="flex flex-1 justify-between">
				<h1 v-if="dashboard" class="text-3xl font-medium text-gray-900">
					{{ dashboard.title }}
				</h1>
				<div class="space-x-2">
					<Button
						iconLeft="refresh-ccw"
						appearance="white"
						title="Refresh Dashboard"
						@click="refreshVisualizations"
						:loading="refreshing"
					>
						Refresh
					</Button>
					<Button
						iconLeft="plus"
						appearance="white"
						title="Add Visualization"
						@click="showAddDialog = true"
					>
						Add
					</Button>
					<Button
						iconLeft="trash-2"
						appearance="white"
						title="Delete Dashboard"
						@click="showDeleteDialog = true"
					>
						Delete
					</Button>
				</div>
			</div>
		</template>
		<template #main>
			<div
				id="dashboard-container"
				class="relative flex h-full w-full flex-wrap overflow-scroll rounded-md bg-slate-50 shadow-inner scrollbar-hide"
				:class="{ 'blur-[4px]': refreshing }"
				@click="() => (refreshing ? $event.stopPropagation() : null)"
				v-if="visualizations"
			>
				<DashboardCard
					v-for="visualization in visualizations"
					parentID="dashboard-container"
					:key="visualization.id"
					:visualizationID="visualization.id"
					:queryID="visualization.query"
					@edit="editVisualization"
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
import Autocomplete from '@/components/Controls/Autocomplete.vue'
import DashboardCard from '@/components/Dashboard/DashboardCard.vue'

import { useRouter } from 'vue-router'
import { computed, ref, provide } from 'vue'
import { createDocumentResource } from 'frappe-ui'
import { updateDocumentTitle } from '@/utils'

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
		refreshVisualizations: 'refresh_visualizations',
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
	newVisualization.value = {}
	showAddDialog.value = false
}
const addingVisualization = computed(() => dashboardResource.addVisualization.loading)

const removeVisualization = (visualizationID) => {
	dashboardResource.removeVisualization.submit({
		visualization: visualizationID,
	})
}

const router = useRouter()
const showDeleteDialog = ref(false)
const deletingDashboard = computed(() => dashboardResource.delete.loading)
const deleteDashboard = () => {
	dashboardResource.delete.submit()
	showDeleteDialog.value = false
	router.push('/dashboard')
}

const editVisualization = (queryID) => {
	router.push(`/query/${queryID}`)
}

const refreshing = computed(() => dashboardResource.refreshVisualizations.loading)
const refreshVisualizations = () => {
	dashboardResource.refreshVisualizations.submit()
}

const pageMeta = computed(() => {
	return {
		title: dashboard.value?.name,
		subtitle: 'Dashboard',
	}
})
updateDocumentTitle(pageMeta)
</script>
