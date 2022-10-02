<template>
	<BasePage>
		<template #header>
			<DashboardHeader
				@addChart="() => (showAddDialog = true)"
				@commitLayout="commitLayout"
			/>
		</template>
		<template #main>
			<div
				v-if="visualizations && visualizations.length > 0"
				class="-mx-1 h-full w-full overflow-scroll pt-1"
				:class="{
					'blur-[4px]': dashboard.refreshing,
					'rounded-md bg-slate-50 shadow-inner': dashboard.editingLayout,
				}"
			>
				<GridLayout
					:items="visualizations"
					itemKey="name"
					@layoutChange="updateLayout"
					:disabled="!dashboard.editingLayout"
					:options="{
						float: true,
						margin: 4,
						column: 20,
						cellHeight: 30,
					}"
				>
					<template #item="{ item }">
						<DashboardCard
							:visualizationID="item.visualizationID"
							:queryID="item.query"
							@edit="editVisualization"
							@remove="removeVisualization"
						/>
					</template>
				</GridLayout>
			</div>
			<div
				v-if="visualizations && visualizations.length == 0"
				class="flex flex-1 flex-col items-center justify-center space-y-1"
			>
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
</template>

<script setup>
import BasePage from '@/components/BasePage.vue'
import Autocomplete from '@/components/Controls/Autocomplete.vue'
import DashboardHeader from '@/components/Dashboard/DashboardHeader.vue'
import DashboardCard from '@/components/Dashboard/DashboardCard.vue'

import { computed, ref, provide, reactive, watch } from 'vue'
import useDashboard from '@/utils/dashboard'
import { updateDocumentTitle } from '@/utils'

import GridLayout from '@/components/Dashboard/GridLayout.vue'
import { safeJSONParse } from '@/utils'

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
		const layout = safeJSONParse(v.layout, {})
		return {
			...v,
			...layout,
			visualizationID: v.visualization,
		}
	})
)

const updatedLayout = reactive({})
const updateLayout = (changedItems) => {
	changedItems.forEach((item) => {
		const name = item.id
		delete item.id
		updatedLayout[name] = item
	})
}

const commitLayout = () => {
	dashboard.updateLayout.submit({
		updated_layout: updatedLayout,
	})
	dashboard.editingLayout = false
}

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

const editVisualization = (queryID) => {
	window.open(`/insights/query/${queryID}`, '_blank')
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
