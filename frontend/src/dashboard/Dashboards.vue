<template>
	<div class="mx-auto flex h-full w-full flex-col space-y-4 px-6 py-4">
		<div class="flex h-12 items-center justify-between">
			<div class="text-3xl font-medium text-gray-900">Dashboards</div>
			<Button appearance="white" iconLeft="plus" class="shadow-sm" @click="showDialog = true">
				Create New
			</Button>
		</div>
		<div class="flex h-[calc(100%-3rem)] flex-col overflow-scroll">
			<DashboardsGroup :dashboards="favorites" title="Favorites" />
			<DashboardsGroup :dashboards="dashboards" title="All" />
		</div>
	</div>

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
import DashboardsGroup from './DashboardsGroup.vue'
import { useRouter } from 'vue-router'
import { createResource } from 'frappe-ui'
import { computed, reactive, ref, inject, provide } from 'vue'
import { updateDocumentTitle } from '@/utils'

const dayjs = inject('$dayjs')
const getDashboards = createResource({
	url: 'insights.api.get_dashboard_list',
	initialData: [],
	auto: true,
})
const dashboards = computed(() => {
	return getDashboards.data.map((dashboard) => {
		dashboard.modified_from_now = dayjs(dashboard.modified).fromNow()
		return dashboard
	})
})
const favorites = computed(() => {
	return dashboards.value.filter((dashboard) => dashboard.is_favourite)
})
function refresh() {
	getDashboards.fetch()
}
provide('refreshDashboards', refresh)

const showDialog = ref(false)
const newDashboard = reactive({ title: '' })
const router = useRouter()
const createDashboardResource = createResource({
	url: 'insights.api.create_dashboard',
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
