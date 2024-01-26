<script setup>
import {
	FlexRender,
	getCoreRowModel,
	getExpandedRowModel,
	getFilteredRowModel,
	getGroupedRowModel,
	getPaginationRowModel,
	getSortedRowModel,
	useVueTable,
} from '@tanstack/vue-table'
import { debounce } from 'frappe-ui'
import { ChevronDown, ChevronLeft, ChevronRight } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import TableColumnFilter from './TableColumnFilter.vue'
import TableEmpty from './TableEmpty.vue'
import { filterFunction } from './utils'

const props = defineProps({
	columns: { type: Array, required: true },
	data: { type: Array, required: true },
	showFilters: { type: Boolean, required: false, default: true },
	showFooter: { type: Boolean, required: false, default: true },
})

const showFooter = computed(() => {
	return props.columns.some((column) => column.footer) && props.showFooter
})

const sorting = ref([])
const grouping = ref([])
const columnFilters = ref([])

const table = useVueTable({
	get data() {
		return props.data
	},
	get columns() {
		return props.columns
	},
	initialState: {
		pagination: {
			pageSize: 100,
			pageIndex: 0,
		},
	},
	state: {
		get sorting() {
			return sorting.value
		},
		get grouping() {
			return grouping.value
		},
		get columnFilters() {
			return columnFilters.value
		},
	},
	filterFns: { filterFunction },
	getCoreRowModel: getCoreRowModel(),
	getExpandedRowModel: getExpandedRowModel(),
	getGroupedRowModel: getGroupedRowModel(),
	getFilteredRowModel: getFilteredRowModel(),
	getSortedRowModel: getSortedRowModel(),
	getPaginationRowModel: getPaginationRowModel(),
	onColumnFiltersChange: debounce((updaterOrValue) => {
		columnFilters.value =
			typeof updaterOrValue == 'function'
				? updaterOrValue(columnFilters.value)
				: updaterOrValue
	}, 300),
	onSortingChange: debounce((updaterOrValue) => {
		sorting.value =
			typeof updaterOrValue == 'function' ? updaterOrValue(sorting.value) : updaterOrValue
	}, 300),
})

const pageLength = computed(() => table.getState().pagination.pageSize)
const currPage = computed(() => table.getState().pagination.pageIndex + 1)
const totalPage = computed(() => table.getPageCount())

const pageStart = computed(() => (currPage.value - 1) * pageLength.value + 1)
const pageEnd = computed(() => {
	const end = currPage.value * pageLength.value
	return end > props.data.length ? props.data.length : end
})
const totalRows = computed(() => props.data.length)
const showPagination = computed(() => totalRows.value > pageLength.value)
</script>

<template>
	<div
		v-if="props?.columns?.length || props.data?.length"
		class="flex h-full w-full flex-col overflow-hidden"
	>
		<div class="relative flex flex-1 flex-col overflow-auto text-base">
			<TableEmpty v-if="props.data?.length == 0" />
			<table v-else class="border-separate border-spacing-0">
				<thead class="sticky top-0 bg-white">
					<tr v-for="headerGroup in table.getHeaderGroups()" :key="headerGroup.id">
						<td
							v-for="header in headerGroup.headers"
							:key="header.id"
							:colSpan="header.colSpan"
							class="min-w-[6rem] border-y border-r text-gray-800"
						>
							<div
								class="cursor-pointer truncate py-2 px-3"
								:class="[
									header.column.columnDef.isNumber ? 'text-right' : '',
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
								v-if="
									props.showFilters &&
									header.column.getCanFilter() &&
									!header.isPlaceholder
								"
							>
								<TableColumnFilter
									:isNumber="header.column.columnDef.isNumber"
									:modelValue="header.column.getFilterValue()"
									@update:modelValue="header.column.setFilterValue($event)"
								/>
							</div>
						</td>
					</tr>
				</thead>
				<tbody>
					<tr v-for="(row, index) in table.getRowModel().rows" :key="row.id">
						<td
							v-for="cell in row.getVisibleCells()"
							:key="cell.id"
							class="min-w-[6rem] truncate border-b border-r py-2 px-3"
							:class="cell.column.columnDef.isNumber ? 'tnum text-right' : ''"
						>
							<div v-if="cell.getIsGrouped()" class="flex gap-1">
								<ChevronDown
									v-if="row.getIsExpanded()"
									class="h-4 w-4 cursor-pointer text-gray-600 hover:text-gray-800"
									@click="row.getToggleExpandedHandler()?.($event)"
								/>
								<ChevronRight
									v-else
									class="h-4 w-4 cursor-pointer text-gray-600 hover:text-gray-800"
									@click="row.getToggleExpandedHandler()?.($event)"
								/>
								<FlexRender
									:render="cell.column.columnDef.cell"
									:props="cell.getContext()"
								/>
							</div>
							<div v-else-if="!cell.getIsPlaceholder()">
								<FlexRender
									:render="cell.column.columnDef.cell"
									:props="cell.getContext()"
								/>
							</div>
						</td>
					</tr>
				</tbody>
				<tfoot v-if="showFooter" class="sticky bottom-0 bg-white">
					<tr v-for="footerGroup in table.getFooterGroups()" :key="footerGroup.id">
						<td
							v-for="header in footerGroup.headers"
							:key="header.id"
							:colSpan="header.colSpan"
							class="truncate border-y border-r py-2 px-3 text-left font-medium first:pl-4 last:pr-2"
							:class="[header.column.columnDef.isNumber ? 'tnum text-right' : '']"
						>
							<FlexRender
								v-if="!header.isPlaceholder"
								:render="header.column.columnDef.footer"
								:props="header.getContext()"
							/>
						</td>
					</tr>
				</tfoot>
			</table>
		</div>

		<div v-if="showPagination" class="flex flex-shrink-0 items-center justify-end gap-3 p-1">
			<p class="tnum text-sm text-gray-600">
				{{ pageStart }} - {{ pageEnd }} of {{ totalRows }} rows
			</p>
			<div class="flex gap-2">
				<Button
					variant="ghost"
					@click="table.previousPage()"
					:disabled="!table.getCanPreviousPage()"
				>
					<ChevronLeft class="h-4 w-4 text-gray-600" />
				</Button>
				<Button
					variant="ghost"
					@click="table.nextPage()"
					:disabled="!table.getCanNextPage()"
				>
					<ChevronRight class="h-4 w-4 text-gray-600" />
				</Button>
			</div>
		</div>
	</div>
</template>
