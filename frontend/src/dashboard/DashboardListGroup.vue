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
	<div>
		<div class="flex items-center">
			<div class="text-xl font-medium text-gray-700">{{ title }}</div>
			<Badge variant="outline" :label="String(dashboards.length)" class="ml-2" />
			<div v-if="enableSearch" class="ml-auto flex items-center">
				<Input
					ref="searchInput"
					v-model="searchTerm"
					iconLeft="search"
					placeholder="Search..."
				/>
			</div>
		</div>
		<div class="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
			<div class="col-span-1" v-for="dashboard in filteredDashboards">
				<DashboardCard :key="dashboard.id" :dashboard="dashboard" />
			</div>
			<div
				v-if="searchTerm && filteredDashboards.length === 0"
				class="w-full text-center text-gray-600"
			>
				No dashboards found.
			</div>
		</div>
	</div>
</template>
