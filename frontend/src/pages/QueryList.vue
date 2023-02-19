<template>
	<BasePage>
		<template #header>
			<div class="flex flex-1 justify-between">
				<h1 class="text-3xl font-medium text-gray-900">Queries</h1>
				<div>
					<Button appearance="white" @click="openDialog = true" class="shadow-sm">
						+ New Query
					</Button>
				</div>
			</div>
		</template>
		<template #main>
			<div class="flex flex-1 flex-col overflow-hidden">
				<div class="mb-4 flex flex-shrink-0 space-x-4">
					<Input type="text" placeholder="ID" v-model="filter.name" />
					<Input type="text" placeholder="Title" v-model="filter.title" />
					<Input
						type="select"
						placeholder="Data Source"
						v-model="filter.dataSource"
						:options="['', ...dataSources]"
						class="w-40"
					/>
				</div>

				<div class="flex flex-1 flex-col overflow-hidden rounded-md border">
					<!-- List Header -->
					<div
						class="flex flex-shrink-0 items-center justify-between border-b py-3 px-4 text-sm text-gray-500"
					>
						<p class="mr-4">
							<Input type="checkbox" class="rounded-md border-gray-300" />
						</p>
						<p class="flex-1 flex-grow-[2]">Title</p>
						<p class="hidden flex-1 flex-grow-[2] lg:inline-block">Tables</p>
						<p class="hidden flex-1 lg:inline-block">Chart Type</p>
						<p class="flex-1">Data Source</p>
						<p class="hidden flex-1 lg:inline-block">ID</p>
						<p class="flex-1 text-right">Created</p>
					</div>
					<ul
						role="list"
						v-if="queries.length > 0"
						class="flex flex-1 flex-col divide-y divide-gray-200 overflow-scroll"
					>
						<li v-for="query in queries" :key="query.name">
							<router-link
								:to="{
									name: 'Query',
									params: { name: query.name },
								}"
								class="flex cursor-pointer items-center rounded-md py-3 px-4 hover:bg-gray-50"
							>
								<p class="mr-4">
									<Input type="checkbox" class="rounded-md border-gray-300" />
								</p>
								<p
									class="flex-1 flex-grow-[2] overflow-hidden text-ellipsis whitespace-nowrap text-sm font-medium text-gray-900"
								>
									{{ query.title }}
								</p>
								<p
									class="hidden flex-1 flex-grow-[2] overflow-hidden text-ellipsis whitespace-nowrap text-sm text-gray-500 lg:inline-block"
								>
									{{ query.tables?.replace(/,/g, ', ') }}
								</p>
								<p
									class="hidden flex-1 whitespace-nowrap text-sm text-gray-500 lg:inline-block"
								>
									{{ query.chart_type || '-' }}
								</p>
								<p class="flex-1 whitespace-nowrap text-sm text-gray-500">
									{{ query.data_source }}
								</p>
								<p
									class="hidden flex-1 whitespace-nowrap text-sm text-gray-500 lg:inline-block"
								>
									{{ query.name }}
								</p>
								<p
									class="flex-1 text-right text-sm text-gray-500"
									:title="query.creation"
								>
									{{ query.creation_from_now }}
								</p>
							</router-link>
						</li>
					</ul>
					<div v-else class="flex flex-1 flex-col items-center justify-center space-y-1">
						<div class="text-base font-light text-gray-500">
							You haven't created any queries yet.
						</div>
						<div
							class="cursor-pointer text-sm font-light text-blue-500 hover:underline"
							@click="openDialog = true"
						>
							Create new?
						</div>
					</div>
					<div class="flex w-full border-t px-4 py-2 text-sm text-gray-500">
						<p class="ml-auto">Showing {{ queries.length }} of {{ queries.length }}</p>
					</div>
				</div>
			</div>
		</template>
	</BasePage>

	<CreateQueryDialog
		v-model:show="openDialog"
		@create="(name) => router.push(`/query/${name}`)"
	/>
</template>

<script setup>
import BasePage from '@/components/BasePage.vue'
import { updateDocumentTitle } from '@/utils'
import { createResource } from 'frappe-ui'
import { computed, inject, reactive, ref, watch } from 'vue'
import CreateQueryDialog from './CreateQueryDialog.vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const getQueries = createResource('insights.api.get_queries')
getQueries.fetch()

const dayjs = inject('$dayjs')
watch(
	() => getQueries.data,
	(data) => {
		if (data && data.length) {
			getQueries.data.forEach((query) => {
				query.creation_from_now = dayjs(query.creation).fromNow()
			})
		}
	}
)

const filter = reactive({
	name: '',
	title: '',
	dataSource: '',
})
const queries = computed(() => {
	if (!getQueries.data) return []
	if (!filter.name && !filter.title && !filter.dataSource) {
		return getQueries.data
	}
	return getQueries.data.filter((query) => {
		return (
			query.name.toLowerCase().includes(filter.name.toLowerCase()) &&
			query.title.toLowerCase().includes(filter.title.toLowerCase()) &&
			query.data_source.toLowerCase().includes(filter.dataSource.toLowerCase())
		)
	})
})

const openDialog = ref(false)
const getDataSources = createResource({
	url: 'insights.api.get_data_sources',
	auto: true,
})
const dataSources = computed(() => {
	return getDataSources.data?.map((d) => d['name']) || []
})

const pageMeta = ref({
	title: 'Queries',
})
updateDocumentTitle(pageMeta)
</script>
