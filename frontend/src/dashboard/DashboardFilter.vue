<script setup>
import { Dialog } from 'frappe-ui'
import DashboardFilterForm from './DashboardFilterForm.vue'

import { inject, reactive, ref } from 'vue'
import SimpleFilter from '../components/SimpleFilter.vue'

const props = defineProps({ item: Object })

const filter = reactive({
	filter_label: props.item.filter_label || '',
	filter_column: props.item.filter_column || {},
	filter_links: props.item.filter_links || {},
	filter_state: props.item.filter_state || {},
})

const dashboard = inject('dashboard')
function saveFilterState(state) {
	dashboard.update_filter_state
		.submit({
			filter_name: props.item.name,
			filter_state: state
				? {
						column: state.column,
						operator: state.operator,
						value: state.value,
				  }
				: {},
		})
		.then(dashboard.refreshItems)
		.catch((e) => {
			console.error(e)
		})
}

const showEditFilterDialog = ref(false)
function editFilter() {
	dashboard.update_filter
		.submit({
			filter: {
				name: props.item.name,
				...filter,
			},
		})
		.then(dashboard.refreshItems)
		.catch((e) => {
			console.error(e)
		})
	showEditFilterDialog.value = false
}
</script>

<template>
	<div class="flex h-full w-full items-center">
		<teleport :to="`#dashboard-item-actions-${item.name}`">
			<Button
				v-if="dashboard.editingLayout"
				appearance="minimal"
				@click.prevent.stop="showEditFilterDialog = true"
				iconLeft="settings"
				class="!text-sm"
			>
				Edit
			</Button>
		</teleport>

		<SimpleFilter
			:disable-columns="true"
			:label="filter.filter_label"
			:column="filter.filter_column"
			:operator="filter.filter_state.operator"
			:value="filter.filter_state.value"
			@apply="saveFilterState"
			@reset="saveFilterState"
		></SimpleFilter>
	</div>

	<Dialog :options="{ title: 'Edit Filter' }" v-model="showEditFilterDialog" :dismissable="true">
		<template #body-content>
			<DashboardFilterForm v-model="filter" />
		</template>
		<template #actions>
			<Button appearance="primary" @click="editFilter"> Done </Button>
		</template>
	</Dialog>
</template>
