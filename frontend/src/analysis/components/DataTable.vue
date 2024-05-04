<script setup lang="ts">
import { QueryResultColumn, QueryResultRow } from '@/query/next/useQuery'
import { FIELDTYPES, formatNumber } from '@/utils'
import { Table2Icon } from 'lucide-vue-next'

const props = defineProps<{ columns: QueryResultColumn[]; rows: QueryResultRow[] }>()
const isNumberColumn = (col: QueryResultColumn) => FIELDTYPES.NUMBER.includes(col.type)
</script>

<template>
	<div
		v-if="columns?.length || rows?.length"
		class="flex h-full w-full overflow-y-auto font-mono text-sm"
	>
		<table class="border-separate border-spacing-0">
			<thead class="sticky top-0 bg-white">
				<tr>
					<td class="border-b border-r py-2 px-3"></td>
					<td
						v-for="(column, idx) in props.columns"
						:key="idx"
						class="truncate border-b border-r py-2 px-3"
						:class="
							FIELDTYPES.NUMBER.includes(column.type) ? 'text-right' : 'text-left'
						"
						width="150px"
					>
						{{ column.name }}
					</td>
				</tr>
			</thead>
			<tbody>
				<tr v-for="(row, idx) in props.rows.slice(0, 100)" :key="idx">
					<td class="border-b border-r px-3">{{ idx + 1 }}</td>
					<td
						v-for="col in props.columns"
						class="truncate border-b border-r py-2 px-3 text-gray-800"
						:class="isNumberColumn(col) ? 'text-right' : 'text-left'"
					>
						{{ isNumberColumn(col) ? formatNumber(row[col.name]) : row[col.name] }}
					</td>
				</tr>
				<tr height="99%" class="border-b"></tr>
			</tbody>
		</table>
	</div>

	<div v-else class="flex h-full w-full items-center justify-center">
		<div class="flex flex-col items-center gap-2">
			<Table2Icon class="h-16 w-16 text-gray-300" stroke-width="1.5" />
			<p class="text-center text-gray-500">No data to display.</p>
		</div>
	</div>
</template>
