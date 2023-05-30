<template>
	<div class="h-full w-full bg-white px-8 py-4">
		<List
			v-if="dataSource.doc && dataSource.tables.length"
			:columns="columns"
			:data="dataSource.tables.filter((t) => !t.is_query_based)"
			:rowClick="
				({ name }) =>
					router.push({
						name: 'DataSourceTable',
						params: { name: dataSource.doc.name, table: name },
					})
			"
		>
			<template #title>
				<div class="flex items-center space-x-4">
					<div class="text-3xl font-medium text-gray-900">{{ dataSource.doc.title }}</div>
					<Badge color="green" class="h-fit">Active</Badge>
					<Dropdown
						placement="left"
						:button="{ icon: 'more-horizontal', appearance: 'minimal' }"
						:options="dropdownActions"
					/>
				</div>
			</template>
			<template #empty-state>
				<div
					v-if="dataSource.tables.length !== 0"
					class="mt-2 flex h-full w-full flex-col items-center justify-center rounded-md text-base font-light text-gray-500"
				>
					<div class="text-base font-light text-gray-500">Tables are not synced yet.</div>
					<div
						class="cursor-pointer text-sm font-light text-blue-500 hover:underline"
						@click="syncTables"
					>
						Sync Tables?
					</div>
				</div>
			</template>
		</List>
	</div>

	<ImportDialog
		:data-source="props.name"
		:show="showImportDialog"
		@close="showImportDialog = false"
	></ImportDialog>
</template>

<script setup lang="jsx">
import ImportDialog from '@/components/ImportDialog.vue'
import List from '@/components/List.vue'
import { useDataSource } from '@/datasource/useDataSource'
import { Badge } from 'frappe-ui'
import { computed, inject, ref } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps({
	name: {
		type: String,
		required: true,
	},
})

const router = useRouter()
const showImportDialog = ref(false)
const dataSource = useDataSource(props.name)
dataSource.fetch_tables()

const StatusCell = (props) => (
	<Badge color={props.row.hidden ? 'yellow' : 'green'}>
		{props.row.hidden ? 'Disabled' : 'Enabled'}
	</Badge>
)
const columns = [
	{ label: 'Table', key: 'label', width: '50%' },
	{ label: 'Status', key: 'status', cellComponent: StatusCell, width: '50%' },
]

const dropdownActions = computed(() => {
	return [
		dataSource.doc.allow_imports
			? {
					label: 'Import CSV',
					icon: 'upload',
					handler: () => (showImportDialog.value = true),
			  }
			: null,
		{
			label: 'Sync Tables',
			icon: 'refresh-cw',
			handler: syncTables,
		},
		{
			label: 'Delete',
			icon: 'trash',
			handler: () => dataSource.delete(),
		},
	]
})

const $notify = inject('$notify')
function syncTables() {
	dataSource
		.sync_tables()
		.catch((err) => $notify({ title: 'Error Syncing Tables', appearance: 'error' }))
}
</script>
