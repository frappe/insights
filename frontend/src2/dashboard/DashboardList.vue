<script setup lang="tsx">
import { Breadcrumbs } from 'frappe-ui'
import { BarChart2, Clock, Eye, MoreVertical, RefreshCw, SearchIcon } from 'lucide-vue-next'
import { ref, watchEffect } from 'vue'
import { useRouter } from 'vue-router'
import useDashboardStore, { DashboardListItem } from './dashboards'

const store = useDashboardStore()
const searchQuery = ref('')
watchEffect(() => {
	store.fetchDashboards(searchQuery.value)
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

		<div class="h-full w-full">
			<!-- Dashboard Cards -->
			<div
				v-if="store.dashboards.length"
				class="grid grid-cols-1 gap-10 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
			>
				<div
					v-for="dashboard in store.dashboards"
					:key="dashboard.name"
					class="group relative flex w-full cursor-pointer flex-col gap-2 rounded bg-white"
				>
					<router-link
						:to="`/dashboards/${dashboard.name}`"
						class="flex h-[150px] overflow-hidden rounded shadow transition-transform duration-200 group-hover:scale-[1.01]"
					>
						<img
							v-if="dashboard.preview_image"
							:src="dashboard.preview_image"
							onerror="this.src = ''"
							class="z-10 object-cover opacity-80"
						/>
						<div
							v-else
							class="flex h-full w-full items-center justify-center bg-gray-50/70"
						>
							<Button
								variant="ghost"
								@click.prevent.stop="store.updatePreviewImage(dashboard.name)"
								:loading="store.updatingPreviewImage[dashboard.name]"
							>
								<template #prefix>
									<RefreshCw class="h-3.5 w-3.5 text-gray-500" />
								</template>
								<span class="text-gray-500">Load Preview</span>
							</Button>
						</div>
					</router-link>
					<div class="flex items-center justify-between gap-2">
						<div class="flex-1">
							<div class="flex items-center gap-1">
								<p class="truncate">
									{{ dashboard.title }}
								</p>
							</div>
							<div class="mt-1.5 flex gap-2">
								<div class="flex items-center gap-1">
									<Eye class="h-3 w-3 text-gray-600" stroke-width="1.5" />
									<span class="text-xs text-gray-600">
										{{ dashboard.views }}
									</span>
								</div>
								<div class="flex items-center gap-1">
									<BarChart2 class="h-3 w-3 text-gray-600" stroke-width="1.5" />
									<span class="text-xs text-gray-600">
										{{ dashboard.charts }}
									</span>
								</div>
								<div class="flex items-center gap-1">
									<Clock class="h-3 w-3 text-gray-600" stroke-width="1.5" />
									<span class="text-xs text-gray-600">
										{{ dashboard.modified_from_now }}
									</span>
								</div>
							</div>
						</div>
						<div class="flex flex-shrink-0 items-center">
							<Dropdown :options="dropdownOptions(dashboard)">
								<Button variant="ghost">
									<template #icon>
										<MoreVertical
											class="h-4 w-4 text-gray-700"
											stroke-width="1.5"
										/>
									</template>
								</Button>
							</Dropdown>
						</div>
					</div>
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
