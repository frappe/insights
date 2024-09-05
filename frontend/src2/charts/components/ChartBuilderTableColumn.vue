<script setup lang="ts">
import ContentEditable from '../../components/ContentEditable.vue'
import { FIELDTYPES } from '../../helpers/constants'
import {
	ArrowDownWideNarrow,
	ArrowUpDown,
	ArrowUpNarrowWide,
	Calendar,
	Check,
	XIcon,
} from 'lucide-vue-next'
import { computed, h, inject } from 'vue'
import { column } from '../../query/helpers'
import { QueryResultColumn } from '../../types/query.types'
import { Chart } from '../chart'

const props = defineProps<{ chart: Chart; column: QueryResultColumn }>()
const chart = props.chart

const currentSortOrder = computed(() => {
	return chart.doc.config.order_by.find((order) => order.column.column_name === props.column.name)
})
const sortOptions = [
	{
		label: 'Sort Ascending',
		icon: h(ArrowUpNarrowWide, { class: 'h-4 w-4 text-gray-700', strokeWidth: 1.5 }),
		onClick: () => onSort('asc'),
	},
	{
		label: 'Sort Descending',
		icon: h(ArrowDownWideNarrow, { class: 'h-4 w-4 text-gray-700', strokeWidth: 1.5 }),
		onClick: () => onSort('desc'),
	},
	{
		label: 'Remove Sort',
		icon: h(XIcon, { class: 'h-4 w-4 text-gray-700', strokeWidth: 1.5 }),
		onClick: () => onSort(''),
	},
]

function onSort(sort_order: 'asc' | 'desc' | '') {
	const existingOrder = chart.doc.config.order_by.find(
		(order) => order.column.column_name === props.column.name
	)
	if (existingOrder) {
		if (sort_order) {
			existingOrder.direction = sort_order
		} else {
			chart.doc.config.order_by = chart.doc.config.order_by.filter(
				(order) => order.column.column_name !== props.column.name
			)
		}
	} else {
		if (!sort_order) return
		chart.doc.config.order_by.push({
			column: column(props.column.name),
			direction: sort_order,
		})
	}
}

const dateGranularityOptions = computed(() => {
	const options = [
		// { label: 'Second', onClick: () => chart.updateGranularity(props.column.name, 'second') },
		// { label: 'Minute', onClick: () => chart.updateGranularity(props.column.name, 'minute') },
		// { label: 'Hour', onClick: () => chart.updateGranularity(props.column.name, 'hour') },
		{ label: 'Day', onClick: () => chart.updateGranularity(props.column.name, 'day') },
		{ label: 'Week', onClick: () => chart.updateGranularity(props.column.name, 'week') },
		{ label: 'Month', onClick: () => chart.updateGranularity(props.column.name, 'month') },
		{ label: 'Quarter', onClick: () => chart.updateGranularity(props.column.name, 'quarter') },
		{ label: 'Year', onClick: () => chart.updateGranularity(props.column.name, 'year') },
	]
	options.forEach((option: any) => {
		option.icon =
			option.label.toLowerCase() === chart.getGranularity(props.column.name)
				? h(Check, {
						class: 'h-4 w-4 text-gray-700',
						strokeWidth: 1.5,
				  })
				: h('div', { class: 'h-4 w-4' })
	})
	return options
})
</script>

<template>
	<div class="flex w-full items-center pl-2">
		<div class="flex items-center">
			<ContentEditable
				:modelValue="props.column.name"
				placeholder="Column Name"
				class="flex h-6 items-center whitespace-nowrap rounded-sm px-0.5 text-sm focus:ring-1 focus:ring-gray-700 focus:ring-offset-1"
				disabled
			/>
		</div>

		<div class="flex">
			<!-- Sort -->
			<Dropdown :options="sortOptions">
				<Button variant="ghost" class="rounded-none">
					<template #icon>
						<component
							:is="
								!currentSortOrder
									? ArrowUpDown
									: currentSortOrder.direction === 'asc'
									? ArrowUpNarrowWide
									: ArrowDownWideNarrow
							"
							class="h-3.5 w-3.5 text-gray-700"
							stroke-width="1.5"
						/>
					</template>
				</Button>
			</Dropdown>

			<!-- Granularity -->
			<Dropdown
				v-if="FIELDTYPES.DATE.includes(props.column.type)"
				:options="dateGranularityOptions"
			>
				<Button variant="ghost" class="rounded-none">
					<template #icon>
						<Calendar class="h-3.5 w-3.5 text-gray-700" stroke-width="1.5" />
					</template>
				</Button>
			</Dropdown>
		</div>
	</div>
</template>
