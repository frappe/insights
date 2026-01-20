<script setup lang="tsx">
import { Breadcrumbs } from 'frappe-ui'
import { SearchIcon } from 'lucide-vue-next'
import { computed, ref, watchEffect } from 'vue'
import { useRouter } from 'vue-router'
import useDashboardStore, { DashboardListItem } from './dashboards'
import DashboardCard from './DashboardCard.vue'

const store = useDashboardStore()
const searchQuery = ref('')
watchEffect(() => {
	store.fetchDashboards(searchQuery.value)
})

const favorites = computed(() => {
	return store.dashboards.filter((d) => d.is_favourite)
})

const router = useRouter()
const dropdownOptions = (dashboard: DashboardListItem) => {
	return [
		{
			label: 'Open Workbook',
			icon: 'external-link',
			onClick: () => router.push(`/workbook/${dashboard.workbook}`),
		},
		{
			label: 'Refresh Preview',
			icon: 'refresh-cw',
			loading: store.updatingPreviewImage,
			onClick: () => store.updatePreviewImage(dashboard.name),
		},
	]
}

const toggleFavorite = (dashboard: DashboardListItem) => {
	store.toggleLike(dashboard.name, !dashboard.is_favourite)
}

watchEffect(() => {
	document.title = 'Dashboards | Insights'
})
</script>

<template>
	<header class="flex h-12 items-center justify-between border-b py-2.5 pl-5 pr-2">
		<Breadcrumbs :items="[{ label: 'Dashboards', route: '/dashboards' }]" />
		<div class="flex items-center gap-2"></div>
	</header>

	<div class="mb-4 flex h-full flex-col gap-3 overflow-auto px-5 py-3">
		<div class="flex gap-2 overflow-visible py-1">
			<FormControl placeholder="Search" v-model="searchQuery" :debounce="300">
				<template #prefix>
					<SearchIcon class="h-4 w-4 text-gray-500" />
				</template>
			</FormControl>
		</div>
		<!-- favourite dashboards -->
		<div class="h-full w-full">
			<div v-if="favorites.length > 0" class="mb-8">
				<h2 class="mb-4 text-lg font-semibold text-gray-700">Favorites</h2>
				<div class="grid grid-cols-1 gap-10 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
					<DashboardCard
						v-for="dashboard in favorites"
						:key="'fav-' + dashboard.name"
						:dashboard="dashboard"
						:dropdown-options="dropdownOptions(dashboard)"
						:preview-loading="store.updatingPreviewImage[dashboard.name]"
						@toggle-favorite="toggleFavorite(dashboard)"
						@update-preview="store.updatePreviewImage(dashboard.name)"
					/>
				</div>
			</div>
			<!-- all dashboards -->
			<div v-if="store.dashboards.length">
				<h2 v-if="favorites.length > 0" class="mb-4 text-lg font-semibold text-gray-700">
					All Dashboards
				</h2>
				<div class="grid grid-cols-1 gap-10 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
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
			</div>

			<!-- Empty State -->
			<div v-else class="flex h-full w-full flex-col items-center justify-center text-base">
				<div class="text-xl font-medium">No Dashboards</div>
				<div class="mt-1 text-base text-gray-600">
					Create a dashboard in your workbook to view it here.
				</div>
			</div>
		</div>
	</div>
</template>
