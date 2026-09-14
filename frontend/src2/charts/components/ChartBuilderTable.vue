<script setup lang="ts">
import { Calendar, Check } from 'lucide-vue-next'
import { h, inject, ref } from 'vue'
import { FIELDTYPES, getGranularityOptions } from '../../helpers/constants'
import ResultPane from '../../components/result_pane/ResultPane.vue'
import QueryDataTable from '../../query/components/QueryDataTable.vue'
import { SortDirection } from '../../types/query.types'
import { sortBy } from '../adapter/table'
import { Chart } from '../chart'
import { chartPreviewKey } from '../chart_read'
import AuthoringDrillDown from '../drill/AuthoringDrillDown.vue'
import type { ChartSegmentClick } from '../drill/segment_click'
import { getGranularity } from '../helpers'

const chart = inject('chart') as Chart
const preview = inject(chartPreviewKey)!

// A cell of the preview is a segment of the same card, so it opens the same
// stack the picture above it does. The config says which columns a cell pins.
//
// No reset watcher here, unlike ChartRenderer. That component takes its chart
// as a prop from a grid that swaps cards. This one injects the preview
// ChartBuilder provided, and `useChartPreview` memoizes one store per chart per
// reading surface, so the injected object never changes identity under this
// component.
const clicked = ref<ChartSegmentClick>()

// The Table card's own sort, on the Chart's own config. One mapping, wherever
// the header that asks for it is drawn.
function onSortChange(column_name: string, sort_order: SortDirection) {
	sortBy(chart.doc.config as any, column_name, sort_order)
}

function getDateGranularityOptions(column_name: string, column_type: string) {
	return getGranularityOptions(column_type).map((option) => {
		const _option = { ...option } as any
		_option.onClick = () => chart.updateGranularity(column_name, option.value)
		_option.icon =
			option.label.toLowerCase() === getGranularity(column_name, chart.doc.config)
				? h(Check, {
						class: 'h-4 w-4 text-ink-gray-6',
						strokeWidth: 1.5,
				  })
				: h('div', { class: 'h-4 w-4' })

		return _option
	})
}
</script>

<template>
	<!-- the pane keeps its height and the card above gives way: a footer cut in
	     half is broken chrome, a shorter picture is not -->
	<div
		v-if="chart.doc.chart_type != 'Table'"
		class="flex h-[18rem] flex-shrink-0 flex-col overflow-hidden"
	>
		<ResultPane :query="preview" no-find>
			<template #grid="{ rows, currentPage, pageSize }">
				<QueryDataTable
					:query="preview"
					:rows="rows"
					:current-page="currentPage"
					:page-size="pageSize"
					:enable-sort="true"
					:enable-drill-down="true"
					@segment-click="clicked = $event"
					:on-sort-change="onSortChange"
				>
					<template #header-suffix="{ column }">
						<Dropdown
							v-if="FIELDTYPES.DATE.includes(column.type)"
							:options="getDateGranularityOptions(column.name, column.type)"
						>
							<Button variant="ghost" class="rounded-none">
								<template #icon>
									<Calendar
										class="h-3.5 w-3.5 text-ink-gray-6"
										stroke-width="1.5"
									/>
								</template>
							</Button>
						</Dropdown>
					</template>
				</QueryDataTable>
			</template>
		</ResultPane>
	</div>

	<!-- `v-if` unmounts it on close, so every drill starts from an empty stack -->
	<AuthoringDrillDown
		v-if="clicked"
		:subject="preview.drillSubject"
		:clicked="clicked"
		:adhoc-filters="preview.routedFilters"
		@close="clicked = undefined"
	/>
</template>
