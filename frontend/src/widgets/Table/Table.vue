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
			label: column,
			value: column,
			column_options: {},
		}))
	}
	return props.options.columns
})

const numberColumns = computed(() => {
	if (!columns.value?.length || !props.data?.length) return []
	return columns.value.filter((column) =>
		props.data.every((row) => typeof row[column.value] == 'number')
	)
})

const tanstackColumns = computed(() => {
	if (!columns.value?.length) return []
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
			id: column.value,
			header: column.value,
			accessorKey: column.value,
			filterFn: 'filterFunction',
			isNumber: numberColumns.value.includes(column.value),
			cell: (props) => getCellComponent(props, column),
			footer: (props) => {
				const isNumberColumn = numberColumns.value.includes(column.value)
				if (!isNumberColumn) return ''
				const filteredRows = props.table.getFilteredRowModel().rows
				const values = filteredRows.map((row) => row.getValue(column.value))
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
			v-if="columns.length || props.data?.length"
			:data="props.data"
			:columns="tanstackColumns"
			:showFilters="props.options.filtersEnabled"
			:showFooter="props.options.showTotal"
		/>
	</div>
</template>
