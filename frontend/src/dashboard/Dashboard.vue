<template>
	<BasePage>
		<template #header>
			<DashboardHeader
				@addChart="() => (showAddDialog = true)"
				@saveLayout="saveLayout"
				@autoLayout="autoLayout"
			/>
		</template>
		<template #main>
			<div
				v-if="dashboard.items && dashboard.items.length > 0"
				class="-mx-1 h-full w-full overflow-scroll pt-1"
				:class="{
					'blur-[4px]': dashboard.refreshing,
					'rounded-md bg-slate-50 shadow-inner': dashboard.editingLayout,
				}"
			>
				<GridLayout
					ref="gridLayout"
					itemKey="name"
					:items="dashboard.items"
					@layoutChange="dashboard.updateLayout"
					:disabled="!dashboard.editingLayout"
					:options="{
						float: true,
						margin: 4,
						column: 20,
						cellHeight: 30,
					}"
				>
					<template #item="{ item }">
						<DashboardItem :item="item" />
					</template>
				</GridLayout>
			</div>
			<div
				v-if="dashboard.items && dashboard.items.length == 0"
				class="flex flex-1 flex-col items-center justify-center space-y-1"
			>
				<div class="text-base font-light text-gray-500">You haven't added any charts.</div>
				<div
					class="cursor-pointer text-sm font-light text-blue-500 hover:underline"
					@click="showAddDialog = true"
				>
					Add one?
				</div>
			</div>
		</template>
	</BasePage>

	<Dialog :options="{ title: 'Add an item' }" v-model="showAddDialog" :dismissable="true">
		<template #body-content>
			<div class="space-y-4">
				<Tabs
					:tabs="addItemTabs"
					@switch="
						(tab) => {
							newItem.item_type = tab.label
						}
					"
				/>
				<Autocomplete
					v-if="newItem.item_type == 'Chart'"
					ref="autocomplete"
					placeholder="Select a chart"
					v-model="newChart"
					:options="dashboard.newChartOptions"
				/>

				<DashboardFilterForm v-if="newItem.item_type == 'Filter'" v-model="newItem" />
			</div>
		</template>
		<template #actions>
			<Button appearance="primary" @click="addItem" :loading="dashboard.add_item.loading">
				Add
			</Button>
		</template>
	</Dialog>
</template>

<script setup>
import BasePage from '@/components/BasePage.vue'
import Autocomplete from '@/components/Controls/Autocomplete.vue'
import DashboardHeader from '@/dashboard/DashboardHeader.vue'
import DashboardItem from '@/dashboard/DashboardItem.vue'
import GridLayout from '@/dashboard/GridLayout.vue'
import Tabs from '@/components/Tabs.vue'
import DashboardFilterForm from './DashboardFilterForm.vue'

import { computed, ref, provide, watch } from 'vue'
import { updateDocumentTitle } from '@/utils'
import useDashboard from '@/dashboard/useDashboard'

const props = defineProps({
	name: {
		type: String,
		required: true,
	},
})

const dashboard = useDashboard(props.name)
provide('dashboard', dashboard)

const showAddDialog = ref(false)
const newItem = ref({
	item_type: 'Chart',
	chart: null,
	filter_label: '',
	filter_type: 'String', // default
	filter_operator: 'equals', // default
})

const autocomplete = ref(null)
watch(showAddDialog, (show) => {
	if (show) {
		setTimeout(() => {
			autocomplete.value?.input.$el.blur()
			autocomplete.value?.input.$el.focus()
		}, 400)
	}
})

const addItemTabs = ref([
	{
		label: 'Chart',
		active: true,
	},
	{
		label: 'Filter',
		active: false,
	},
])
watch(
	() => newItem.value.item_type,
	(type) => {
		addItemTabs.value.forEach((tab) => {
			tab.active = tab.label == type
		})
	},
	{ immediate: true }
)

const newChart = ref({})
watch(newChart, (chart) => chart && (newItem.value.chart = chart.value))

function addItem() {
	if (newItem.value.item_type == 'Chart') {
		dashboard.addItem({
			item_type: 'Chart',
			chart: newItem.value.chart,
		})
	} else {
		dashboard.addItem({
			item_type: 'Filter',
			filter_label: newItem.value.filter_label,
			filter_type: newItem.value.filter_type,
			filter_operator: newItem.value.filter_operator,
		})
	}
	showAddDialog.value = false
	newItem.value = {
		item_type: 'Chart',
		chart: null,
		filter_label: '',
		filter_type: 'String', // default
		filter_operator: 'equals', // default
	}
	newChart.value = {}
}

const gridLayout = ref(null)
function saveLayout() {
	dashboard.saveLayout(gridLayout.value.grid.save(false))
}
async function autoLayout() {
	gridLayout.value.grid.compact()
	console.log(gridLayout.value.grid.getGridItems())
}

const pageMeta = computed(() => {
	return {
		title: props.name,
		subtitle: 'Dashboard',
	}
})
updateDocumentTitle(pageMeta)
</script>
