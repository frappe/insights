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
			<div class="flex flex-1 flex-col space-y-4">
				<div class="flex space-x-4">
					<Input type="text" placeholder="Title" />
					<Input type="text" placeholder="Data Source" />
				</div>
				<div class="flex h-[calc(100%-1.75rem)] flex-col rounded-md border">
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
				<Input type="text" label="Title" v-model="newQuery.title" />
			</div>
		</template>
		<template #actions>
			<Button appearance="primary" @click="submitQuery" :loading="createQuery.loading">
				Create
			</Button>
		</template>
	</Dialog>
</template>

<script setup>
import BasePage from '@/components/BasePage.vue'

import moment from 'moment'
import { useRouter } from 'vue-router'
import { computed, reactive, ref } from 'vue'
import { createResource } from 'frappe-ui'
import { updateDocumentTitle } from '@/utils/document'

const openDialog = ref(false)
const newQuery = reactive({
	dataSource: '',
	title: '',
})

const getQueries = createResource('insights.api.get_queries')
const queries = computed(() => {
	const queries = getQueries.data || []
	queries.forEach((query) => {
		query.modified_from_now = moment(query.modified).fromNow()
	})
	return queries
})
getQueries.fetch()

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

const submitQuery = () => {
	if (newQuery.title && newQuery.dataSource) {
		createQuery.submit({
			title: newQuery.title,
			data_source: newQuery.dataSource,
		})
	}
}

const pageMeta = ref({
	title: 'Queries',
})
updateDocumentTitle(pageMeta)
</script>
