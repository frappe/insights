<template>
	<div class="flex flex-1 flex-col space-y-4 overflow-hidden bg-white px-6 py-4">
		<div class="flex h-12 flex-shrink-0 items-center justify-between">
			<div class="text-3xl font-medium text-gray-900">Dashboards</div>
			<Button variant="solid" @click="showDialog = true">
				<template #prefix>
					<Plus class="h-4 w-4" />
				</template>
				New Dashboard
			</Button>
		</div>
		<div
			v-if="dashboards?.list?.length"
			class="-m-1 flex flex-1 flex-col space-y-6 overflow-y-scroll p-1"
		>
			<DashboardsGroup
				v-if="favorites.length > 0"
				:dashboards="favorites"
				title="Favorites"
			/>
			<DashboardsGroup
				v-if="settings.doc?.enable_permissions"
				:dashboards="privates"
				title="Private"
			/>
			<DashboardsGroup :dashboards="sortedDashboards" title="All" :enableSearch="true" />
		</div>
		<div v-else class="flex flex-1 flex-col items-center justify-center space-y-1">
			<div class="text-base font-light text-gray-600">
				You haven't created any dashboards yet.
			</div>
			<div
				class="cursor-pointer text-sm font-light text-blue-500 hover:underline"
				@click="showDialog = true"
			>
				Create a new dashboard
			</div>
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
			<Button variant="solid" @click="createDashboard" :loading="dashboards.creating">
				Create
			</Button>
		</template>
	</Dialog>
</template>

<script setup>
import useDashboards from '@/dashboard/useDashboards'
import { updateDocumentTitle } from '@/utils'
import settings from '@/utils/settings'
import { Plus } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import DashboardsGroup from './DashboardListGroup.vue'

const dashboards = useDashboards()
dashboards.reload()
const sortedDashboards = computed(() => {
	// sort alphabetically
	return dashboards.list.sort((a, b) => {
		return a.title.toLowerCase() < b.title.toLowerCase() ? -1 : 1
	})
})
const favorites = computed(() => {
	return dashboards.list.filter((dashboard) => dashboard.is_favourite)
})
const privates = computed(() => {
	return dashboards.list.filter((dashboard) => dashboard.is_private)
})

const showDialog = ref(false)
const route = useRoute()
if (route.hash == '#new') {
	showDialog.value = true
}

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
