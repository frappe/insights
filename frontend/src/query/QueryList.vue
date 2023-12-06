<script setup lang="jsx">
import IndicatorIcon from '@/components/Icons/IndicatorIcon.vue'
import ListFilter from '@/components/ListFilter/ListFilter.vue'
import ListView from '@/components/ListView.vue'
import NewDialogWithTypes from '@/components/NewDialogWithTypes.vue'
import PageBreadcrumbs from '@/components/PageBreadcrumbs.vue'
import useNotebooks from '@/notebook/useNotebooks'
import useDataSourceStore from '@/stores/dataSourceStore'
import useQueryStore from '@/stores/queryStore'
import sessionStore from '@/stores/sessionStore'
import { isEmptyObj, updateDocumentTitle } from '@/utils'
import { getIcon } from '@/widgets/widgets'
import { useStorage } from '@vueuse/core'
import { ListRow, ListRowItem } from 'frappe-ui'
import { PlusIcon } from 'lucide-vue-next'
import { computed, nextTick, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const queryStore = useQueryStore()

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
	() => !newQuery.value.dataSource || !newQuery.value.title || queryStore.creating
)
const createQuery = async () => {
	const { dataSource, title } = newQuery.value
	const name = await queryStore.create({
		data_source: dataSource,
		title,
	})
	newQuery.value = { dataSource: '', title: '' }
	await nextTick()
	router.push({ name: 'Query', params: { name } })
}

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
	if (type === 'sql') new_query.is_native_query = 1
	if (type === 'script') new_query.is_script_query = 1
	const query = await queryStore.create(new_query)
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
		label: 'SQL',
		description: 'Create a query by writing native query',
		icon: 'code',
		onClick: () => openQueryEditor('sql'),
	},
	{
		label: 'Script',
		description: 'Create a query by writing a python script',
		icon: 'code',
		tag: 'beta',
		onClick: () => openQueryEditor('script'),
	},
])

const user_id = sessionStore().user.user_id
const filters = useStorage('insights:query-list-filters', {
	owner: ['=', user_id],
})
const queries = computed(() => {
	if (isEmptyObj(filters.value)) {
		return queryStore.list
	}
	return queryStore.list.filter((query) => {
		for (const [fieldname, [operator, value]] of Object.entries(filters.value)) {
			if (!fieldname || !operator || !value) continue
			const field_value = query[fieldname]
			if (operator === '=') return field_value === value
			if (operator === '!=') return field_value !== value
			if (operator === '<') return field_value < value
			if (operator === '>') return field_value > value
			if (operator === '<=') return field_value <= value
			if (operator === '>=') return field_value >= value
			if (operator.includes('like')) {
				return field_value.toLowerCase().includes(value.toLowerCase())
			}
		}
		return true
	})
})
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

	<ListView
		:columns="[
			{ label: 'Title', name: 'title', class: 'flex-[3]' },
			{ label: 'Status', name: 'status', class: 'flex-[2]' },
			{ label: 'Chart Type', name: 'chart_type', class: 'flex-1' },
			{ label: 'Data Source', name: 'data_source', class: 'flex-1' },
			{ label: 'ID', name: 'name', class: 'flex-1' },
			{ label: 'Created By', name: 'owner_name', class: 'flex-1' },
			{ label: 'Created', name: 'created_from_now', class: 'flex-1 text-right' },
		]"
		:rows="queries"
	>
		<template #actions>
			<ListFilter v-model="filters" :docfields="queryStore.getFilterableFields()" />
		</template>
		<template #list-row="{ row: query }">
			<ListRow
				as="router-link"
				:row="query"
				:to="{ name: 'Query', params: { name: query.name } }"
			>
				<ListRowItem class="flex-[3]"> {{ query.title }} </ListRowItem>
				<ListRowItem class="flex-[2] space-x-2">
					<IndicatorIcon
						:class="
							{
								'Pending Execution': 'text-yellow-500',
								'Execution Successful': 'text-green-500',
								'Execution Failed': 'text-red-500',
							}[query.status] || 'text-gray-500'
						"
					/>
					<span> {{ query.status }} </span>
				</ListRowItem>
				<ListRowItem class="flex-1 space-x-2">
					<component
						v-if="query.chart_type"
						:is="getIcon(query.chart_type)"
						class="h-4 w-4 text-gray-700"
					/>
					<span> {{ query.chart_type }} </span>
				</ListRowItem>
				<ListRowItem class="flex-1"> {{ query.data_source }} </ListRowItem>
				<ListRowItem class="flex-1"> {{ query.name }} </ListRowItem>
				<ListRowItem class="flex-1 space-x-2">
					<Avatar :image="query.owner_image" :label="query.owner_name" size="md" />
					<span> {{ query.owner_name }} </span>
				</ListRowItem>
				<ListRowItem class="flex-1 justify-end">
					{{ query.created_from_now }}
				</ListRowItem>
			</ListRow>
		</template>

		<template #emptyState>
			<div class="text-xl font-medium">No Query Created.</div>
			<div class="mt-1 text-base text-gray-600">Create a new query to get started.</div>
			<Button class="mt-3" label="New Query" variant="solid" @click="new_dialog = true" />
		</template>
	</ListView>

	<NewDialogWithTypes
		v-model:show="new_dialog"
		title="Select Interface Type"
		:types="queryBuilderTypes"
	/>
</template>
