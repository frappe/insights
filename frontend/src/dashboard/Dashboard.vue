<template>
	<BasePage>
		<template #header>
			<DashboardHeader
				@addChart="() => (showAddDialog = true)"
				@commitLayout="dashboard.commitLayout"
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
					:items="dashboard.items"
					itemKey="name"
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
							addItemTabs.forEach((t) => {
								t.active = t.label === tab.label
							})
							newItem.item_type = tab.label
						}
					"
				/>
				<Autocomplete
					v-if="newItemType == 'Chart'"
					ref="autocomplete"
					placeholder="Select a chart"
					v-model="newItem"
					:options="dashboard.newChartOptions"
				/>

				<DashboardFilterForm v-if="newItemType == 'Filter'" v-model="newItem" />
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
			autocomplete.value.input.$el.blur()
			autocomplete.value.input.$el.focus()
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
const newItemType = computed(() => {
	return addItemTabs.value.find((t) => t.active).label
})

function addItem() {
	if (newItemType.value == 'Chart') {
		dashboard.addItem({
			item_type: 'Chart',
			chart: newItem.value.value,
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
}

const pageMeta = computed(() => {
	return {
		title: props.name,
		subtitle: 'Dashboard',
	}
})
updateDocumentTitle(pageMeta)
</script>
