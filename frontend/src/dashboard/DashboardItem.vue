<template>
	<div class="group relative flex h-full w-full items-center justify-center rounded-md">
		<div
			v-if="show"
			class="flex h-full w-full rounded-md bg-white"
			:class="{ 'pointer-events-none opacity-50': dashboard.editingLayout }"
		>
			<!-- dynamically rendered component based on item type (Text, Filter, Chart)-->
			<component
				v-if="item.component && item.componentProps"
				:is="item.component"
				v-bind="item.componentProps"
			>
			</component>
		</div>
		<LoadingIndicator v-else class="mb-2 w-6 text-gray-300" />

		<div
			v-if="!dashboard.editingLayout && props.item.item_type == 'Chart'"
			class="absolute top-3 right-3 z-10 flex items-center space-x-1"
		>
			<div
				class="invisible cursor-pointer rounded p-1 text-gray-600 hover:bg-gray-100 group-hover:visible"
			>
				<FeatherIcon
					name="external-link"
					class="h-4 w-4"
					@mousedown.prevent.stop=""
					@click.prevent.stop="openQuery"
				/>
			</div>

			<div v-if="appliedFilters.length">
				<Tooltip :text="appliedFilters.join(', ')">
					<div
						class="flex items-center space-x-1 rounded-full bg-gray-100 px-2 py-1 text-sm leading-3 text-gray-600"
					>
						<span>{{ appliedFilters.length }}</span>
						<FeatherIcon name="filter" class="h-3 w-3" @mousedown.prevent.stop="" />
					</div>
				</Tooltip>
			</div>
		</div>

		<div
			v-show="dashboard.editingLayout"
			class="absolute top-0 right-0 z-10 flex h-full w-full items-center justify-center"
		>
			<DashboardEditItemActions />
		</div>
	</div>
</template>

<script setup>
import useDashboardItem from '@/dashboard/useDashboardItem'
import { LoadingIndicator } from 'frappe-ui'
import { computed, inject, provide, ref } from 'vue'
import DashboardEditItemActions from './DashboardEditItemActions.vue'

const props = defineProps({ item: Object })
const dashboard = inject('dashboard')
const item = useDashboardItem(dashboard, props.item)
provide('item', props.item)

const show = computed(() => {
	return Boolean(item && item.component && item.componentProps && !item.loading)
})

const appliedFilters = ref([])
if (props.item.item_type == 'Chart') {
	dashboard.get_chart_filters
		.submit({
			chart_name: props.item.chart,
		})
		.then((res) => {
			appliedFilters.value = res.message.map((filter) => filter.label)
		})
}

function openQuery() {
	window.open(`/insights/query/${props.item.query}`, '_blank')
}
</script>
