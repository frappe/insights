<script setup>
import ChartTitle from '@/components/Charts/ChartTitle.vue'
import TanstackTable from '@/components/Table/TanstackTable.vue'
import { getFormattedCell } from '@/components/Table/utils'
import { formatNumber } from '@/utils'
import { computed } from 'vue'

const props = defineProps({
	data: { type: Object, required: true },
	options: { type: Object, required: true },
})

const numberColumns = computed(() => {
	if (!props.options.columns?.length || !props.data?.length) return []
	return props.options.columns.filter((column) =>
		props.data.every((row) => typeof row[column] == 'number')
	)
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
</script>

<template>
	<div class="flex h-full w-full flex-col">
		<ChartTitle :title="props.options.title" />
		<TanstackTable
			v-if="props.options?.columns?.length || props.data?.length"
			:data="props.data"
			:columns="tanstackColumns"
			:showFilters="props.options.filtersEnabled"
		/>
	</div>
</template>
