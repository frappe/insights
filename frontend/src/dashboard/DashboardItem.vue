<script setup>
import { inject, ref } from 'vue'
import InvalidWidget from './widgets/InvalidWidget.vue'
import widgets from './widgets/widgets'

const dashboard = inject('dashboard')
const props = defineProps({
	item: { type: Object, required: true },
})

const actions = [
	{
		icon: 'settings',
		label: 'Edit',
		onClick: (item) => dashboard.setCurrentItem(item.item_id),
	},
	{
		icon: 'trash',
		label: 'Delete',
		onClick: (item) => dashboard.removeItem(item),
	},
	{
		icon: 'download',
		label: 'Download',
		hidden: (item) => item.item_type === 'Filter' || item.item_type === 'Text',
		onClick: downloadChart,
	},
]
const widget = ref(null)
function downloadChart() {
	widget.value?.$refs?.eChart?.downloadChart?.()
}
const chartFilters = ref([])
dashboard.getChartFilters(props.item.item_id).then((filters) => {
	chartFilters.value = filters
})

function makeRefreshKey(item) {
	// This is a hack to force the component to refresh when the options change
	// Returns a hash code from a string
	const str = JSON.stringify(item.options)
	let hash = 0
	for (let i = 0, len = str.length; i < len; i++) {
		let chr = str.charCodeAt(i)
		hash = (hash << 5) - hash + chr
		hash |= 0 // Convert to 32bit integer
	}
	return hash
}
</script>

<template>
	<div class="dashboard-item h-full min-h-[3rem] w-full min-w-[8rem] p-1.5">
		<div
			class="group relative flex h-full rounded-md"
			:class="{
				'bg-white shadow-sm': item.item_type !== 'Filter' && item.item_type !== 'Text',
				'ring-2 ring-blue-300 ring-offset-1':
					item.item_id === dashboard.currentItem?.item_id,
				'cursor-grab': dashboard.editing,
			}"
			@click.prevent.stop="dashboard.setCurrentItem(item.item_id)"
		>
			<div
				v-if="item.refreshing"
				class="absolute inset-0 z-[10000] flex h-full w-full items-center justify-center bg-white"
			>
				<LoadingIndicator class="w-6 text-gray-300" />
			</div>

			<component
				ref="widget"
				:class="[dashboard.editing ? 'pointer-events-none' : '']"
				:is="widgets.getComponent(item.item_type)"
				:item_id="item.item_id"
				:options="item.options"
				:key="makeRefreshKey(item)"
			>
				<template #placeholder>
					<InvalidWidget
						class="absolute"
						title="Insufficient options"
						message="Please check the options for this widget"
						icon="settings"
						icon-class="text-gray-400"
					/>
				</template>
			</component>

			<div class="absolute top-3 right-3 z-10 flex items-center">
				<div v-if="chartFilters.length">
					<Tooltip :text="chartFilters.map((c) => c.label).join(', ')">
						<div
							class="flex items-center space-x-1 rounded-full bg-gray-100 px-2 py-1 text-sm leading-3 text-gray-600"
						>
							<span>{{ chartFilters.length }}</span>
							<FeatherIcon name="filter" class="h-3 w-3" @mousedown.prevent.stop="" />
						</div>
					</Tooltip>
				</div>
			</div>

			<div
				v-if="dashboard.editing"
				class="absolute -top-7 right-0 z-20 flex cursor-pointer space-x-2.5 rounded-md bg-gray-700 px-2 py-1.5 opacity-0 shadow-sm transition-opacity duration-200 ease-in-out group-hover:opacity-100"
			>
				<FeatherIcon
					v-for="action in actions"
					:key="action.label"
					:name="action.icon"
					class="h-3.5 w-3.5 text-white"
					:class="{ hidden: action.hidden && action.hidden(item) }"
					@click="action.onClick(item)"
				/>
			</div>
		</div>
	</div>
</template>
