<template>
	<router-link
		class="mb-4 flex w-full min-w-[16rem] cursor-pointer lg:w-1/3 xl:w-1/4"
		:to="{
			name: 'Dashboard',
			params: { name: dashboard.name },
		}"
	>
		<div
			class="mr-4 flex h-full flex-1 flex-col rounded-md border border-gray-100 bg-white shadow-sm"
		>
			<div class="flex flex-1 flex-col p-4">
				<div class="flex flex-col space-y-3">
					<div class="flex items-center justify-between">
						<div class="flex h-6 items-center">
							<div class="flex-shrink-0 text-xl font-medium text-gray-800">
								{{ dashboard.title }}
							</div>
							<span
								class="ml-2 flex h-5 w-5 cursor-pointer items-center justify-center rounded-md hover:bg-gray-100"
								:class="{
									'text-yellow-400': dashboard.is_favourite,
									'text-gray-400': !dashboard.is_favourite,
								}"
								@click.prevent.stop="toggleFavourite"
							>
								{{ dashboard.is_favourite ? '★' : '☆' }}
							</span>
						</div>
						<FeatherIcon name="arrow-right" class="h-4 w-4 text-gray-500" />
					</div>
					<div class="flex items-end justify-between">
						<div
							class="flex h-6 items-center rounded-lg bg-gray-50 px-2 text-sm text-gray-500"
						>
							<FeatherIcon name="bar-chart-2" class="mr-1 h-4 w-4" />
							{{ dashboard.charts.length }}
						</div>

						<div class="flex h-6 items-center text-sm font-light text-gray-500">
							Updated {{ dashboard.modified_from_now }}
						</div>
					</div>
				</div>
			</div>
		</div>
	</router-link>
</template>

<script setup>
import { FeatherIcon } from 'frappe-ui'
import { createResource } from 'frappe-ui'
import { inject } from 'vue'

const props = defineProps({
	dashboard: {
		type: Object,
		required: true,
	},
})

const refreshDashboards = inject('refreshDashboards')
const toggleFavourite = () => {
	const toggleFavouriteResource = createResource({
		url: 'frappe.desk.like.toggle_like',
		params: {
			doctype: 'Insights Dashboard',
			name: props.dashboard.name,
		},
		onSuccess() {
			refreshDashboards()
		},
	})
	toggleFavouriteResource.submit()
}
</script>
