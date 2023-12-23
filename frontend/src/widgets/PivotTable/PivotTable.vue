<script setup>
import ChartTitle from '@/components/Charts/ChartTitle.vue'
import { call } from 'frappe-ui'
import { computed, ref } from 'vue'
import { convertToNestedObject, convertToTanstackColumns } from './utils'
import TanstackTable from '@/components/Table/TanstackTable.vue'

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
</script>

<template>
	<div class="flex h-full w-full flex-col">
		<ChartTitle :title="props.options.title" />
		<TanstackTable
			v-if="props.options?.columns?.length || props.data?.length"
			:data="pivotedData"
			:columns="tanstackColumns"
		/>
	</div>
</template>
