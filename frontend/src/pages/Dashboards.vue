<template>
	<BasePage>
		<template #header>
			<div class="flex flex-1 justify-between">
				<h1 class="text-3xl font-medium text-gray-900">Dashboards</h1>
			</div>
		</template>
		<template #main>
			<div class="flex flex-1 flex-col space-y-4">
				<div class="flex space-x-4">
					<Input type="text" placeholder="Title" />
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
						<p class="flex-1 text-right">Last Modified</p>
					</div>
					<ul
						role="list"
						class="flex flex-1 flex-col divide-y divide-gray-200 overflow-y-scroll"
					>
						<li v-for="dashboard in dashboards" :key="dashboard.name">
							<router-link
								:to="{ name: 'Dashboard', params: { name: dashboard.name } }"
								class="flex cursor-pointer items-center rounded-md py-3 px-4 hover:bg-gray-50"
							>
								<p class="mr-4">
									<Input type="checkbox" class="rounded-md border-gray-400" />
								</p>
								<p
									class="flex-1 whitespace-nowrap text-sm font-medium text-gray-900"
								>
									{{ dashboard.title }}
								</p>
								<p
									class="flex-1 text-right text-sm text-gray-500"
									:title="dashboard.modified"
								>
									{{ dashboard.modified_from_now }}
								</p>
							</router-link>
						</li>
					</ul>
					<div class="flex w-full border-t px-4 py-2 text-sm text-gray-500">
						<p class="ml-auto">
							Showing {{ dashboards.length }} of {{ dashboards.length }}
						</p>
					</div>
				</div>
			</div>
		</template>
	</BasePage>
</template>

<script setup>
import BasePage from '@/components/BasePage.vue'
import { createResource } from 'frappe-ui'
import { updateDocumentTitle } from '@/utils/document'

import moment from 'moment'
import { computed, ref } from 'vue'

const getDashboards = createResource({
	method: 'insights.api.get_dashboard_list',
	initialData: [],
})
getDashboards.fetch()

const dashboards = computed(() => {
	return getDashboards.data.map((dashboard) => {
		dashboard.modified_from_now = moment(dashboard.modified).fromNow()
		return dashboard
	})
})

const pageMeta = ref({
	title: 'Dashboards',
})
updateDocumentTitle(pageMeta)
</script>
