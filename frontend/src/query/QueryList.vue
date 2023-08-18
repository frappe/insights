<script setup lang="jsx">
import ListView from '@/components/ListView.vue'
import NewDialogWithTypes from '@/components/NewDialogWithTypes.vue'
import PageBreadcrumbs from '@/components/PageBreadcrumbs.vue'
import useDataSourceStore from '@/stores/dataSourceStore'
import useNotebooks from '@/notebook/useNotebooks'
import { updateDocumentTitle } from '@/utils'
import { Badge } from 'frappe-ui'
import { PlusIcon } from 'lucide-vue-next'
import { computed, nextTick, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import useQueries from './useQueries'

const queries = useQueries()
queries.reload()

const new_dialog = ref(false)
const route = useRoute()
if (route.hash == '#new') {
	new_dialog.value = true
}

const router = useRouter()
const sources = useDataSourceStore()

const newQuery = ref({ dataSource: '', title: '' })
const dataSourceOptions = computed(() => [
	{ label: 'Select a Data Source', value: '' },
	...sources.list.map((s) => ({ label: s.title, value: s.name })),
])
const createDisabled = computed(
	() => !newQuery.value.dataSource || !newQuery.value.title || queries.creating
)
const createQuery = async () => {
	const { dataSource, title } = newQuery.value
	const name = await queries.create({
		data_source: dataSource,
		title,
	})
	newQuery.value = { dataSource: '', title: '' }
	await nextTick()
	router.push({ name: 'Query', params: { name } })
}

const StatusCell = (props) => (
	<Badge theme={props.row.status == 'Pending Execution' ? 'orange' : 'green'}>
		{props.row.status}
	</Badge>
)
const columns = [
	{ label: 'Title', key: 'title' },
	{ label: 'Status', key: 'status', cellComponent: StatusCell },
	{ label: 'Chart Type', key: 'chart_type' },
	{ label: 'Data Source', key: 'data_source' },
	{ label: 'ID', key: 'name' },
	{ label: 'Created', key: 'created_from_now' },
]

const pageMeta = ref({ title: 'Queries' })
updateDocumentTitle(pageMeta)

const notebooks = useNotebooks()
notebooks.reload()
async function openQueryEditor(type) {
	if (type === 'notebook') {
		const uncategorized = notebooks.list.find((notebook) => notebook.title === 'Uncategorized')
		const page_name = await notebooks.createPage(uncategorized.name)
		return router.push({
			name: 'NotebookPage',
			params: {
				notebook: uncategorized.name,
				name: page_name,
			},
		})
	}
	const new_query = {}
	if (type === 'visual') new_query.is_assisted_query = 1
	if (type === 'classic') new_query.is_assisted_query = 0
	if (type === 'sql') new_query.is_native_query = 1
	if (type === 'script') new_query.is_script_query = 1
	const query = await queries.create(new_query)
	router.push({
		name: 'Query',
		params: { name: query.name },
	})
}

const queryBuilderTypes = ref([
	{
		label: 'Notebook',
		description: 'Create a query using the notebook interface',
		icon: 'book',
		tag: 'beta',
		onClick: () => openQueryEditor('notebook'),
	},
	{
		label: 'Visual',
		description: 'Create a query using the visual interface',
		icon: 'box',
		onClick: () => openQueryEditor('visual'),
	},
	{
		label: 'Classic',
		description: 'Create a query using the classic interface',
		icon: 'layout',
		onClick: () => openQueryEditor('classic'),
	},
	{
		label: 'SQL',
		description: 'Create a query using SQL',
		icon: 'code',
		onClick: () => openQueryEditor('sql'),
	},
	{
		label: 'Script',
		description: 'Create a query using a script',
		icon: 'code',
		tag: 'beta',
		onClick: () => openQueryEditor('script'),
	},
])
</script>

<template>
	<header class="sticky top-0 z-10 flex items-center justify-between bg-white px-5 py-2.5">
		<PageBreadcrumbs class="h-7" :items="[{ label: 'Queries' }]" />
		<div>
			<Button label="New Query" variant="solid" @click="new_dialog = true">
				<template #prefix>
					<PlusIcon class="w-4" />
				</template>
			</Button>
		</div>
	</header>
	<div class="flex flex-1 overflow-hidden bg-white px-6 py-2">
		<ListView
			:columns="columns"
			:data="queries.list"
			:rowClick="({ name }) => router.push({ name: 'Query', params: { name } })"
		>
		</ListView>
	</div>

	<NewDialogWithTypes
		v-model:show="new_dialog"
		title="Select Interface Type"
		:types="queryBuilderTypes"
	/>
</template>
