<template>
	<header class="sticky top-0 z-10 flex items-center justify-between bg-white px-5 py-2.5 shadow">
		<PageBreadcrumbs
			class="h-7"
			:items="[
				{ label: 'Data Sources', route: { path: '/data-source' } },
				{ label: dataSource.doc.title },
			]"
		/>
	</header>

	<div class="flex h-full w-full overflow-hidden">
		<TableRelationshipEditor />
	</div>
</template>

<script setup lang="jsx">
import PageBreadcrumbs from '@/components/PageBreadcrumbs.vue'
import useDataSource from '@/datasource/useDataSource'
import { computed, inject, provide, ref } from 'vue'
import { useRouter } from 'vue-router'
import TableRelationshipEditor from './TableRelationshipEditor.vue'

const props = defineProps({
	name: {
		type: String,
		required: true,
	},
})

const router = useRouter()
const dataSource = useDataSource(props.name)
dataSource.fetchTables()

provide('dataSource', dataSource)

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
			onClick: async () => {
				await dataSource.delete()
				router.push({ name: 'DataSourceList' })
			},
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
