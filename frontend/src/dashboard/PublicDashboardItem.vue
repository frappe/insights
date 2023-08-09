<script setup>
import InvalidWidget from '@/widgets/InvalidWidget.vue'
import useChartData from '@/widgets/useChartData'
import widgets from '@/widgets/widgets'
import { whenever } from '@vueuse/shared'
import { computed, inject, reactive, watch } from 'vue'

const dashboard = inject('dashboard')
const props = defineProps({
	item: { type: Object, required: true },
})

let chartFilters = null
let isChart = dashboard.isChart(props.item)
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
	dashboard.refreshChartFilters(props.item.item_id)
	watch(chartFilters, () => {
		chartData.load(props.item.options.query)
	})
}
</script>

<template>
	<div class="dashboard-item h-full min-h-[60px] w-full p-1.5">
		<div class="flex h-full w-full">
			<div
				class="group relative flex h-full w-full rounded"
				:class="{
					'bg-white shadow': item.item_type !== 'Filter' && item.item_type !== 'Text',
				}"
			>
				<div
					v-if="chartData.loading"
					class="absolute inset-0 z-[10000] flex h-full w-full items-center justify-center rounded bg-white"
				>
					<LoadingIndicator class="w-6 text-gray-300" />
				</div>

				<component
					ref="widget"
					:is="widgets.getComponent(item.item_type)"
					:data="chartData.data"
					:item_id="item.item_id"
					:options="item.options"
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
			</div>
		</div>
	</div>
</template>
