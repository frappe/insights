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
import { inject } from 'vue'
const dashboard = inject('dashboard')
const dashboardItem = inject('item')

function openQuery() {
	window.open(`/insights/query/${dashboardItem.query}`, '_blank')
}
</script>
