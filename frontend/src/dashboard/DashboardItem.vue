<script setup>
import UsePopover from '@/components/UsePopover.vue'
import InvalidWidget from '@/widgets/InvalidWidget.vue'
import useChartData from '@/widgets/useChartData'
import widgets from '@/widgets/widgets'
import { watchDebounced, whenever } from '@vueuse/shared'
import { debounce } from 'frappe-ui'
import { computed, inject, provide, reactive, ref, watch } from 'vue'
import DashboardItemActions from './DashboardItemActions.vue'

const dashboard = inject('dashboard')
const props = defineProps({
	item: { type: Object, required: true },
})

let isChart = dashboard.isChart(props.item)
let chartFilters = isChart ? computed(() => dashboard.filtersByChart[props.item.item_id]) : null
let chartData = reactive({})
if (isChart) {
	const query = computed(() => props.item.options.query)
	chartData = useChartData({
		resultsFetcher() {
			return dashboard.getChartResults(props.item.item_id)
		},
	})
	// load chart data
	whenever(query, () => chartData.load(query.value), { immediate: true })
	dashboard.onRefresh(() => chartData.load(query.value))
	dashboard.refreshChartFilters(props.item.item_id)
	watch(chartFilters, () => chartData.load(props.item.options.query))

	// set initial chart options
	watchDebounced(() => chartData.recommendedChart, setInitialChartOptions, {
		deep: true,
		debounce: 500,
	})
}

const itemRef = ref(null) // used for popover
const widget = ref(null)
provide('widgetRef', widget)

const refreshKey = ref(0)
watch(
	() => JSON.stringify([props.item.item_id, props.item.options, chartFilters?.value]),
	() => debounce(() => refreshKey.value++, refreshKey.value == 0 ? 2000 : 500)(),
	{ deep: true }
)

function setInitialChartOptions() {
	if (!props.item.options.query) return
	if (props.item.options.title) return
	if (
		props.item.options.query == dashboard.currentItem?.options.query &&
		!props.item.options.title
	) {
		props.item.options.title = dashboard.currentItem.query.doc.title
	}

	if (props.item.item_type !== chartData.recommendedChart.type) return
	props.item.options = {
		...props.item.options,
		...chartData.recommendedChart.options,
	}
}

function openQueryInNewTab() {
	window.open(`/insights/query/build/${props.item.options.query}`, '_blank')
}
</script>

<template>
	<div class="dashboard-item h-full min-h-[60px] w-full p-2 [&>div:first-child]:h-full">
		<div
			ref="itemRef"
			class="group relative flex h-full rounded"
			:class="{
				' bg-white shadow': item.item_type !== 'Filter' && item.item_type !== 'Text',
				'ring-2 ring-blue-300 ring-offset-1':
					item.item_id === dashboard.currentItem?.item_id,
				'cursor-grab': dashboard.editing,
			}"
			@click.prevent.stop="dashboard.setCurrentItem(item.item_id)"
			@dblclick.prevent.stop="dashboard.edit() || dashboard.setCurrentItem(item.item_id)"
		>
			<div
				v-if="chartData.loading"
				class="absolute inset-0 z-[10000] flex h-full w-full items-center justify-center rounded bg-white"
			>
				<LoadingIndicator class="w-6 text-gray-300" />
			</div>

			<component
				ref="widget"
				:class="[dashboard.editing ? 'pointer-events-none' : '']"
				:is="widgets.getComponent(item.item_type)"
				:item_id="item.item_id"
				:data="chartData.data"
				:options="item.options"
				:key="refreshKey"
			>
				<template #placeholder>
					<InvalidWidget
						class="absolute"
						title="Insufficient options"
						icon="settings"
						:message="null"
						icon-class="text-gray-500"
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
							<FeatherIcon name="filter" class="h-3 w-3" @mousedown.prevent.stop="" />
						</div>
					</Tooltip>
				</div>
				<div
					v-if="!dashboard.editing && item.options.query"
					class="invisible -mb-1 -mt-1 flex cursor-pointer rounded p-1 text-gray-600 hover:bg-gray-100 group-hover:visible"
				>
					<FeatherIcon
						name="external-link"
						class="h-4 w-4"
						@click="openQueryInNewTab(item)"
					/>
				</div>
			</div>
		</div>

		<UsePopover
			v-if="dashboard.editing && itemRef"
			:targetElement="itemRef"
			:show="dashboard.editing && dashboard.currentItem?.item_id === item.item_id"
			placement="top-end"
		>
			<DashboardItemActions :item="item" />
		</UsePopover>
	</div>
</template>
