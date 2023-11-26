<template>
	<header class="sticky top-0 z-10 flex items-center justify-between bg-white px-5 py-2.5">
		<PageBreadcrumbs
			class="h-7"
			:items="[
				{ label: 'Data Sources', route: { path: '/data-source' } },
				{ label: dataSource.doc.title },
			]"
		/>
	</header>

	<ListView
		:columns="[
			{ label: 'Table', name: 'label' },
			{ label: 'Status', name: 'status' },
		]"
		:rows="dataSource.tableList.filter((table) => !table.is_query_based)"
	>
		<template #actions>
			<Button
				variant="outline"
				iconLeft="link-2"
				@click="$router.push(`/data-source/${dataSource.doc.name}/relationships`)"
			>
				Manage Relationships
			</Button>
			<Dropdown
				placement="left"
				:button="{ icon: 'more-horizontal', variant: 'outline' }"
				:options="dropdownActions"
			/>
		</template>

		<template #list-row="{ row: table }">
			<ListRow
				as="router-link"
				:row="table"
				:to="{
					name: 'DataSourceTable',
					params: { name: dataSource.doc.name, table: table.name },
				}"
			>
				<ListRowItem> {{ table.label }} </ListRowItem>
				<ListRowItem class="space-x-2">
					<IndicatorIcon :class="table.hidden ? 'text-gray-500' : 'text-green-500'" />
					<span> {{ table.hidden ? 'Disabled' : 'Enabled' }} </span>
				</ListRowItem>
			</ListRow>
		</template>

		<template #emptyState>
			<div class="text-xl font-medium">No tables.</div>
			<div class="mt-1 text-base text-gray-600">No tables to display.</div>
			<Button class="mt-4" label="Sync Tables" variant="solid" @click="syncTables" />
		</template>
	</ListView>

	<Dialog
		v-model="showDeleteDialog"
		:dismissable="true"
		:options="{
			title: 'Delete Data Source',
			message: 'Are you sure you want to delete this data source?',
			icon: { name: 'trash', appearance: 'danger' },
			actions: [
				{
					label: 'Delete',
					variant: 'solid',
					theme: 'red',
					onClick: async () => {
						await dataSource.delete()
						router.push({ name: 'DataSourceList' })
					},
				},
			],
		}"
	>
	</Dialog>
</template>

<script setup lang="jsx">
import IndicatorIcon from '@/components/Icons/IndicatorIcon.vue'
import ListView from '@/components/ListView.vue'
import PageBreadcrumbs from '@/components/PageBreadcrumbs.vue'
import { ListRow, ListRowItem } from 'frappe-ui'
import { computed, inject, provide, ref } from 'vue'
import { useRouter } from 'vue-router'
import useDataSource from './useDataSource'

const props = defineProps({
	name: {
		type: String,
		required: true,
	},
})

const router = useRouter()
const dataSource = useDataSource(props.name)
provide('dataSource', dataSource)
dataSource.fetchTables()

const searchQuery = ref('')
const filteredList = computed(() => {
	if (!searchQuery.value) {
		return dataSource.tableList.filter((table) => !table.is_query_based)
	}
	return dataSource.tableList.filter(
		(table) =>
			!table.is_query_based &&
			table.label.toLowerCase().includes(searchQuery.value.toLowerCase())
	)
})

const showDeleteDialog = ref(false)
const dropdownActions = computed(() => {
	return [
		{
			label: 'Sync Tables',
			icon: 'refresh-cw',
			onClick: syncTables,
		},
		{
			label: 'Delete',
			icon: 'trash',
			onClick: () => (showDeleteDialog.value = true),
		},
	]
})

const $notify = inject('$notify')
function syncTables() {
	dataSource
		.syncTables()
		.catch((err) => $notify({ title: 'Error Syncing Tables', variant: 'error' }))
}
</script>
