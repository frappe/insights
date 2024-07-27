<script setup>
import useDashboards from '@/dashboard/useDashboards'
import { getShortNumber } from '@/utils'
const props = defineProps({
	dashboard: { type: Object, required: true },
})
const dashboards = useDashboards()
function toggleFavourite() {
	dashboards.toggleLike(props.dashboard)
}
</script>

<template>
	<router-link
		class="flex w-full cursor-pointer"
		:to="{
			name: 'Dashboard',
			params: { name: dashboard.name },
		}"
	>
		<div
			class="flex h-full flex-1 flex-col space-y-3 overflow-hidden rounded bg-white p-4 shadow"
		>
			<div class="flex w-full items-center justify-between overflow-hidden">
				<div class="flex h-6 items-center overflow-hidden">
					<div class="flex-1 truncate text-xl font-medium text-gray-800">
						{{ dashboard.title }}
					</div>
					<span
						class="ml-1 flex h-5 w-5 flex-shrink-0 cursor-pointer items-center justify-center rounded hover:bg-gray-100"
						:class="{
							'text-yellow-500': dashboard.is_favourite,
							'text-gray-600': !dashboard.is_favourite,
						}"
						@click.prevent.stop="toggleFavourite()"
					>
						{{ dashboard.is_favourite ? '★' : '☆' }}
					</span>
				</div>
				<FeatherIcon name="arrow-right" class="h-4 w-4 text-gray-600" />
			</div>
			<div class="flex w-full items-end justify-between">
				<div class="flex gap-2">
					<div class="flex h-6 items-center text-sm text-gray-600">
						<FeatherIcon name="eye" class="mr-1 h-4 w-4" />
						{{ getShortNumber(dashboard.view_count) }}
					</div>
					<div class="flex h-6 items-center text-sm text-gray-600">
						<FeatherIcon name="bar-chart-2" class="mr-1 h-4 w-4" />
						{{ dashboard.charts.length }}
					</div>
				</div>

				<div class="flex h-6 items-center text-sm text-gray-600">
					Updated {{ dashboard.modified_from_now }}
				</div>
			</div>
		</div>
	</router-link>
</template>
