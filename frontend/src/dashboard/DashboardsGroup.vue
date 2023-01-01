<template>
	<div class="flex items-baseline">
		<div class="text-xl font-medium text-gray-700">{{ title }}</div>
		<div class="ml-2 rounded-md border bg-white px-2 text-gray-500">
			{{ dashboards.length }}
		</div>
	</div>
	<div class="flex flex-wrap py-4">
		<DashboardCard v-for="dashboard in dashboards" :key="dashboard.id" :dashboard="dashboard" />
	</div>
</template>

<script setup>
import DashboardCard from './DashboardCard.vue'

const props = defineProps({
	title: {
		type: String,
		required: true,
	},
	dashboards: {
		type: Array,
		required: true,
	},
})
</script>
