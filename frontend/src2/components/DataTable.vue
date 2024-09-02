<script setup lang="ts">
import { Table2Icon } from 'lucide-vue-next'
import { formatNumber } from '../helpers'
import { FIELDTYPES } from '../helpers/constants'
import { QueryResultColumn, QueryResultRow } from '../types/query.types'

const props = defineProps<{
	columns: QueryResultColumn[] | undefined
	rows: QueryResultRow[] | undefined
}>()
const isNumberColumn = (col: QueryResultColumn) => FIELDTYPES.NUMBER.includes(col.type)
</script>

<template>
	<div
		v-if="columns?.length || rows?.length"
		class="flex h-full w-full flex-col overflow-hidden font-mono text-sm"
	>
		<div class="w-full flex-1 overflow-y-auto">
			<table class="h-full w-full border-separate border-spacing-0">
				<thead class="sticky top-0 bg-white">
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
					</tr>
				</thead>
				<tbody>
					<tr v-for="(row, idx) in props.rows?.slice(0, 100)" :key="idx">
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
						>
							{{ isNumberColumn(col) ? formatNumber(row[col.name]) : row[col.name] }}
						</td>
					</tr>
					<tr height="99%" class="border-b"></tr>
				</tbody>
			</table>
		</div>
		<slot name="footer"></slot>
	</div>

	<div v-else class="flex h-full w-full items-center justify-center">
		<div class="flex flex-col items-center gap-2">
			<Table2Icon class="h-16 w-16 text-gray-300" stroke-width="1.5" />
			<p class="text-center text-gray-500">No data to display.</p>
		</div>
	</div>
</template>
