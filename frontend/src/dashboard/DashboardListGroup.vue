<script setup>
import { ref, computed } from 'vue'
import DashboardCard from './DashboardListCard.vue'
const props = defineProps({
	title: { type: String, required: true },
	dashboards: { type: Array, required: true },
	enableSearch: { type: Boolean, default: false },
})
const searchTerm = ref('')
const filteredDashboards = computed(() => {
	if (!searchTerm.value) return props.dashboards
	return props.dashboards.filter((dashboard) => {
		return dashboard.title.toLowerCase().includes(searchTerm.value.toLowerCase())
	})
})
</script>

<template>
	<div class="flex items-baseline">
		<div class="text-xl font-medium text-gray-700">{{ title }}</div>
		<div class="ml-2 rounded-md border bg-white px-2 text-gray-500">
			{{ dashboards.length }}
		</div>
		<div v-if="enableSearch" class="ml-auto flex items-center pr-4">
			<div class="flex items-center rounded-md border border-gray-100 bg-white px-3">
				<FeatherIcon name="search" class="h-4 w-4 text-gray-500" />
				<input
					ref="searchInput"
					v-model="searchTerm"
					class="flex w-64 items-center bg-white px-2 py-1.5 focus:outline-none"
					placeholder="Search..."
				/>
			</div>
		</div>
	</div>
	<div class="flex flex-wrap py-4">
		<DashboardCard
			v-for="dashboard in filteredDashboards"
			:key="dashboard.id"
			:dashboard="dashboard"
		/>
		<div
			v-if="searchTerm && filteredDashboards.length === 0"
			class="w-full text-center text-gray-500"
		>
			No dashboards found.
		</div>
	</div>
</template>
