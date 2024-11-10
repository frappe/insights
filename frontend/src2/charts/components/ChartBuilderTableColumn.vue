<script setup lang="ts">
import {
	ArrowDownWideNarrow,
	ArrowUpDown,
	ArrowUpNarrowWide,
	Calendar,
	Check,
	XIcon,
} from 'lucide-vue-next'
import { computed, h } from 'vue'
import ContentEditable from '../../components/ContentEditable.vue'
import { FIELDTYPES, granularityOptions } from '../../helpers/constants'
import { column } from '../../query/helpers'
import { GranularityType, QueryResultColumn } from '../../types/query.types'
import { WorkbookChart } from '../../types/workbook.types'
import { getGranularity } from '../helpers'

const props = defineProps<{
	config: WorkbookChart['config']
	column: QueryResultColumn
	onGranularityChange?: (column_name: string, granularity: GranularityType) => void
}>()

const currentSortOrder = computed(() => {
	return props.config.order_by?.find((order) => order.column.column_name === props.column.name)
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
	const existingOrder = props.config.order_by.find(
		(order) => order.column.column_name === props.column.name
	)
	if (existingOrder) {
		if (sort_order) {
			existingOrder.direction = sort_order
		} else {
			props.config.order_by = props.config.order_by.filter(
				(order) => order.column.column_name !== props.column.name
			)
		}
	} else {
		if (!sort_order) return
		props.config.order_by.push({
			column: column(props.column.name),
			direction: sort_order,
		})
	}
}

const dateGranularityOptions = computed(() => {
	if (!props.onGranularityChange) return []

	return granularityOptions.map((option) => {
		const _option = { ...option } as any
		_option.onClick = () => props.onGranularityChange?.(props.column.name, option.value)
		_option.icon =
			option.label.toLowerCase() === getGranularity(props.column.name, props.config)
				? h(Check, {
						class: 'h-4 w-4 text-gray-700',
						strokeWidth: 1.5,
				  })
				: h('div', { class: 'h-4 w-4' })

		return _option
	})
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
				v-if="FIELDTYPES.DATE.includes(props.column.type) && props.onGranularityChange"
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
