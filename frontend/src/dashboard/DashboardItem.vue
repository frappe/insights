<template>
	<div
		class="group relative flex h-full w-full items-center justify-center rounded-md bg-gray-50"
	>
		<div
			v-if="show"
			class="flex h-full w-full bg-white"
			:class="{ 'rounded-md border-2 border-dashed': dashboard.editingLayout }"
		>
			<!-- dynamically rendered component based on item type (Text, Filter, Chart)-->
			<component
				v-if="item.component && item.componentProps"
				:is="item.component"
				v-bind="item.componentProps"
			>
			</component>
		</div>
		<Spinner v-else class="mb-2 w-6 text-gray-300" />

		<div class="absolute top-3 right-3 z-10 flex h-5 items-center">
			<DashboardItemActions />
		</div>
	</div>
</template>

<script setup>
import { computed, inject, provide } from 'vue'
import DashboardItemActions from './DashboardItemActions.vue'
import useDashboardItem from '@/dashboard/useDashboardItem'
import { Spinner } from 'frappe-ui'

const props = defineProps({ item: Object })
const dashboard = inject('dashboard')
const item = useDashboardItem(dashboard, props.item)
provide('item', props.item)

const show = computed(() => {
	return Boolean(item && item.component && item.componentProps && !item.loading)
})
</script>
