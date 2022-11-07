<template>
	<BasePage>
		<template #header>
			<div class="flex flex-1 justify-between">
				<h1 class="text-3xl font-medium text-gray-900">Dashboards</h1>
				<div>
					<Button appearance="primary" @click="showDialog = true">
						+ New Dashboard
					</Button>
				</div>
			</div>
		</template>
		<template #main>
			<div class="flex flex-1 flex-col">
				<div class="mb-4 flex space-x-4">
					<Input type="text" placeholder="Title" />
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
						<p class="flex-1 text-right">Last Modified</p>
					</div>
					<ul
						role="list"
						v-if="dashboards.length > 0"
						class="flex flex-1 flex-col divide-y divide-gray-200 overflow-y-scroll"
					>
						<li v-for="dashboard in dashboards" :key="dashboard.name">
							<router-link
								:to="{
									name: 'Dashboard',
									params: { name: dashboard.name },
								}"
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
					<div v-else class="flex flex-1 flex-col items-center justify-center space-y-1">
						<div class="text-base font-light text-gray-500">
							You haven't created any dashboards yet.
						</div>
						<div
							class="cursor-pointer text-sm font-light text-blue-500 hover:underline"
							@click="showDialog = true"
						>
							Create new?
						</div>
					</div>
					<div class="flex w-full border-t px-4 py-2 text-sm text-gray-500">
						<p class="ml-auto">
							Showing {{ dashboards.length }} of
							{{ dashboards.length }}
						</p>
					</div>
				</div>
			</div>
		</template>
	</BasePage>

	<Dialog :options="{ title: 'New Dashboard' }" v-model="showDialog">
		<template #body-content>
			<div class="space-y-4">
				<Input
					type="text"
					label="Title"
					placeholder="Enter a suitable title..."
					v-model="newDashboard.title"
				/>
			</div>
		</template>
		<template #actions>
			<Button appearance="primary" @click="createDashboard" :loading="creatingDashboard">
				Create
			</Button>
		</template>
	</Dialog>
</template>

<script setup>
import BasePage from '@/components/BasePage.vue'

import moment from 'moment'
import { useRouter } from 'vue-router'
import { createResource } from 'frappe-ui'
import { computed, reactive, ref } from 'vue'
import { updateDocumentTitle } from '@/utils'

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

const showDialog = ref(false)
const newDashboard = reactive({ title: '' })
const router = useRouter()
const createDashboardResource = createResource({
	method: 'insights.api.create_dashboard',
	onSuccess({ name }) {
		getDashboards.fetch()
		showDialog.value = false
		newDashboard.title = ''
		router.push(`/dashboard/${name}`)
	},
})
const creatingDashboard = computed(() => {
	return createDashboardResource.loading
})
const createDashboard = () => {
	if (newDashboard.title) {
		createDashboardResource.submit({
			title: newDashboard.title,
		})
	}
}

const pageMeta = ref({
	title: 'Dashboards',
})
updateDocumentTitle(pageMeta)
</script>
