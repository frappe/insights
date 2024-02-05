<script setup>
import TanstackTable from '@/components/Table/TanstackTable.vue'
import { FIELDTYPES, formatNumber } from '@/utils'
import { convertResultToObjects } from '@/widgets/useChartData'
import { computed, inject } from 'vue'

const query = inject('query')
const needsExecution = computed(() => query.doc.status == 'Pending Execution')
const hasResults = computed(() => query.results?.formattedResults?.length > 0)
const data = computed(() => convertResultToObjects(query.results.formattedResults))
const tanstackColumns = computed(() => {
	if (!query.results.columns?.length) return []
	const indexColumn = {
		id: 'index',
		header: '#',
		accessorKey: 'index',
		cell: (props) => props.row.index + 1,
	}
	const cols = query.results.columns.map((column) => {
		const isNumber = FIELDTYPES.NUMBER.includes(column.type)
		return {
			id: column.label,
			header: column.label,
			accessorKey: column.label,
			enableSorting: false,
			isNumber: isNumber,
			cell: (props) => {
				const value = props.getValue()
				return isNumber ? formatNumber(value) : value
			},
		}
	})
	return [indexColumn, ...cols]
})
</script>

<template>
	<div class="relative flex h-full w-full flex-col overflow-hidden rounded border">
		<div
			v-if="needsExecution || query.executing"
			class="absolute top-8 z-10 flex h-[calc(100%-2rem)] w-full items-center justify-center rounded bg-gray-50/30 backdrop-blur-sm"
		>
			<div class="flex flex-1 flex-col items-center justify-center gap-2">
				<Button
					class="shadow-2xl"
					variant="solid"
					@click="query.execute()"
					:loading="query.executing"
				>
					Execute Query
				</Button>
			</div>
		</div>

		<TanstackTable
			:class="needsExecution ? 'pointer-events-none' : ''"
			:data="data"
			:columns="tanstackColumns"
			:showPagination="false"
		>
			<template v-if="$slots.columnActions" #columnActions="{ column: tanstackColumn }">
				<slot
					name="columnActions"
					v-if="tanstackColumn.id != 'index'"
					:column="{ label: tanstackColumn.id }"
				></slot>
			</template>
		</TanstackTable>

		<div v-if="$slots.footer && hasResults" class="border-t p-1">
			<slot name="footer"></slot>
		</div>
	</div>
</template>
