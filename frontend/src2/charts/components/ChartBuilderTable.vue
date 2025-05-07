<script setup lang="ts">
import { Calendar, Check } from 'lucide-vue-next'
import { h, inject, watchEffect } from 'vue'
import { FIELDTYPES, granularityOptions } from '../../helpers/constants'
import QueryDataTable from '../../query/components/QueryDataTable.vue'
import { column } from '../../query/helpers'
import { SortDirection } from '../../types/query.types'
import { Chart } from '../chart'
import { getGranularity } from '../helpers'

const chart = inject('chart') as Chart

watchEffect(() => {
	if (!chart.doc.config.order_by) {
		chart.doc.config.order_by = []
	}
})

function onSortChange(column_name: string, sort_order: SortDirection) {
	const existingOrder = chart.doc.config.order_by.find(
		(order) => order.column.column_name === column_name
	)
	if (existingOrder) {
		if (sort_order) {
			existingOrder.direction = sort_order
		} else {
			chart.doc.config.order_by = chart.doc.config.order_by.filter(
				(order) => order.column.column_name !== column_name
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

function getDateGranularityOptions(column_name: string) {
	return granularityOptions.map((option) => {
		const _option = { ...option } as any
		_option.onClick = () => chart.updateGranularity(column_name, option.value)
		_option.icon =
			option.label.toLowerCase() === getGranularity(column_name, chart.doc.config)
				? h(Check, {
						class: 'h-4 w-4 text-gray-700',
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
		class="flex h-[18rem] flex-col overflow-hidden rounded border"
	>
		<QueryDataTable
			:query="chart.dataQuery"
			:enable-alerts="true"
			:enable-sort="true"
			:enable-drill-down="true"
			:on-sort-change="onSortChange"
		>
			<template #header-suffix="{ column }">
				<Dropdown
					v-if="FIELDTYPES.DATE.includes(column.type)"
					:options="getDateGranularityOptions(column.name)"
				>
					<Button variant="ghost" class="rounded-none">
						<template #icon>
							<Calendar class="h-3.5 w-3.5 text-gray-700" stroke-width="1.5" />
						</template>
					</Button>
				</Dropdown>
			</template>
		</QueryDataTable>
	</div>
</template>
