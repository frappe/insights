<template>
	<BasePage>
		<template #header>
			<div class="flex flex-1 justify-between">
				<h1 v-if="dashboard.doc" class="text-3xl font-medium text-gray-900">
					{{ dashboard.doc.title }}
				</h1>
				<div class="flex items-start space-x-2">
					<Button
						v-if="dashboard.editingLayout"
						appearance="white"
						@click="dashboard.editingLayout = false"
					>
						Discard
					</Button>
					<Button
						v-if="dashboard.editingLayout"
						appearance="primary"
						@click="updateLayout"
					>
						Done
					</Button>
					<Dropdown
						placement="right"
						:button="{ icon: 'more-horizontal', appearance: 'white' }"
						:options="[
							{
								label: 'Refresh',
								icon: 'refresh-ccw',
								handler: refreshVisualizations,
							},
							{
								label: 'Edit Layout',
								icon: 'edit',
								handler: () => (dashboard.editingLayout = true),
							},
							{
								label: 'Add Visualization',
								icon: 'plus',
								handler: () => (showAddDialog = true),
							},
							{
								label: 'Delete',
								icon: 'trash-2',
								handler: () => (showDeleteDialog = true),
							},
						]"
					/>
				</div>
			</div>
		</template>
		<template #main>
			<div
				id="dashboard-container"
				class="relative mt-1 flex h-full w-full flex-wrap overflow-scroll scrollbar-hide"
				:class="{
					'blur-[4px]': refreshing,
					'rounded-md bg-slate-50 shadow-inner': dashboard.editingLayout,
				}"
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
					@layoutChange="updateVisualizationLayout"
				/>
			</div>
		</template>
	</BasePage>

	<Dialog :options="{ title: 'Add Visualization' }" v-model="showAddDialog" :dismissable="true">
		<template #body-content>
			<div class="space-y-4">
				<Autocomplete
					ref="autocomplete"
					placeholder="Select a visualization"
					v-model="newVisualization"
					:options="dashboard.newVisualizationOptions"
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
import { Dropdown } from 'frappe-ui'
import BasePage from '@/components/BasePage.vue'
import Autocomplete from '@/components/Controls/Autocomplete.vue'
import DashboardCard from '@/components/Dashboard/DashboardCard.vue'

import { useRouter } from 'vue-router'
import { computed, ref, provide, reactive, watch } from 'vue'
import useDashboard from '@/utils/dashboard'
import { updateDocumentTitle } from '@/utils'

const props = defineProps({
	name: {
		type: String,
		required: true,
	},
})

const dashboard = useDashboard(props.name)
provide('dashboard', dashboard)

const visualizations = computed(() =>
	dashboard.doc?.visualizations.map((v) => {
		return {
			query: v.query,
			id: v.visualization,
		}
	})
)

const showAddDialog = ref(false)
const newVisualization = ref({})

const addVisualization = () => {
	dashboard.addVisualization.submit({
		visualization: newVisualization.value.value,
	})
	newVisualization.value = {}
	showAddDialog.value = false
}
const addingVisualization = computed(() => dashboard.addVisualization.loading)

const removeVisualization = (visualizationID) => {
	dashboard.removeVisualization.submit({
		visualization: visualizationID,
	})
}

const router = useRouter()
const showDeleteDialog = ref(false)
const deletingDashboard = computed(() => dashboard.delete.loading)
const deleteDashboard = () => {
	dashboard.delete.submit()
	showDeleteDialog.value = false
	router.push('/dashboard')
}

const editVisualization = (queryID) => {
	window.open(`/insights/query/${queryID}`, '_blank')
}

const refreshing = computed(() => dashboard.refreshVisualizations.loading)
const refreshVisualizations = () => {
	dashboard.refreshVisualizations.submit()
}

const updatedLayouts = reactive({})
const updateVisualizationLayout = (id, layout) => {
	updatedLayouts[id] = layout

	dashboard.doc?.visualizations.some((v) => {
		if (v.visualization === id) {
			v.layout = JSON.stringify(layout)
			return true
		}
	})
}
const updateLayout = () => {
	dashboard.updateLayout.submit({
		visualizations: updatedLayouts,
	})
	dashboard.editingLayout = false
}

const autocomplete = ref(null)
watch(showAddDialog, (show) => {
	if (show) {
		setTimeout(() => {
			autocomplete.value.input.$el.blur()
			autocomplete.value.input.$el.focus()
		}, 400)
	}
})

const pageMeta = computed(() => {
	return {
		title: dashboard.doc?.name,
		subtitle: 'Dashboard',
	}
})
updateDocumentTitle(pageMeta)
</script>
