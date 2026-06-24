<script setup lang="tsx">
import { useStorage } from '@vueuse/core'
import { Breadcrumbs, TabButtons } from 'frappe-ui'
import { SearchIcon } from 'lucide-vue-next'
import { computed, ref, toRef, watchEffect } from 'vue'
import { useRouter } from 'vue-router'
import FolderCard from '../components/FolderCard.vue'
import { showErrorToast, wheneverChanges } from '../helpers'
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
type DashboardFilter = 'all' | 'recents' | 'favorites' | 'created' | 'shared'

const filterTabs: { label: string; value: DashboardFilter }[] = [
	{ label: __('All'), value: 'all' },
	{ label: __('Recents'), value: 'recents' },
	{ label: __('Favorites'), value: 'favorites' },
	{ label: __('Created'), value: 'created' },
	{ label: __('Shared'), value: 'shared' },
]

// persist the chosen filter locally so it survives reloads
const filter = useStorage<DashboardFilter>('insights:dashboard-filter', 'all')

// folders only make sense in the "all" view; the other lenses span folders
const showFolders = computed(() => filter.value === 'all')

// "Load more" grows the page size and refetches (recents is capped server-side)
const PAGE_SIZE = 20
const limit = ref(PAGE_SIZE)
const hasMore = computed(() => filter.value !== 'recents' && store.dashboards.length >= limit.value)

// dashboards come from the server; subfolders + breadcrumb are derived on the
// client from the shared workbook folder tree
async function refresh() {
	if (filter.value === 'recents') {
		store.fetchRecentDashboards(searchQuery.value)
		return
	}
	store.fetchDashboards({
		// only the "all" view is folder-scoped; lenses span folders
		folder: filter.value === 'all' ? currentFolder.value ?? 'root' : undefined,
		search_term: searchQuery.value,
		favorites: filter.value === 'favorites',
		scope:
			filter.value === 'created' ? 'owned' : filter.value === 'shared' ? 'shared' : undefined,
		limit: limit.value,
	})
}

// reset pagination for a new query (filter/folder/search change)
function reload() {
	limit.value = PAGE_SIZE
	refresh()
}

function loadMore() {
	limit.value += PAGE_SIZE
	refresh()
}

const emptyState = computed(() => {
	switch (filter.value) {
		case 'favorites':
			return {
				title: __('No Favorites'),
				subtitle: __('Mark a dashboard as favorite to see it here.'),
			}
		case 'recents':
			return {
				title: __('No Recents'),
				subtitle: __('Dashboards you open will show up here.'),
			}
		case 'created':
			return {
				title: __('Nothing here'),
				subtitle: __("You haven't created any dashboards yet."),
			}
		case 'shared':
			return {
				title: __('Nothing here'),
				subtitle: __('Dashboards shared with you will show up here.'),
			}
		default:
			return {
				title: __('Nothing here'),
				subtitle: __('No folders or dashboards to display.'),
			}
	}
})

// reset on folder/filter change so a slow fetch can't keep showing the previous
// folder's dashboards; search keeps previous data (no flicker)
wheneverChanges(
	() => [filter.value, currentFolder.value],
	() => {
		store.dashboards = []
		reload()
	},
	{ immediate: true },
)
wheneverChanges(searchQuery, reload, { debounce: 300 })

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
	// optimistic: flip the icon locally instead of refetching the whole list
	const next = !dashboard.is_favourite
	dashboard.is_favourite = next
	store
		.toggleLike(dashboard.name, next)
		.then(() => {
			// in the favorites lens an un-favorited card should drop out, so refetch
			if (filter.value === 'favorites') refresh()
		})
		.catch((error: Error) => {
			dashboard.is_favourite = !next // revert on failure
			showErrorToast(error, false)
		})
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
		<div class="flex items-center justify-between gap-2 overflow-visible py-1">
			<FormControl
				class="w-64"
				:placeholder="__('Search by title')"
				v-model="searchQuery"
				:debounce="300"
				autocomplete="off"
			>
				<template #prefix>
					<SearchIcon class="h-4 w-4 text-gray-500" />
				</template>
			</FormControl>
			<TabButtons :buttons="filterTabs" v-model="filter" />
		</div>

		<div class="h-full w-full">
			<!-- folders (sorted on top) and dashboards share one grid -->
			<div
				v-if="(showFolders && subfolders.length) || store.dashboards.length"
				class="grid grid-cols-1 gap-10 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
			>
				<template v-if="showFolders">
					<FolderCard
						v-for="folder in subfolders"
						:key="'folder-' + folder.name"
						:title="folder.title"
						@open="drillInto(folder.name)"
					/>
				</template>
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

			<!-- load more -->
			<div v-if="hasMore" class="flex pt-8">
				<Button :label="__('Load more')" :loading="store.loading" @click="loadMore" />
			</div>

			<!-- empty (hidden while a fetch is in flight so it doesn't flash on tab switch) -->
			<div
				v-if="
					(!showFolders || !subfolders.length) &&
					!store.dashboards.length &&
					!store.loading
				"
				class="flex h-full w-full flex-col items-center justify-center text-base"
			>
				<div class="text-xl font-medium">{{ emptyState.title }}</div>
				<div class="mt-1 text-base text-gray-600">{{ emptyState.subtitle }}</div>
			</div>
		</div>
	</div>
</template>
