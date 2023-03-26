<template>
	<div class="flex flex-1 flex-col space-y-4 overflow-hidden px-6 py-4">
		<div class="flex h-12 flex-shrink-0 items-center justify-between">
			<div class="text-3xl font-medium text-gray-900">Dashboards</div>
			<Button appearance="white" iconLeft="plus" class="shadow-sm" @click="showDialog = true">
				Create New
			</Button>
		</div>
		<div class="flex flex-1 flex-col overflow-scroll">
			<DashboardsGroup :dashboards="favorites" title="Favorites" />
			<DashboardsGroup
				v-if="settings.doc?.enable_permissions"
				:dashboards="privates"
				title="Private"
			/>
			<DashboardsGroup :dashboards="dashboards.list" title="All" :enableSearch="true" />
		</div>
	</div>

	<Dialog :options="{ title: 'New Dashboard' }" v-model="showDialog">
		<template #body-content>
			<div class="space-y-4">
				<Input
					type="text"
					label="Title"
					placeholder="Enter a suitable title..."
					v-model="newDashboardTitle"
				/>
			</div>
		</template>
		<template #actions>
			<Button appearance="primary" @click="createDashboard" :loading="dashboards.creating">
				Create
			</Button>
		</template>
	</Dialog>
</template>

<script setup>
import useDashboards from '@/dashboard/useDashboards'
import { updateDocumentTitle } from '@/utils'
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import settings from '@/utils/settings'
import DashboardsGroup from './DashboardListGroup.vue'

const dashboards = useDashboards()
dashboards.reload()
const favorites = computed(() => {
	return dashboards.list.filter((dashboard) => dashboard.is_favourite)
})
const privates = computed(() => {
	return dashboards.list.filter((dashboard) => dashboard.is_private)
})

const showDialog = ref(false)
const newDashboardTitle = ref('')
const router = useRouter()

async function createDashboard() {
	const name = await dashboards.create(newDashboardTitle.value)
	showDialog.value = false
	newDashboardTitle.value = ''
	router.push(`/dashboard/${name}`)
}

const pageMeta = ref({ title: 'Dashboards' })
updateDocumentTitle(pageMeta)
</script>
