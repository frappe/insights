<template>
	<div class="flex space-x-1">
		<!-- teleport target -->
		<div :id="`dashboard-item-actions-${dashboardItem.name}`" />
		<div
			v-if="dashboardItem.item_type == 'Chart'"
			class="invisible cursor-pointer rounded p-1 text-gray-600 hover:bg-gray-100 group-hover:visible"
		>
			<!-- visible on dashboard item hover -->
			<FeatherIcon
				name="external-link"
				class="h-4 w-4"
				@mousedown.prevent.stop=""
				@click="openQuery"
			/>
		</div>
		<div
			v-if="!dashboard.editingLayout && dashboardItem.item_type == 'Chart' && filtersCount"
			class="flex items-center space-x-1 rounded-full bg-gray-100 px-3 text-sm leading-3 text-gray-700"
		>
			<span>{{ filtersCount }}</span>
			<FeatherIcon name="filter" class="h-3 w-3" @mousedown.prevent.stop="" />
		</div>
		<div
			v-if="dashboard.editingLayout"
			class="cursor-pointer rounded p-1 text-gray-600 hover:bg-gray-100"
		>
			<FeatherIcon
				name="x"
				class="h-4 w-4"
				@mousedown.prevent.stop=""
				@click="dashboard.removeItem(dashboardItem.name)"
			/>
		</div>
	</div>
</template>

<script setup>
import { inject, ref } from 'vue'
const dashboard = inject('dashboard')
const dashboardItem = inject('item')

const filtersCount = ref(0)
if (dashboardItem.item_type == 'Chart') {
	dashboard.get_chart_filters
		.submit({
			chart_name: dashboardItem.chart,
		})
		.then((res) => {
			filtersCount.value = res.message.length
		})
}

function openQuery() {
	window.open(`/insights/query/${dashboardItem.query}`, '_blank')
}
</script>
