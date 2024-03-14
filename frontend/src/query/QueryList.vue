<script setup lang="jsx">
import IndicatorIcon from '@/components/Icons/IndicatorIcon.vue'
import ListFilter from '@/components/ListFilter/ListFilter.vue'
import NewDialogWithTypes from '@/components/NewDialogWithTypes.vue'
import PageBreadcrumbs from '@/components/PageBreadcrumbs.vue'
import useNotebooks from '@/notebook/useNotebooks'
import useQueryStore from '@/stores/queryStore'
import sessionStore from '@/stores/sessionStore'
import { isEmptyObj, updateDocumentTitle } from '@/utils'
import { getIcon } from '@/widgets/widgets'
import { useStorage } from '@vueuse/core'
import { Avatar, ListView } from 'frappe-ui'
import {
	AlignStartVertical,
	ComponentIcon,
	FileTerminal,
	GanttChartSquare,
	PlusIcon,
	SearchIcon,
	Square,
} from 'lucide-vue-next'
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const queryStore = useQueryStore()
const router = useRouter()
const route = useRoute()

const new_dialog = ref(false)
if (route.hash == '#new') {
	new_dialog.value = true
}

const pageMeta = ref({ title: 'Queries' })
updateDocumentTitle(pageMeta)

const notebooks = useNotebooks()
async function openQueryEditor(type) {
	if (type === 'notebook') {
		await notebooks.reload()
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
		label: 'Visual',
		description: 'Create a query using the visual interface',
		icon: 'bar-chart-2',
		onClick: () => openQueryEditor('visual'),
	},

	{
		label: 'SQL',
		description: 'Create a query by writing native query',
		icon: 'code',
		onClick: () => openQueryEditor('sql'),
	},
	{
		label: 'Notebook',
		description: 'Create a query using the notebook interface',
		icon: 'book',
		tag: 'beta',
		onClick: () => openQueryEditor('notebook'),
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

function getQueryTypeIcon(query) {
	if (query.is_assisted_query) return AlignStartVertical
	if (query.is_native_query) return GanttChartSquare
	if (query.is_script_query) return FileTerminal
	return Square
}

const queryListColumns = [
	{
		label: 'Title',
		key: 'title',
		width: 2,
		prefix: ({ row }) => {
			if (!row.is_stored) return null
			return <ComponentIcon class="h-4 w-4 text-gray-600" fill="currentColor" />
		},
	},
	{
		label: 'Execution Status',
		key: 'status',
		width: 1,
		getLabel: ({ row }) => row.status.replace('Execution', ''),
		prefix: ({ row }) => {
			let color = 'text-gray-500'
			if (row.status === 'Pending Execution') color = 'text-yellow-500'
			if (row.status === 'Execution Successful') color = 'text-green-500'
			if (row.status === 'Execution Failed') color = 'text-red-500'
			return <IndicatorIcon class={color} />
		},
	},
	{
		label: 'Chart Type',
		key: 'chart_type',
		width: 1,
		prefix: ({ row }) => {
			if (!row.chart_type) return null
			const Icon = getIcon(row.chart_type)
			return <Icon class="h-4 w-4 text-gray-700" />
		},
	},
	{
		label: 'Data Source',
		key: 'data_source',
		width: 1,
		getLabel: ({ row }) => row.data_source_title || row.data_source,
	},
	{
		label: 'ID',
		key: 'name',
		width: 1,
	},
	{
		label: 'Created By',
		key: 'owner_name',
		width: 1,
		prefix: ({ row }) => {
			return <Avatar image={row.owner_image} label={row.owner_name} size="md" />
		},
	},
	{
		label: 'Created',
		key: 'created_from_now',
		width: 1,
		align: 'right',
	},
]
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

	<div class="mb-4 flex h-full flex-col gap-2 overflow-auto px-4">
		<div class="flex gap-2 overflow-visible py-1">
			<FormControl
				placeholder="Search by Title"
				:modelValue="filters.title?.[1]"
				@update:modelValue="filters.title = ['like', $event]"
				:debounce="300"
			>
				<template #prefix>
					<SearchIcon class="h-4 w-4 text-gray-500" />
				</template>
			</FormControl>
			<ListFilter v-model="filters" :docfields="queryStore.getFilterableFields()" />
		</div>
		<ListView
			:columns="queryListColumns"
			:rows="queries"
			:row-key="'name'"
			:options="{
				showTooltip: false,
				getRowRoute: (query) => ({ name: 'Query', params: { name: query.name } }),
				emptyState: {
					title: 'No Query Created.',
					description: 'Create a new query to get started.',
					button: {
						label: 'New Query',
						variant: 'solid',
						onClick: () => (new_dialog = true),
					},
				},
			}"
		>
		</ListView>
	</div>

	<NewDialogWithTypes
		v-model:show="new_dialog"
		title="Select Interface Type"
		:types="queryBuilderTypes"
	/>
</template>
