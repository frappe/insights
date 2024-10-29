<script setup lang="tsx">
import { Breadcrumbs } from 'frappe-ui'
import { BarChart2, Eye, SearchIcon } from 'lucide-vue-next'
import { ref, watchEffect } from 'vue'
import useDashboardStore from './dashboards'

const store = useDashboardStore()
const searchQuery = ref('')
watchEffect(() => {
	store.fetchDashboards(searchQuery.value)
})

watchEffect(() => {
	document.title = 'Dashboards | Insights'
})
</script>

<template>
	<header class="mb-2 flex h-12 items-center justify-between border-b py-2.5 pl-5 pr-2">
		<Breadcrumbs :items="[{ label: 'Dashboards', route: '/dashboard' }]" />
		<div class="flex items-center gap-2"></div>
	</header>

	<div class="mb-4 flex h-full flex-col gap-2 overflow-auto px-4">
		<div class="flex gap-2 overflow-visible py-1">
			<FormControl placeholder="Search" v-model="searchQuery" :debounce="300">
				<template #prefix>
					<SearchIcon class="h-4 w-4 text-gray-500" />
				</template>
			</FormControl>
		</div>

		<div class="h-full w-full">
			<!-- Dashboard Cards -->
			<div class="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
				<router-link
					v-for="dashboard in store.dashboards"
					:key="dashboard.name"
					:to="`/dashboard/${dashboard.name}`"
				>
					<div
						class="group relative flex w-full cursor-pointer flex-col gap-2 rounded bg-white"
					>
						<div
							class="flex h-[150px] overflow-hidden rounded shadow-sm group-hover:shadow"
						>
							<img
								v-if="dashboard.thumbnail"
								src="https://via.placeholder.com/150"
								onerror="this.src='/assets/builder/images/fallback.png'"
								class="w-full object-cover"
							/>
							<div v-else class="flex w-full items-center justify-center bg-gray-100">
								<p class="text-gray-500">No Thumbnail</p>
							</div>
						</div>
						<div class="flex items-center justify-between">
							<div class="flex-1">
								<div class="flex items-center gap-1">
									<p class="truncate">
										{{ dashboard.title }}
									</p>
								</div>
								<p class="mt-1 text-xs text-gray-600">
									Updated {{ dashboard.modified_from_now }}
								</p>
							</div>
							<div class="flex flex-shrink-0 flex-col items-center gap-1">
								<div class="flex gap-1">
									<Eye class="h-3.5 w-3.5 text-gray-500" stroke-width="1.5" />
									<span class="text-xs text-gray-500">10</span>
								</div>
								<div class="flex gap-1">
									<BarChart2
										class="h-3.5 w-3.5 text-gray-500"
										stroke-width="1.5"
									/>
									<span class="text-xs text-gray-500">{{
										dashboard.charts
									}}</span>
								</div>
							</div>
						</div>
					</div>
				</router-link>
			</div>
		</div>
	</div>
</template>
