<template>
	<BasePage>
		<template #header>
			<div class="flex flex-1 items-center justify-between">
				<h1 v-if="dashboard.doc" class="text-3xl font-medium text-gray-900">
					{{ dashboard.doc.title }}
				</h1>
				<div class="flex items-start space-x-2">
					<Button
						v-if="!dashboard.editingLayout"
						appearance="white"
						icon="refresh-ccw"
						@click="refreshVisualizations"
					/>
					<Button
						v-if="!dashboard.editingLayout"
						appearance="white"
						icon="edit"
						@click="() => (dashboard.editingLayout = true)"
					/>
					<Button
						v-if="dashboard.editingLayout"
						appearance="white"
						icon="plus"
						@click="() => (showAddDialog = true)"
					/>
					<Button
						v-if="!dashboard.editingLayout"
						appearance="white"
						icon="trash-2"
						@click="() => (showDeleteDialog = true)"
					/>
					<Button
						v-if="dashboard.editingLayout"
						appearance="danger"
						icon="x"
						@click="dashboard.editingLayout = false"
					/>
					<Button
						v-if="dashboard.editingLayout"
						appearance="primary"
						icon="check"
						@click="updateLayout"
					/>
				</div>
			</div>
		</template>
		<template #main>
			<div
				v-if="visualizations && visualizations.length > 0"
				class="mt-2 h-full w-full overflow-scroll"
				:class="{
					'blur-[4px]': refreshing,
					'rounded-md bg-slate-50 shadow-inner': dashboard.editingLayout,
				}"
				@click="() => (refreshing ? $event.stopPropagation() : null)"
			>
				<DraggableResizeable
					:enabled="dashboard.editingLayout"
					:items="visualizations"
					@sort="updateOrder"
					@resize="updateSize"
				>
					<template #item="{ item: visualization }">
						<DashboardCard
							:visualizationID="visualization.id"
							:queryID="visualization.query"
							@edit="editVisualization"
							@remove="removeVisualization"
						/>
					</template>
				</DraggableResizeable>
			</div>
			<div v-else class="flex flex-1 flex-col items-center justify-center space-y-1">
				<div class="text-base font-light text-gray-500">
					You haven't added any visualizations.
				</div>
				<div
					class="cursor-pointer text-sm font-light text-blue-500 hover:underline"
					@click="showAddDialog = true"
				>
					Add one?
				</div>
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
import BasePage from '@/components/BasePage.vue'
import Autocomplete from '@/components/Controls/Autocomplete.vue'
import DashboardCard from '@/components/Dashboard/DashboardCard.vue'

import { useRouter } from 'vue-router'
import { computed, ref, provide, reactive, watch } from 'vue'
import useDashboard from '@/utils/dashboard'
import { updateDocumentTitle } from '@/utils'

import DraggableResizeable from '@/components/DraggableResizeable.vue'

const props = defineProps({
	name: {
		type: String,
		required: true,
	},
})

const dashboard = useDashboard(props.name)
provide('dashboard', dashboard)

const visualizations = computed(() => {
	return dashboard.doc?.visualizations.map((v) => {
		return {
			id: v.visualization,
			...v,
		}
	})
})

const showAddDialog = ref(false)
const newVisualization = ref({})

const addVisualization = () => {
	dashboard.addVisualization
		.submit({
			visualization: newVisualization.value.value,
		})
		.then(() => {
			newVisualization.value = {}
			showAddDialog.value = false
			dashboard.updateNewVisualizationOptions()
		})
}
const addingVisualization = computed(() => dashboard.addVisualization.loading)

const removeVisualization = (visualizationID) => {
	dashboard.removeVisualization
		.submit({
			visualization: visualizationID,
		})
		.then(() => {
			dashboard.updateNewVisualizationOptions()
		})
}

const router = useRouter()
const showDeleteDialog = ref(false)
const deletingDashboard = computed(() => dashboard.delete.loading)
const deleteDashboard = () => {
	dashboard.delete.submit().then(() => {
		showDeleteDialog.value = false
		router.push('/dashboard')
	})
}

const editVisualization = (queryID) => {
	window.open(`/insights/query/${queryID}`, '_blank')
}

const refreshing = ref(false)
const refreshVisualizations = async () => {
	refreshing.value = true
	// hack: update the visualizations
	await dashboard.refreshVisualizations.submit()
	// then reload the dashboard doc
	// to re-render the visualizations with new data
	dashboard.doc.visualizations = []
	await dashboard.reload()
	refreshing.value = false
}

const updatedLayout = reactive({
	moved: [],
	resized: [],
})

const updateOrder = ({ oldIndex, newIndex }) => {
	updatedLayout['moved'].push({
		from_index: oldIndex,
		to_index: newIndex,
	})
}

const updateSize = ({ name, width, height }) => {
	updatedLayout['resized'].push({ name, width, height })
}
const updateLayout = () => {
	dashboard.updateLayout.submit({
		updated_layout: updatedLayout,
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
