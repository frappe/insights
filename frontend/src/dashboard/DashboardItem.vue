<script setup>
import UsePopover from '@/components/UsePopover.vue'
import useChartData from '@/widgets/useChartData'
import widgets from '@/widgets/widgets'
import { whenever } from '@vueuse/shared'
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
	whenever(
		query,
		async () => {
			await chartData.load(query.value)
			setGuessedChart()
		},
		{ immediate: true }
	)
	dashboard.onRefresh(() => chartData.load(query.value))

	dashboard.refreshChartFilters(props.item.item_id)
	watch(chartFilters, () => chartData.load(query.value))
}

const itemRef = ref(null) // used for popover
const widget = ref(null)
provide('widgetRef', widget)

function setGuessedChart() {
	if (!props.item.options.query) return
	if (props.item.options.title) return
	if (!props.item.item_type) return
	if (
		props.item.options.query == dashboard.currentItem?.options.query &&
		!props.item.options.title
	) {
		props.item.options.title = dashboard.currentItem.query.doc.title
	}

	const guessedChart = chartData.getGuessedChart(props.item.item_type)
	if (props.item.item_type !== guessedChart.type) return
	props.item.options = {
		...props.item.options,
		...guessedChart.options,
		title: props.item.options.title,
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
				' bg-white shadow': dashboard.isChart(item),
				'ring-2 ring-gray-700 ring-offset-2':
					item.item_id === dashboard.currentItem?.item_id,
				'cursor-grab': dashboard.editing,
			}"
			@click.prevent.stop="dashboard.setCurrentItem(item.item_id)"
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
			/>

			<div class="absolute right-3 top-3 z-[10001] flex items-center">
				<div v-if="chartFilters?.length">
					<Tooltip :text="chartFilters.map((c) => c.label || c.column?.label).join(', ')">
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
