<script setup lang="jsx">
import List from '@/components/List.vue'
import useDataSources from '@/datasource/useDataSources'
import useNotebooks from '@/notebook/useNotebooks'
import { updateDocumentTitle } from '@/utils'
import { computed, nextTick, ref } from 'vue'
import { useRouter } from 'vue-router'
import useQueries from './useQueries'
import { Badge } from 'frappe-ui'

const queries = useQueries()
queries.reload()

const new_dialog = ref(false)
const router = useRouter()
const sources = useDataSources()
sources.reload()

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
	router.push({ name: 'QueryBuilder', params: { name } })
}

const StatusCell = (props) => (
	<Badge color={props.row.status == 'Pending Execution' ? 'yellow' : 'green'}>
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
				page: page_name,
			},
		})
	}
	const new_query = {}
	if (type === 'visual') new_query.is_assisted_query = 1
	if (type === 'classic') new_query.is_assisted_query = 0
	const query = await queries.create(new_query)
	router.push({
		name: 'QueryBuilder',
		params: { name: query.name },
	})
}

const queryBuilderTypes = ref([
	{
		label: 'Notebook',
		description: 'Create a query using the notebook interface',
		icon: 'book',
		tag: 'beta',
		handler: () => openQueryEditor('notebook'),
	},
	{
		label: 'Visual',
		description: 'Create a query using the visual interface',
		icon: 'box',
		tag: 'beta',
		handler: () => openQueryEditor('visual'),
	},
	{
		label: 'Classic',
		description: 'Create a query using the classic interface',
		icon: 'layout',
		handler: () => openQueryEditor('classic'),
	},
])
</script>

<template>
	<div class="h-full w-full bg-white px-6 py-4">
		<List
			title="Queries"
			:actions="[
				{
					label: 'New Query',
					appearance: 'white',
					iconLeft: 'plus',
					handler: () => (new_dialog = true),
				},
			]"
			:columns="columns"
			:data="queries.list"
			:rowClick="({ name }) => router.push({ name: 'QueryBuilder', params: { name } })"
		>
		</List>
	</div>

	<Dialog v-model="new_dialog">
		<template #body>
			<div class="bg-white px-4 py-5 text-base sm:p-6">
				<h3 class="text-lg font-medium leading-6 text-gray-900">Select Interface Type</h3>
				<!-- There are three types of query builder -->
				<div class="mt-4 grid grid-cols-1 gap-6">
					<div
						v-for="(type, index) in queryBuilderTypes"
						:key="index"
						class="group flex cursor-pointer items-center space-x-4"
						@click="type.handler()"
					>
						<div
							class="rounded-md border p-4 text-gray-400 shadow-sm transition-all group-hover:scale-105"
						>
							<FeatherIcon :name="type.icon" class="h-6 w-6 text-gray-400" />
						</div>
						<div>
							<div class="flex items-center space-x-2">
								<p
									class="text-lg font-medium leading-6 text-gray-900 transition-colors group-hover:text-blue-500"
								>
									{{ type.label }}
								</p>
								<Badge
									v-if="type.tag"
									color="green"
									class="!rounded-full !px-2 !py-0.5"
								>
									{{ type.tag }}
								</Badge>
							</div>
							<p class="text-sm leading-5 text-gray-500">
								{{ type.description }}
							</p>
						</div>
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>
