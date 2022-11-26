<template>
	<BasePage>
		<template #header>
			<div class="flex flex-1 justify-between">
				<h1 class="text-3xl font-medium text-gray-900">Running Queries</h1>
				<div>
					<Button
						appearance="primary"
						@click="
							getRunningQueries.submit({
								data_source: dataSource,
							})
						"
					>
						Refresh
					</Button>
				</div>
			</div>
		</template>
		<template #main>
			<div class="flex flex-1 flex-col space-y-4">
				<div class="flex space-x-4">
					<Input type="select" :options="dataSources" v-model="dataSource" />
				</div>
				<div class="flex h-[calc(100%-1.75rem)] flex-col rounded-md border">
					<!-- List Header -->
					<div
						class="flex items-center justify-between border-b py-3 px-4 text-sm text-gray-500"
					>
						<p class="mr-4">
							<Input type="checkbox" class="rounded-md border-gray-400" />
						</p>
						<p class="flex-1">Query</p>
						<p class="w-28 text-right">Time</p>
						<p class="w-28 text-right">Progress</p>
						<p class="w-28 text-right">Actions</p>
					</div>
					<div
						class="flex flex-1 select-text flex-col divide-y divide-gray-200 overflow-y-scroll"
					>
						<div
							v-for="query in runningQueries"
							class="flex cursor-pointer items-center rounded-md py-3 px-4 hover:bg-gray-50"
						>
							<p class="mr-4">
								<Input type="checkbox" class="rounded-md border-gray-400" />
							</p>
							<p class="flex-1 text-sm text-gray-900">
								{{ query.info }}
							</p>
							<p
								class="text-sm text-gray-900"
								:class="{
									'!w-28 text-right': ['time', 'progress'].includes(key),
								}"
								v-for="key in ['time', 'progress']"
							>
								{{ query[key] }}
							</p>
							<p class="w-28 text-right text-sm text-gray-900">
								<Button
									class="shadow"
									appearance="white"
									@click="killQuery(query.id)"
								>
									Stop
								</Button>
							</p>
						</div>
					</div>
				</div>
			</div>
		</template>
	</BasePage>
</template>

<script setup>
import BasePage from '@/components/BasePage.vue'
import { createResource } from 'frappe-ui'
import { updateDocumentTitle } from '@/utils'

import { computed, ref, inject } from 'vue'

const dataSource = ref('')
const getDataSources = createResource({
	method: 'insights.api.get_data_sources',
	initialData: [],
	onSuccess(res) {
		if (res.length) {
			dataSource.value = res[0].name
			getRunningQueries.submit({ data_source: dataSource.value })
		}
	},
})
getDataSources.fetch()
const dataSources = computed(() => {
	return getDataSources.data?.map((d) => d['name']) || []
})

const getRunningQueries = createResource({
	method: 'insights.api.get_running_jobs',
	initialData: [],
})

const dayjs = inject('$dayjs')
const runningQueries = computed(() => {
	console.log(getRunningQueries.data)
	return getRunningQueries.data
		.filter((d) => d.info)
		.map((d) => {
			d['time'] = dayjs(d['time']).format('S') + 's'
			d['progress'] = `${d['progress']}%`
			// trim info to fit in the table
			// d['info'] = d['info']?.substring(0, 100) + '...'
			return d
		})
})

const killQueryResource = createResource({
	method: 'insights.api.kill_running_job',
	onSuccess(res) {
		getRunningQueries.submit({ data_source: dataSource.value })
	},
})
const killQuery = (id) => {
	killQueryResource.submit({
		data_source: dataSource.value,
		query_id: id,
	})
}

const pageMeta = ref({
	title: 'Running Queries',
})
updateDocumentTitle(pageMeta)
</script>
