<script setup>
import { useDataSourceTable } from '@/datasource/useDataSource'
import { computed, ref, watch } from 'vue'
import InputWithPopover from './InputWithPopover.vue'
const props = defineProps({
	data_source: String,
	tables: Array,
	modelValue: Object,
	columnFilter: Function,
	value: { type: Object, default: undefined },
	columnOptions: { type: Array, default: () => [] },
})
const emit = defineEmits(['update:modelValue'])

const valuePropPassed = computed(() => props.value !== undefined)
const column = computed({
	get: () =>
		// hacky: because unless the exact matching object is passed
		// the combobox doesn't select the value
		// so, we find the matching object from the columnOptions using the value
		// this way, as long actual value is passed, it will select the correct option
		findOptionByValue(
			columns.value,
			valuePropPassed.value ? getColumnValue(props.value) : getColumnValue(props.modelValue)
		),
	set: (option) => {
		const column = findOptionByValue(columns.value, option.value)
		emit('update:modelValue', {
			...column,
			...option,
			alias: column.alias || props.modelValue.alias,
			order: column.order || props.modelValue.order,
			granularity: column.granularity || props.modelValue.granularity,
			aggregation: column.aggregation || props.modelValue.aggregation,
			format: column.format || props.modelValue.format,
			expression: column.expression || props.modelValue.expression,
		})
	},
})

function findOptionByValue(columns, value) {
	return columns.find((c) => value == getColumnValue(c))
}

const dataSourceTables = ref([])
watch(
	() => props.tables,
	async () => {
		if (!props.tables?.length) return []
		const tablePromises = []
		props.tables.forEach((table) => {
			if (!table.table) return Promise.resolve()
			tablePromises.push(
				useDataSourceTable({
					data_source: props.data_source,
					table: table.table,
				})
			)
		})
		dataSourceTables.value = await Promise.all(tablePromises)
	},
	{ immediate: true }
)

function getColumnValue(column) {
	if (!column) return
	if (column.description == 'local') return column.alias
	return column.expression?.raw || `${column.table}.${column.column}`
}
function filterFn(col, currIndex, self) {
	if (!col) return false
	const otherIndex = self.findIndex((c) => getColumnValue(c) === getColumnValue(col))
	return otherIndex === currIndex && (!props.columnFilter || props.columnFilter(col))
}

const columns = computed(() => {
	const columnOptions = props.columnOptions.filter(filterFn)
	if (!dataSourceTables.value?.length) return columnOptions
	const source_table_columns = dataSourceTables.value
		.map((d) => d.doc?.columns)
		.flat()
		.filter(filterFn)
	return columnOptions.concat(source_table_columns)
})
const columnOptions = computed(() => {
	if (!columns.value?.length) return []
	return columns.value.map((c) => {
		return {
			label: c.label || c.alias,
			description: c.description || c.table,
			value: getColumnValue(c),
		}
	})
})
</script>

<template>
	<div>
		<InputWithPopover
			v-model="column"
			:items="columnOptions"
			placeholder="Column"
		></InputWithPopover>
	</div>
</template>
