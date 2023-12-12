<script setup>
import { formatNumber } from '@/utils'
import {
	FlexRender,
	getCoreRowModel,
	getFilteredRowModel,
	getSortedRowModel,
	useVueTable,
} from '@tanstack/vue-table'
import { debounce } from 'frappe-ui'
import { computed, provide, ref } from 'vue'
import TableColumnFilter from './TableColumnFilter.vue'
import TableEmptySection from './TableEmptySection.vue'
import { filterFunction, getFormattedCell } from './utils'

const props = defineProps({
	data: { type: Object, required: true },
	options: { type: Object, required: true },
})

const _data = computed(() => props.data)
const numberColumns = computed(() => {
	if (!props.options.columns?.length || !props.data?.length) return []
	return props.options.columns.filter((column) => props.data.every((row) => !isNaN(row[column])))
})

const tanstackColumns = computed(() => {
	if (!props.options.columns?.length) return []
	const indexColumn = {
		id: 'index',
		header: '#',
		accessorKey: 'index',
		enableColumnFilter: false,
		cell: (props) => props.row.index + 1,
		footer: 'Total',
	}
	const cols = props.options.columns.map((column) => {
		return {
			id: column,
			header: column,
			accessorKey: column,
			filterFn: 'filterFunction',
			isNumber: numberColumns.value.includes(column),
			cell: (props) => getFormattedCell(props.getValue()),
			footer: (props) => {
				const isNumberColumn = numberColumns.value.includes(column)
				if (!isNumberColumn) return ''
				const filteredRows = props.table.getFilteredRowModel().rows
				const values = filteredRows.map((row) => row.getValue(column))
				return formatNumber(values.reduce((acc, curr) => acc + curr, 0))
			},
		}
	})
	return props.options.index ? [indexColumn, ...cols] : cols
})

const columnFilters = ref([])
const sorting = ref([])
const table = useVueTable({
	get data() {
		return _data.value
	},
	get columns() {
		return tanstackColumns.value
	},
	state: {
		get sorting() {
			return sorting.value
		},
		get columnFilters() {
			return columnFilters.value
		},
	},
	filterFns: { filterFunction },
	getCoreRowModel: getCoreRowModel(),
	getFilteredRowModel: getFilteredRowModel(),
	getSortedRowModel: getSortedRowModel(),
	onColumnFiltersChange: debounce((updaterOrValue) => {
		columnFilters.value =
			typeof updaterOrValue == 'function'
				? updaterOrValue(columnFilters.value)
				: updaterOrValue
	}, 500),
	onSortingChange: debounce((updaterOrValue) => {
		sorting.value =
			typeof updaterOrValue == 'function' ? updaterOrValue(sorting.value) : updaterOrValue
	}, 500),
})
</script>

<template>
	<div
		v-if="props.options?.columns?.length || props.data?.length"
		class="flex h-full w-full flex-col overflow-hidden rounded"
	>
		<div
			v-if="props.options.title"
			class="px-4 py-2 text-lg font-medium leading-6 text-gray-800"
		>
			{{ props.options.title }}
		</div>
		<div class="relative flex flex-1 flex-col overflow-scroll text-base">
			<TableEmptySection v-if="props.data?.length == 0" />
			<table v-else-if="props.options.columns" class="border-separate border-spacing-0">
				<thead class="sticky top-0">
					<tr v-for="headerGroup in table.getHeaderGroups()" :key="headerGroup.id">
						<td
							v-for="header in headerGroup.headers"
							:key="header.id"
							:colSpan="header.colSpan"
							class="min-w-[6rem] border-y border-r bg-white"
						>
							<div
								class="cursor-pointer truncate py-2 px-3 text-gray-600"
								:class="[
									numberColumns.includes(header.column.id) ? 'text-right' : '',
									header.column.getCanSort() ? 'hover:text-gray-800' : '',
								]"
								@click.prevent="header.column.getToggleSortingHandler()?.($event)"
							>
								<FlexRender
									v-if="!header.isPlaceholder"
									:render="header.column.columnDef.header"
									:props="header.getContext()"
								/>
								<span class="ml-2 text-[10px] text-gray-400">
									{{
										header.column.getIsSorted() == 'desc'
											? '▼'
											: header.column.getIsSorted() == 'asc'
											? '▲'
											: ''
									}}
								</span>
							</div>
							<div
								class="border-t p-1"
								v-if="props.options.filtersEnabled && header.column.getCanFilter()"
							>
								<TableColumnFilter
									:isNumber="numberColumns.includes(header.column.id)"
									:modelValue="header.column.getFilterValue()"
									@update:modelValue="header.column.setFilterValue($event)"
								/>
							</div>
						</td>
					</tr>
				</thead>
				<tbody>
					<tr
						v-for="(row, index) in table.getRowModel().rows.slice(0, 300)"
						:key="row.id"
					>
						<td
							v-for="cell in row.getVisibleCells()"
							:key="cell.id"
							class="min-w-[6rem] truncate border-b border-r bg-white py-2 px-3"
						>
							<FlexRender
								:render="cell.column.columnDef.cell"
								:props="cell.getContext()"
							/>
						</td>
					</tr>
				</tbody>
				<tfoot v-if="props.options.showTotal" class="sticky bottom-0 bg-white">
					<tr v-for="footerGroup in table.getFooterGroups()" :key="footerGroup.id">
						<th
							v-for="header in footerGroup.headers"
							:key="header.id"
							:colSpan="header.colSpan"
							class="truncate border-y border-r bg-white py-2 px-3 text-left font-medium"
							:class="[
								numberColumns.includes(header.column.id) ? 'tnum text-right' : '',
							]"
						>
							<FlexRender
								v-if="!header.isPlaceholder"
								:render="header.column.columnDef.footer"
								:props="header.getContext()"
							/>
						</th>
					</tr>
				</tfoot>
			</table>
		</div>
	</div>
</template>
