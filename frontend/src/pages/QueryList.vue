<template>
	<BasePage>
		<template #header>
			<div class="flex flex-1 justify-between">
				<h1 class="text-3xl font-medium text-gray-900">Queries</h1>
				<div>
					<Button appearance="primary" @click="openDialog = true"> + New Query </Button>
				</div>
			</div>
		</template>
		<template #main>
			<div class="flex flex-1 flex-col">
				<div class="mb-4 flex space-x-4">
					<Input type="text" placeholder="Title" v-model="filter.title" />
					<Input
						type="select"
						placeholder="Data Source"
						v-model="filter.dataSource"
						:options="['', ...dataSources]"
					/>
				</div>
				<div class="flex h-[calc(100%-3rem)] flex-col rounded-md border">
					<!-- List Header -->
					<div
						class="flex items-center justify-between border-b py-3 px-4 text-sm text-gray-500"
					>
						<p class="mr-4">
							<Input type="checkbox" class="rounded-md border-gray-400" />
						</p>
						<p class="flex-1">Title</p>
						<p class="flex-1">Tables</p>
						<p class="flex-1">Data Source</p>
						<p class="flex-1 text-right">Last Modified</p>
					</div>
					<ul
						role="list"
						class="flex flex-1 flex-col divide-y divide-gray-200 overflow-y-scroll"
					>
						<li v-for="query in queries" :key="query.name">
							<router-link
								:to="{ name: 'Query', params: { name: query.name } }"
								class="flex cursor-pointer items-center rounded-md py-3 px-4 hover:bg-gray-50"
							>
								<p class="mr-4">
									<Input type="checkbox" class="rounded-md border-gray-400" />
								</p>
								<p
									class="flex-1 whitespace-nowrap text-sm font-medium text-gray-900"
								>
									{{ query.title }}
								</p>
								<p class="flex-1 whitespace-nowrap text-sm text-gray-500">
									{{ query.tables?.replace(/,/g, ', ') }}
								</p>
								<p class="flex-1 whitespace-nowrap text-sm text-gray-500">
									{{ query.data_source }}
								</p>
								<p
									class="flex-1 text-right text-sm text-gray-500"
									:title="query.modified"
								>
									{{ query.modified_from_now }}
								</p>
							</router-link>
						</li>
					</ul>
					<div class="flex w-full border-t px-4 py-2 text-sm text-gray-500">
						<p class="ml-auto">Showing {{ queries.length }} of {{ queries.length }}</p>
					</div>
				</div>
			</div>
		</template>
	</BasePage>

	<Dialog :options="{ title: 'New Query' }" v-model="openDialog">
		<template #body-content>
			<div class="space-y-4">
				<Input
					type="select"
					label="Data Source"
					v-model="newQuery.dataSource"
					:options="dataSources"
				/>
				<div>
					<div class="mb-2 block text-sm leading-4 text-gray-700">Table</div>
					<Autocomplete
						v-model="newQuery.table"
						:options="tableOptions"
						placeholder="Select a table..."
					/>
				</div>
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
				@click="submitQuery"
				:disabled="createDisabled"
				:loading="createQuery.loading"
			>
				Create
			</Button>
		</template>
	</Dialog>
</template>

<script setup>
import BasePage from '@/components/BasePage.vue'
import Autocomplete from '@/components/Controls/Autocomplete.vue'

import moment from 'moment'
import { useRouter } from 'vue-router'
import { computed, reactive, ref, watch } from 'vue'
import { createResource } from 'frappe-ui'
import { updateDocumentTitle } from '@/utils'

const openDialog = ref(false)
const newQuery = reactive({
	dataSource: '',
	title: '',
	table: null,
})

const getQueries = createResource('insights.api.get_queries')
getQueries.fetch()
watch(
	() => getQueries.data,
	(data) => {
		if (data && data.length) {
			getQueries.data.forEach((query) => {
				query.modified_from_now = moment(query.modified).fromNow()
			})
		}
	}
)

const filter = reactive({
	title: '',
	dataSource: '',
})
const queries = computed(() => {
	if (!getQueries.data) return []
	if (!filter.title && !filter.dataSource) {
		return getQueries.data
	}
	return getQueries.data.filter((query) => {
		return (
			query.title.toLowerCase().includes(filter.title.toLowerCase()) &&
			query.data_source.toLowerCase().includes(filter.dataSource.toLowerCase())
		)
	})
})

const getDataSources = createResource({
	method: 'insights.api.get_data_sources',
	onSuccess(res) {
		if (res.length) {
			newQuery.dataSource = res[0].name
		}
	},
})
const dataSources = computed(() => {
	return getDataSources.data?.map((d) => d['name']) || []
})
getDataSources.fetch()
watch(
	() => newQuery.dataSource,
	(data_source, old) => {
		if (data_source !== old) {
			getTableOptions.submit({ data_source })
		}
	}
)

const getTableOptions = createResource({
	method: 'insights.api.get_tables',
	initialData: [],
})
const tableOptions = computed(() =>
	getTableOptions.data.map((table) => ({
		...table,
		value: table.table,
	}))
)

const router = useRouter()
const createQuery = createResource({
	method: 'insights.api.create_query',
	onSuccess(name) {
		newQuery.title = ''
		newQuery.dataSource = ''
		openDialog.value = false
		router.push(`/query/${name}`)
	},
})

const createDisabled = computed(() => {
	return !newQuery.dataSource || !newQuery.table || !newQuery.title
})
const submitQuery = () => {
	if (!createDisabled.value) {
		createQuery.submit({
			title: newQuery.title,
			data_source: newQuery.dataSource,
			table: newQuery.table,
		})
	}
}

const pageMeta = ref({
	title: 'Queries',
})
updateDocumentTitle(pageMeta)
</script>
