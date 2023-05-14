<script setup>
import InvalidWidget from '@/widgets/InvalidWidget.vue'
import useChartData from '@/widgets/useChartData'
import widgets from '@/widgets/widgets'
import { watchOnce, whenever } from '@vueuse/shared'
import { computed, inject, reactive, ref, watch } from 'vue'

const dashboard = inject('dashboard')
const props = defineProps({
	item: { type: Object, required: true },
})

function openQueryInNewTab() {
	if (!props.item.options.query) return
	window.open(`/insights/query/build/${props.item.options.query}`, '_blank')
}
const actions = [
	{
		icon: 'external-link',
		label: 'Open Query',
		hidden: (item) => item.item_type === 'Filter' || item.item_type === 'Text',
		onClick: openQueryInNewTab,
	},
	{
		icon: 'download',
		label: 'Download',
		hidden: (item) => item.item_type === 'Filter' || item.item_type === 'Text',
		onClick: downloadChart,
	},
	{
		icon: 'trash',
		label: 'Delete',
		onClick: (item) => dashboard.removeItem(item),
	},
]

let isChart = dashboard.isChart(props.item)
let chartFilters = null
let chartData = reactive({})
if (isChart) {
	const query = computed(() => props.item.options.query)
	chartData = useChartData({
		resultsFetcher() {
			return dashboard.getChartResults(props.item.item_id)
		},
	})
	whenever(query, () => chartData.load(query.value), { immediate: true })
	dashboard.onRefresh(() => chartData.load(query.value))
	chartFilters = computed(() => dashboard.filtersByChart[props.item.item_id])
	dashboard.updateChartFilters(props.item.item_id)
	watch(chartFilters, () => {
		chartData.load(props.item.options.query)
	})
	watchOnce(
		() => chartData.recommendedChart,
		() => {
			if (props.item.options.query) return
			if (props.item.item_type !== chartData.recommendedChart.type) return
			props.item.options = {
				...props.item.options,
				...chartData.recommendedChart.options,
			}
		}
	)
}

const widget = ref(null)
function downloadChart() {
	widget.value?.$refs?.eChart?.downloadChart?.()
}
</script>

<template>
	<div class="dashboard-item h-full min-h-[60px] w-full p-1.5 [&>div:first-child]:h-full">
		<Popover
			class="flex h-full w-full [&>div:first-child]:w-full"
			:show="dashboard.editing && dashboard.currentItem?.item_id === item.item_id"
			placement="top-end"
		>
			<template #target>
				<div
					class="group relative flex h-full rounded-md"
					:class="{
						'border bg-white shadow-sm':
							item.item_type !== 'Filter' && item.item_type !== 'Text',
						'ring-2 ring-blue-300 ring-offset-1':
							item.item_id === dashboard.currentItem?.item_id,
						'cursor-grab': dashboard.editing,
					}"
					@click.prevent.stop="dashboard.setCurrentItem(item.item_id)"
					@dblclick.prevent.stop="
						dashboard.edit() || dashboard.setCurrentItem(item.item_id)
					"
				>
					<div
						v-if="chartData.loading"
						class="absolute inset-0 z-[10000] flex h-full w-full items-center justify-center rounded-md bg-white"
					>
						<LoadingIndicator class="w-6 text-gray-300" />
					</div>

					<component
						ref="widget"
						:class="[dashboard.editing ? 'pointer-events-none' : '']"
						:is="widgets.getComponent(item.item_type)"
						:chartData="chartData"
						:options="item.options"
						:key="
							JSON.stringify([
								props.item.item_id,
								props.item.options,
								chartFilters?.value,
							])
						"
					>
						<template #placeholder>
							<InvalidWidget
								class="absolute"
								title="Insufficient options"
								icon="settings"
								:message="null"
								icon-class="text-gray-400"
							/>
						</template>
					</component>

					<div class="absolute right-3 top-3 z-10 flex items-center">
						<div v-if="chartFilters?.length">
							<Tooltip :text="chartFilters.map((c) => c.label).join(', ')">
								<div
									class="flex items-center space-x-1 rounded-full bg-gray-100 px-2 py-1 text-sm leading-3 text-gray-600"
								>
									<span>{{ chartFilters.length }}</span>
									<FeatherIcon
										name="filter"
										class="h-3 w-3"
										@mousedown.prevent.stop=""
									/>
								</div>
							</Tooltip>
						</div>
						<div
							v-if="!dashboard.editing && item.options.query"
							class="invisible -mb-1 -mt-1 flex cursor-pointer rounded-md p-1 text-gray-600 hover:bg-gray-100 group-hover:visible"
						>
							<FeatherIcon
								name="external-link"
								class="h-4 w-4"
								@click="openQueryInNewTab(item)"
							/>
						</div>
					</div>
				</div>
			</template>

			<template #body>
				<div
					class="mb-1 flex cursor-pointer space-x-2.5 rounded-md bg-gray-700 px-2 py-1.5 shadow-sm transition-opacity duration-200 ease-in-out"
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
			</template>
		</Popover>
	</div>
</template>
