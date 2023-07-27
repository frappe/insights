<template>
	<div class="h-full w-full bg-white px-6 py-4">
		<Breadcrumbs
			:items="[
				{ label: 'Data Sources', href: '/data-source' },
				{ label: dataSource.doc.title },
			]"
		></Breadcrumbs>
		<ListView
			v-if="dataSource.doc && dataSource.tables.length"
			:title="dataSource.doc.title"
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
			<template #title-items>
				<Badge theme="green">Active</Badge>
				<Dropdown
					placement="left"
					:button="{ icon: 'more-horizontal', variant: 'ghost' }"
					:options="dropdownActions"
				/>
			</template>
			<template #empty-state>
				<div
					v-if="dataSource.tables.length !== 0"
					class="mt-2 flex h-full w-full flex-col items-center justify-center rounded text-base font-light text-gray-600"
				>
					<div class="text-base font-light text-gray-600">Tables are not synced yet.</div>
					<div
						class="cursor-pointer text-sm font-light text-blue-500 hover:underline"
						@click="syncTables"
					>
						Sync Tables?
					</div>
				</div>
			</template>
		</ListView>
	</div>
</template>

<script setup lang="jsx">
import Breadcrumbs from '@/components/Breadcrumbs.vue'
import ListView from '@/components/ListView.vue'
import { useDataSource } from '@/datasource/useDataSource'
import { Badge } from 'frappe-ui'
import { computed, inject } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps({
	name: {
		type: String,
		required: true,
	},
})

const router = useRouter()
const dataSource = useDataSource(props.name)
dataSource.fetch_tables()

const StatusCell = (props) => (
	<Badge theme={props.row.hidden ? 'orange' : 'green'}>
		{props.row.hidden ? 'Disabled' : 'Enabled'}
	</Badge>
)
const columns = [
	{ label: 'Table', key: 'label', width: '50%' },
	{ label: 'Status', key: 'status', cellComponent: StatusCell, width: '50%' },
]

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
			onClick: () => dataSource.delete(),
		},
	]
})

const $notify = inject('$notify')
function syncTables() {
	dataSource
		.sync_tables()
		.catch((err) => $notify({ title: 'Error Syncing Tables', variant: 'error' }))
}
</script>
