<script setup>
import PageBreadcrumbs from '@/components/PageBreadcrumbs.vue'
import TableRelationshipEditor from './TableRelationshipEditor.vue'
import useDataSource from './useDataSource'
import { provide } from 'vue'

const props = defineProps({
	name: {
		type: String,
		required: true,
	},
})

const dataSource = useDataSource(props.name)
provide('dataSource', dataSource)
dataSource.fetchTables()
</script>

<template>
	<header class="sticky top-0 z-10 flex items-center justify-between bg-white px-5 py-2.5 shadow">
		<PageBreadcrumbs
			class="h-7"
			:items="[
				{ label: 'Data Sources', route: { path: '/data-source' } },
				{
					label: dataSource.doc?.title || dataSource.doc?.name,
					route: { path: `/data-source/${dataSource.doc?.name}` },
				},
				{ label: 'Relationships' },
			]"
		/>
	</header>

	<div v-if="dataSource.doc" class="flex h-full w-full overflow-hidden">
		<TableRelationshipEditor v-if="dataSource.doc.name" />
	</div>
</template>
