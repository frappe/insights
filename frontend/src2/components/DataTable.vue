<script setup lang="ts">
import { Download, Search, Table2Icon } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import { createHeaders, formatNumber } from '../helpers'
import { FIELDTYPES } from '../helpers/constants'
import { QueryResultColumn, QueryResultRow } from '../types/query.types'
import DataTableColumn from './DataTableColumn.vue'

const emit = defineEmits({
	sort: (sort_order: Record<string, 'asc' | 'desc'>) => true,
	'cell-dbl-click': (row: QueryResultRow, column: QueryResultColumn) => true,
})
const props = defineProps<{
	columns: QueryResultColumn[] | undefined
	rows: QueryResultRow[] | undefined
	showRowTotals?: boolean
	showColumnTotals?: boolean
	showFilterRow?: boolean
	loading?: boolean
	onExport?: Function
	sortOrder?: Record<string, 'asc' | 'desc'>
}>()

const headers = computed(() => {
	if (!props.columns?.length) return []
	return createHeaders(props.columns)
})

const isNumberColumn = (col: QueryResultColumn): boolean => FIELDTYPES.NUMBER.includes(col.type)

const filterPerColumn = ref<Record<string, string>>({})
const visibleRows = computed(() => {
	const columns = props.columns
	const rows = props.rows
	if (!columns?.length || !rows?.length || !props.showFilterRow) return rows

	const filters = filterPerColumn.value
	return rows.filter((row) => {
		return Object.entries(filters).every(([col, filter]) => {
			if (!filter) return true
			const isNumber = isNumberColumn(columns.find((c) => c.name === col)!)
			const value = row[col]
			return applyFilter(value, isNumber, filter)
		})
	})
})

function applyFilter(value: any, isNumber: boolean, filter: string) {
	if (isNumber) {
		const operator = ['>', '<', '>=', '<=', '=', '!='].find((op) => filter.startsWith(op))
		if (operator) {
			const num = Number(filter.replace(operator, ''))
			switch (operator) {
				case '>':
					return Number(value) > num
				case '<':
					return Number(value) < num
				case '>=':
					return Number(value) >= num
				case '<=':
					return Number(value) <= num
				case '=':
					return Number(value) === num
				case '!=':
					return Number(value) !== num
			}
		}
	}
	return String(value).toLowerCase().includes(filter.toLowerCase())
}

const totalPerColumn = computed(() => {
	const columns = props.columns
	const rows = visibleRows.value
	if (!columns?.length || !rows?.length || !props.showColumnTotals) return

	const totals: Record<string, number> = {}
	columns.forEach((col) => {
		if (isNumberColumn(col)) {
			totals[col.name] = rows.reduce((acc, row) => acc + (row[col.name] as number), 0)
		}
	})
	return totals
})

const totalPerRow = computed(() => {
	const columns = props.columns
	const rows = visibleRows.value
	if (!columns?.length || !rows?.length || !props.showRowTotals) return

	const totals: Record<number, number> = {}
	rows.forEach((row, idx) => {
		totals[idx] = columns.reduce((acc, col) => {
			if (isNumberColumn(col)) {
				return acc + (row[col.name] as number)
			}
			return acc
		}, 0)
	})
	return totals
})

const totalColumnTotal = computed(() => {
	if (!props.showColumnTotals || !totalPerColumn.value) return
	return Object.values(totalPerColumn.value).reduce((acc, val) => acc + val, 0)
})

const sortOrder = ref<Record<string, 'asc' | 'desc'>>({ ...props.sortOrder })
function getSortOrder(column: QueryResultColumn) {
	return sortOrder.value[column.name]
}
function sortBy(column: QueryResultColumn, direction: 'asc' | 'desc' | '') {
	if (!direction) {
		delete sortOrder.value[column.name]
	} else {
		sortOrder.value[column.name] = direction
	}
	emit('sort', sortOrder.value)
}
</script>

<template>
	<div
		v-if="columns?.length || rows?.length"
		class="flex h-full w-full flex-col overflow-hidden text-sm"
	>
		<div class="w-full flex-1 overflow-y-auto">
			<table class="relative h-full w-full border-separate border-spacing-0">
				<thead class="sticky top-0 z-10 bg-white">
					<tr v-for="headerRow in headers">
						<td
							class="sticky left-0 z-10 whitespace-nowrap border-b border-r bg-white"
							width="1%"
						></td>
						<td
							v-for="(header, idx) in headerRow"
							:key="idx"
							class="border-b border-r"
							:class="[
								header.isLast && isNumberColumn(header.column)
									? 'text-right'
									: 'text-left',
							]"
							:colspan="header.colspan"
						>
							<slot
								v-if="header.isLast"
								name="column-header"
								:column="header.column"
								:label="header.label"
							>
								<DataTableColumn
									:column="header.column"
									:label="header.label"
									:sort-order="getSortOrder(header.column)"
									@sort-change="sortBy(header.column, $event)"
								/>
							</slot>

							<div v-else class="flex h-7 items-center truncate px-3">
								{{ header.label }}
							</div>
						</td>

						<td
							v-if="props.showRowTotals"
							class="border-b border-r text-right"
							width="1%"
						>
							<div class="truncate pl-3 pr-20"></div>
						</td>
					</tr>

					<tr v-if="props.showFilterRow">
						<td
							class="sticky left-0 z-10 whitespace-nowrap border-b border-r bg-white"
							width="1%"
						></td>
						<td
							v-for="(column, idx) in props.columns"
							:key="idx"
							class="border-b border-r p-1"
						>
							<FormControl
								type="text"
								v-model="filterPerColumn[column.name]"
								autocomplete="off"
								class="[&_input]:h-6 [&_input]:bg-gray-200/80"
							>
								<template #prefix>
									<Search class="h-4 w-4 text-gray-500" stroke-width="1.5" />
								</template>
							</FormControl>
						</td>
						<td
							v-if="props.showRowTotals"
							class="border-b border-r text-right"
							width="1%"
						>
							<div class="truncate pl-3 pr-20"></div>
						</td>
					</tr>
				</thead>
				<tbody>
					<tr v-for="(row, idx) in visibleRows?.slice(0, 100)" :key="idx">
						<td
							class="sticky left-0 z-10 whitespace-nowrap border-b border-r bg-white px-2 text-right text-xs"
							width="1%"
							height="30px"
						>
							{{ idx + 1 }}
						</td>

						<td
							v-for="col in props.columns"
							class="max-w-[24rem] truncate border-b border-r py-2 px-3 text-gray-800"
							:class="isNumberColumn(col) ? 'tnum text-right' : 'text-left'"
							height="30px"
							@dblclick="emit('cell-dbl-click', row, col)"
						>
							{{ isNumberColumn(col) ? formatNumber(row[col.name]) : row[col.name] }}
						</td>

						<td
							v-if="props.showRowTotals && totalPerRow"
							class="tnum border-b border-r px-3 text-right font-bold"
							height="30px"
						>
							{{ formatNumber(totalPerRow[idx]) }}
						</td>
					</tr>

					<tr
						v-if="props.showColumnTotals && totalPerColumn"
						class="sticky bottom-0 z-10 border-b bg-white"
					>
						<td class="whitespace-nowrap border-r border-t px-3"></td>
						<td
							v-for="col in props.columns"
							class="truncate border-r border-t py-2 px-3 font-bold text-gray-800"
							:class="isNumberColumn(col) ? 'tnum text-right' : 'text-left'"
						>
							{{ isNumberColumn(col) ? formatNumber(totalPerColumn[col.name]) : '' }}
						</td>

						<td
							v-if="props.showRowTotals && totalColumnTotal"
							class="tnum border-r border-t px-3 text-right font-bold"
						>
							{{ formatNumber(totalColumnTotal) }}
						</td>
					</tr>

					<tr height="99%" class="border-b"></tr>
				</tbody>
			</table>
		</div>
		<slot name="footer">
			<div class="flex flex-shrink-0 items-center justify-between border-t px-2 py-1">
				<slot name="footer-left">
					<div></div>
				</slot>
				<slot name="footer-right">
					<div>
						<Button v-if="props.onExport" variant="ghost" @click="props.onExport">
							<template #icon>
								<Download class="h-4 w-4 text-gray-700" stroke-width="1.5" />
							</template>
						</Button>
					</div>
				</slot>
			</div>
		</slot>
	</div>

	<div v-else class="flex h-full w-full items-center justify-center">
		<div class="flex flex-col items-center gap-2">
			<Table2Icon class="h-16 w-16 text-gray-300" stroke-width="1.5" />
			<p class="text-center text-gray-500">No data to display.</p>
		</div>
	</div>

	<div
		v-if="props.loading"
		class="absolute top-10 z-10 flex h-[calc(100%-2rem)] w-full items-center justify-center rounded bg-white/30 backdrop-blur-sm"
	>
		<LoadingIndicator class="h-8 w-8 text-gray-700" />
	</div>
</template>
