<script setup lang="ts">
import { Table2Icon } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import { formatNumber } from '../helpers'
import { FIELDTYPES } from '../helpers/constants'
import { QueryResultColumn, QueryResultRow } from '../types/query.types'

const emit = defineEmits({
	'cell-dbl-click': (row: QueryResultRow, column: QueryResultColumn) => true,
})
const props = defineProps<{
	columns: QueryResultColumn[] | undefined
	rows: QueryResultRow[] | undefined
	showRowTotals?: boolean
	showColumnTotals?: boolean
	showFilterRow?: boolean
	loading?: boolean
}>()

const isNumberColumn = (col: QueryResultColumn) => FIELDTYPES.NUMBER.includes(col.type)

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

const filterPerColumn = ref<Record<string, string>>({})
</script>

<template>
	<div
		v-if="columns?.length || rows?.length"
		class="flex h-full w-full flex-col overflow-hidden font-mono text-sm"
	>
		<div class="w-full flex-1 overflow-y-auto">
			<table class="h-full w-full border-separate border-spacing-0">
				<thead class="sticky top-0 z-10 bg-white">
					<tr>
						<td class="whitespace-nowrap border-b border-r" width="1%"></td>
						<td
							v-for="(column, idx) in props.columns"
							:key="idx"
							class="border-b border-r"
							:class="isNumberColumn(column) ? 'text-right' : 'text-left'"
						>
							<slot name="column-header" :column="column">
								<div class="truncate py-2 px-3">
									{{ column.name }}
								</div>
							</slot>
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
					<!-- filter row -->
					<tr v-if="props.showFilterRow">
						<td class="whitespace-nowrap border-b border-r" width="1%"></td>
						<td
							v-for="(column, idx) in props.columns"
							:key="idx"
							class="z-0 border-b border-r p-1"
						>
							<FormControl type="text" v-model="filterPerColumn[column.name]" />
						</td>
						<td
							v-if="props.showRowTotals"
							class="border-b border-r text-right"
							width="1%"
						>
							<div class="truncate pl-3 pr-20"></div>
						</td>
					</tr>
					<tr v-for="(row, idx) in visibleRows?.slice(0, 100)" :key="idx">
						<td
							class="whitespace-nowrap border-b border-r px-3"
							width="1%"
							height="30px"
						>
							{{ idx + 1 }}
						</td>
						<td
							v-for="col in props.columns"
							class="max-w-[24rem] truncate border-b border-r py-2 px-3 text-gray-800"
							:class="isNumberColumn(col) ? 'text-right' : 'text-left'"
							height="30px"
							@dblclick="emit('cell-dbl-click', row, col)"
						>
							{{ isNumberColumn(col) ? formatNumber(row[col.name]) : row[col.name] }}
						</td>

						<td
							v-if="props.showRowTotals && totalPerRow"
							class="border-b border-r px-3 text-right font-bold"
							height="30px"
						>
							{{ formatNumber(totalPerRow[idx]) }}
						</td>
					</tr>

					<tr v-if="props.showColumnTotals && totalPerColumn" class="border-b">
						<td class="whitespace-nowrap border-r px-3"></td>
						<td
							v-for="col in props.columns"
							class="truncate border-r py-2 px-3 font-bold text-gray-800"
							:class="isNumberColumn(col) ? 'text-right' : 'text-left'"
						>
							{{ isNumberColumn(col) ? formatNumber(totalPerColumn[col.name]) : '' }}
						</td>

						<td
							v-if="props.showRowTotals && totalColumnTotal"
							class="border-r px-3 text-right font-bold"
						>
							{{ formatNumber(totalColumnTotal) }}
						</td>
					</tr>

					<tr height="99%" class="border-b"></tr>
				</tbody>
			</table>
		</div>
		<slot name="footer"></slot>
	</div>

	<div
		v-else-if="props.loading"
		class="absolute top-10 z-10 flex h-[calc(100%-2rem)] w-full items-center justify-center rounded bg-gray-50/30 backdrop-blur-sm"
	>
		<LoadingIndicator class="h-8 w-8 text-gray-700" />
	</div>

	<div v-else class="flex h-full w-full items-center justify-center">
		<div class="flex flex-col items-center gap-2">
			<Table2Icon class="h-16 w-16 text-gray-300" stroke-width="1.5" />
			<p class="text-center text-gray-500">No data to display.</p>
		</div>
	</div>
</template>
