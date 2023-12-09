<script setup>
import { ellipsis, formatNumber } from '@/utils'
import {
	FlexRender,
	getCoreRowModel,
	getFilteredRowModel,
	getSortedRowModel,
	useVueTable,
} from '@tanstack/vue-table'
import { Badge, debounce } from 'frappe-ui'
import { computed, h, ref } from 'vue'

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
	return props.options.columns.map((column) => {
		return {
			id: column,
			header: column,
			accessorKey: column,
			cell: (props) => getFormattedCell(props.getValue()),
			footer: (props) => (numberColumns.value.includes(column) ? total(column) : ''),
		}
	})
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

function total(column) {
	const total = props.data.map((row) => Number(row[column]) || 0).reduce((a, b) => a + b, 0)
	return formatNumber(Number(total))
}

function getFormattedCell(cell) {
	const parsedPills = parsePills(cell)
	if (parsedPills) {
		return h(
			'div',
			parsedPills.map((item) => h(Badge, { label: item }))
		)
	}
	const isNumber = typeof cell == 'number'
	const cellValue = isNumber ? formatNumber(cell) : ellipsis(cell, 100)
	return h('div', { class: isNumber ? 'text-right tnum' : '' }, cellValue)
}
function parsePills(cell) {
	try {
		const parsedPills = JSON.parse(cell)
		if (Array.isArray(parsedPills) && parsedPills.length) {
			return parsedPills
		}
	} catch (e) {
		return undefined
	}
}
</script>

<template>
	<div
		v-if="props.options?.columns?.length || rows?.length"
		class="flex h-full w-full flex-col overflow-hidden rounded"
	>
		<div
			v-if="props.options.title"
			class="px-4 py-2 text-lg font-medium leading-6 text-gray-800"
		>
			{{ props.options.title }}
		</div>
		<div class="relative flex flex-1 flex-col overflow-scroll text-base">
			<div
				v-if="props.data?.length == 0"
				class="absolute top-0 flex h-full w-full items-center justify-center text-lg text-gray-600"
			>
				<span>No Data</span>
			</div>
			<table v-if="props.options.columns" class="border-separate border-spacing-0">
				<thead class="sticky top-0">
					<tr v-for="headerGroup in table.getHeaderGroups()" :key="headerGroup.id">
						<td
							v-if="props.options.index"
							class="w-10 border-y border-r bg-white py-2 px-3"
						>
							#
						</td>
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
							<div class="border-t p-1">
								<FormControl
									v-if="header.column.getCanFilter()"
									type="text"
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
							v-if="props.options.index"
							class="w-10 border-b border-r bg-white py-2 px-3"
						>
							{{ index + 1 }}
						</td>
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
							v-if="props.options.index"
							class="w-10 border-y border-r bg-white py-2 px-3 font-medium"
						>
							Total
						</th>
						<th
							v-for="header in footerGroup.headers"
							:key="header.id"
							:colSpan="header.colSpan"
							class="min-w-[6rem] truncate border-y border-r bg-white py-2 px-3 font-medium"
							:class="
								numberColumns.includes(header.column.id) ? 'tnum text-right' : ''
							"
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

<style>
.tnum {
	font-feature-settings: 'tnum';
}
</style>
