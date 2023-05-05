<script setup lang="jsx">
import List from '@/components/List.vue'
import useDataSources from '@/datasource/useDataSources'
import { updateDocumentTitle } from '@/utils'
import { computed, nextTick, ref } from 'vue'
import { useRouter } from 'vue-router'
import useQueries from './useQueries'

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
	const name = await queries.create(dataSource, title)
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

	<Dialog :options="{ title: 'New Query' }" v-model="new_dialog">
		<template #body-content>
			<div class="space-y-4">
				<Input
					type="select"
					label="Data Source"
					v-model="newQuery.dataSource"
					:options="dataSourceOptions"
				/>
				<Input
					type="text"
					label="Title"
					v-model="newQuery.title"
					placeholder="Enter a suitable title..."
				/>
			</div>
		</template>
		<template #actions>
			<Button
				appearance="primary"
				@click="createQuery"
				:disabled="createDisabled"
				:loading="queries.creating"
			>
				Create
			</Button>
		</template>
	</Dialog>
</template>
