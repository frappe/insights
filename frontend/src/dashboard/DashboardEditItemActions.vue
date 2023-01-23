<template>
	<div
		class="invisible flex items-center justify-center rounded-md border bg-white shadow group-hover:visible"
	>
		<!-- teleport target -->
		<div :id="`dashboard-edit-item-actions-${dashboardItem.name}`" />

		<Button
			v-if="dashboardItem.item_type == 'Chart'"
			appearance="minimal"
			@click.prevent.stop="openQuery"
			iconLeft="external-link"
			class="whitespace-nowrap !text-sm !text-gray-500 hover:bg-white hover:!text-gray-900"
		>
			Open Query
		</Button>

		<Button
			appearance="minimal"
			@click.prevent.stop="dashboard.removeItem(dashboardItem.name)"
			iconLeft="x"
			class="whitespace-nowrap !text-sm !text-gray-500 hover:bg-white hover:!text-gray-900"
		>
			Remove
		</Button>
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
