<template>
	<div
		class="invisible flex items-center justify-center rounded-md border bg-white !text-sm shadow group-hover:visible"
	>
		<!-- teleport target -->
		<div :id="`dashboard-edit-item-actions-${dashboardItem.name}`" />

		<Button
			v-if="dashboardItem.item_type == 'Chart'"
			appearance="minimal"
			@click.prevent.stop="openQuery"
			iconLeft="external-link"
			class="!text-sm"
		>
			Open Query
		</Button>

		<Button
			appearance="minimal"
			@click.prevent.stop="dashboard.removeItem(dashboardItem.name)"
			iconLeft="x"
			class="!text-sm"
		>
			Remove
		</Button>
	</div>
</template>

<script setup>
import { inject, ref } from 'vue'
const dashboard = inject('dashboard')
const dashboardItem = inject('item')

function openQuery() {
	window.open(`/insights/query/${dashboardItem.query}`, '_blank')
}
</script>
