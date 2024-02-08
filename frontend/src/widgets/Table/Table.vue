<script setup>
import ChartTitle from '@/components/Charts/ChartTitle.vue'
import TanstackTable from '@/components/Table/TanstackTable.vue'
import { getCellComponent } from '@/components/Table/utils'
import { formatNumber } from '@/utils'
import { computed } from 'vue'

const props = defineProps({
	data: { type: Object, required: true },
	options: { type: Object, required: true },
})

const columns = computed(() => {
	if (!props.options.columns?.length) return []
	if (typeof props.options.columns[0] === 'string') {
		return props.options.columns.map((column) => ({
			column,
			column_options: {},
		}))
	}
	return props.options.columns.map((column) => ({
		column: column.column || column.label || column.value,
		column_options: column.column_options || {},
	}))
})

const numberColumns = computed(() => {
	if (!columns.value?.length || !props.data?.length) return []
	return columns.value
		.filter((column) => props.data.every((row) => typeof row[column.column] == 'number'))
		.map((column) => column.column)
})

const tanstackColumns = computed(() => {
	if (!columns.value?.length) return []
	if (columns.value.some((c) => !c.column)) return []

	const indexColumn = {
		id: 'index',
		header: '#',
		accessorKey: 'index',
		enableColumnFilter: false,
		cell: (props) => props.row.index + 1,
		footer: 'Total',
	}
	const cols = columns.value.map((column) => {
		return {
			id: column.column,
			header: column.column,
			accessorKey: column.column,
			filterFn: 'filterFunction',
			isNumber: numberColumns.value.includes(column.column),
			cell: (props) => getCellComponent(props, column),
			footer: (props) => {
				const isNumberColumn = numberColumns.value.includes(column.column)
				if (!isNumberColumn) return ''
				const filteredRows = props.table.getFilteredRowModel().rows
				const values = filteredRows.map((row) => row.getValue(column.column))
				return formatNumber(
					values.reduce((acc, curr) => acc + curr, 0),
					2
				)
			},
		}
	})
	return props.options.index ? [indexColumn, ...cols] : cols
})
</script>

<template>
	<div class="flex h-full w-full flex-col">
		<ChartTitle v-if="props.options.title" :title="props.options.title" />
		<TanstackTable
			v-if="columns.length || props.data?.length"
			:data="props.data"
			:columns="tanstackColumns"
			:showFooter="props.options.showTotal"
			:showFilters="Boolean(props.options.filtersEnabled)"
		/>
	</div>
</template>
