<script setup>
import { getShortNumber } from '@/utils'
import useDashboards from '@/dashboard/useDashboards'
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
		<div class="flex h-full flex-1 flex-col rounded bg-white shadow">
			<div class="flex flex-1 flex-col p-4">
				<div class="flex flex-col space-y-3">
					<div class="flex items-center justify-between">
						<div class="flex h-6 items-center">
							<div class="flex-shrink-0 text-xl font-medium text-gray-800">
								{{ dashboard.title }}
							</div>
							<span
								class="ml-2 flex h-5 w-5 cursor-pointer items-center justify-center rounded hover:bg-gray-100"
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
					<div class="flex items-end justify-between">
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
			</div>
		</div>
	</router-link>
</template>
