<script setup lang="ts">
import { Calendar, Check } from 'lucide-vue-next'
import { h, inject, ref, watchEffect } from 'vue'
import { FIELDTYPES, getGranularityOptions } from '../../helpers/constants'
import QueryDataTable from '../../query/components/QueryDataTable.vue'
import { column } from '../../query/helpers'
import { SortDirection } from '../../types/query.types'
import { Chart } from '../chart'
import type { ChartRead } from '../chart_read'
import AuthoringDrillDown from '../drill/AuthoringDrillDown.vue'
import type { ChartSegmentClick } from '../drill/segment_click'
import { getGranularity } from '../helpers'

// the chart being edited, and the rows the server ran for it
const chart = inject('chart') as Chart
const preview = inject('chartPreview') as ChartRead

// A cell of the preview is a segment of the same card, so it opens the same
// stack the picture above it does. The config says which columns a cell pins.
//
// No reset watcher here, unlike ChartRenderer. That component takes its chart
// as a prop from a grid that swaps cards. This one injects the preview
// ChartBuilder provided, and `useChartPreview` memoizes one store per chart
// docname, so the injected object never changes identity under this component.
const clicked = ref<ChartSegmentClick>()

watchEffect(() => {
	if (!chart.doc.config.order_by) {
		chart.doc.config.order_by = []
	}
})

function onSortChange(column_name: string, sort_order: SortDirection) {
	const existingOrder = chart.doc.config.order_by.find(
		(order) => order.column.column_name === column_name,
	)
	if (existingOrder) {
		if (sort_order) {
			existingOrder.direction = sort_order
		} else {
			chart.doc.config.order_by = chart.doc.config.order_by.filter(
				(order) => order.column.column_name !== column_name,
			)
		}
	} else {
		if (!sort_order) return
		chart.doc.config.order_by.push({
			column: column(column_name),
			direction: sort_order,
		})
	}
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
	<div
		v-if="chart.doc.chart_type != 'Table'"
		class="flex h-[18rem] flex-col overflow-hidden rounded-4 border"
	>
		<QueryDataTable
			:query="preview"
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
							<Calendar class="h-3.5 w-3.5 text-ink-gray-6" stroke-width="1.5" />
						</template>
					</Button>
				</Dropdown>
			</template>
		</QueryDataTable>
	</div>

	<!-- keyed on the click, so every drill starts from an empty stack -->
	<AuthoringDrillDown
		v-if="clicked"
		:subject="preview.drillSubject"
		:clicked="clicked"
		:adhoc-filters="preview.routedFilters"
		@close="clicked = undefined"
	/>
</template>
