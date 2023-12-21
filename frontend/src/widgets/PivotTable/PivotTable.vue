<script setup>
import {
	FlexRender,
	createColumnHelper,
	getCoreRowModel,
	getExpandedRowModel,
	getGroupedRowModel,
	useVueTable,
} from '@tanstack/vue-table'
import { call } from 'frappe-ui'
import { ChevronDown, ChevronRight } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import TableEmptySection from '../Table/TableEmptySection.vue'
import { convertToNestedObject, convertToTanstackColumns } from './utils'

const props = defineProps({
	data: { type: Object, required: true },
	options: { type: Object, required: true },
})

const _data = computed(() => props.data)
const indexColumns = computed(() => props.options.rows?.map((column) => column.value) || [])
const pivotColumns = computed(() => props.options.columns?.map((column) => column.value) || [])
const valueColumns = computed(() => props.options.values?.map((column) => column.value) || [])

const pivotedData = ref([])
call('insights.api.queries.pivot', {
	data: _data.value,
	indexes: indexColumns.value,
	columns: pivotColumns.value,
	values: valueColumns.value,
}).then((data) => (pivotedData.value = data))

const tanstackColumns = computed(() => {
	if (!pivotedData.value.length) return []

	const firstPivotedRow = pivotedData.value[0]
	if (!firstPivotedRow) return []

	const nestedRowObject = convertToNestedObject(firstPivotedRow)
	const columns = convertToTanstackColumns(nestedRowObject)
	const indexTanstackColumns = columns
		.filter((column) => indexColumns.value.includes(column.accessorKey))
		.sort(
			(a, b) =>
				indexColumns.value.indexOf(a.accessorKey) -
				indexColumns.value.indexOf(b.accessorKey)
		)
	const otherTanstackColumns = columns.filter(
		(column) => !indexColumns.value.includes(column.accessorKey)
	)
	return [...indexTanstackColumns, ...otherTanstackColumns]
})

const grouping = ref([])
const columnHelper = createColumnHelper()
const table = useVueTable({
	get data() {
		return pivotedData.value
	},
	get columns() {
		return tanstackColumns.value
	},
	state: {
		get grouping() {
			return grouping.value
		},
	},
	getCoreRowModel: getCoreRowModel(),
	getExpandedRowModel: getExpandedRowModel(),
	getGroupedRowModel: getGroupedRowModel(),
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
							class="min-w-[6rem] border-y border-r bg-white py-2 px-3 text-gray-800 first:pl-4"
						>
							<div class="truncate">
								<FlexRender
									v-if="!header.isPlaceholder"
									:render="header.column.columnDef.header"
									:props="header.getContext()"
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
							class="min-w-[6rem] truncate border-b border-r bg-white py-2 px-3 first:pl-4"
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
			</table>
		</div>
	</div>
</template>
