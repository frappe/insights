<script setup lang="tsx">
import { Breadcrumbs } from 'frappe-ui'
import { SearchIcon } from 'lucide-vue-next'
import { ref, toRef, watchEffect } from 'vue'
import { useRouter } from 'vue-router'
import FolderCard from '../components/FolderCard.vue'
import { wheneverChanges } from '../helpers'
import { __ } from '../translation'
import { useFolderNavigation } from '../workbook/useFolderNavigation'
import useWorkbookFolders from '../workbook/workbookFolders'
import DashboardCard from './DashboardCard.vue'
import useDashboardStore, { DashboardListItem } from './dashboards'

const store = useDashboardStore()
const folderStore = useWorkbookFolders()
const router = useRouter()

const { currentFolder, searchQuery, drillInto, subfolders, breadcrumbs } = useFolderNavigation(
	toRef(folderStore, 'folders'),
	__('Dashboards'),
)
const filter = ref<'all' | 'favorites'>('all')

// dashboards of the current folder come from the server; subfolders + breadcrumb
// are derived on the client from the shared workbook folder tree
async function refresh() {
	store.fetchDashboards(currentFolder.value, searchQuery.value, filter.value === 'favorites')
}

// reset on folder/filter change so a slow fetch can't keep showing the previous
// folder's dashboards; search keeps previous data (no flicker)
wheneverChanges(
	() => [filter.value, currentFolder.value],
	() => {
		store.dashboards = []
		refresh()
	},
	{ immediate: true },
)
wheneverChanges(searchQuery, refresh, { debounce: 300 })

const dropdownOptions = (dashboard: DashboardListItem) => [
	{
		label: __('Open Workbook'),
		icon: 'external-link',
		onClick: () => router.push(`/workbook/${dashboard.workbook}`),
	},
	{
		label: __('Refresh Preview'),
		icon: 'refresh-cw',
		loading: store.updatingPreviewImage,
		onClick: () => store.updatePreviewImage(dashboard.name),
	},
]

const toggleFavorite = (dashboard: DashboardListItem) => {
	store.toggleLike(dashboard.name, !dashboard.is_favourite).then(refresh)
}

watchEffect(() => {
	document.title = 'Dashboards | Insights'
})
</script>

<template>
	<header class="flex h-12 items-center justify-between border-b py-2.5 pl-5 pr-2">
		<Breadcrumbs :items="breadcrumbs" />
	</header>

	<div class="mb-4 flex h-full flex-col gap-3 overflow-auto px-5 py-3">
		<div class="flex gap-2 overflow-visible py-1">
			<FormControl
				:placeholder="__('Search by Title')"
				v-model="searchQuery"
				:debounce="300"
				autocomplete="off"
			>
				<template #prefix>
					<SearchIcon class="h-4 w-4 text-gray-500" />
				</template>
			</FormControl>
			<FormControl
				type="select"
				v-model="filter"
				:options="[
					{ label: __('All'), value: 'all' },
					{ label: __('Favorites'), value: 'favorites' },
				]"
			/>
		</div>

		<div class="h-full w-full">
			<!-- folders (sorted on top) and dashboards share one grid -->
			<div
				v-if="subfolders.length || store.dashboards.length"
				class="grid grid-cols-1 gap-10 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
			>
				<FolderCard
					v-for="folder in subfolders"
					:key="'folder-' + folder.name"
					:title="folder.title"
					@open="drillInto(folder.name)"
				/>
				<DashboardCard
					v-for="dashboard in store.dashboards"
					:key="dashboard.name"
					:dashboard="dashboard"
					:dropdown-options="dropdownOptions(dashboard)"
					:preview-loading="store.updatingPreviewImage[dashboard.name]"
					@toggle-favorite="toggleFavorite(dashboard)"
					@update-preview="store.updatePreviewImage(dashboard.name)"
				/>
			</div>

			<!-- empty -->
			<div
				v-if="!subfolders.length && !store.dashboards.length"
				class="flex h-full w-full flex-col items-center justify-center text-base"
			>
				<div class="text-xl font-medium">
					{{ filter === 'favorites' ? __('No Favorites') : __('Nothing here') }}
				</div>
				<div class="mt-1 text-base text-gray-600">
					{{
						filter === 'favorites'
							? __('Mark a dashboard as favorite to see it here.')
							: __('No folders or dashboards to display.')
					}}
				</div>
			</div>
		</div>
	</div>
</template>
