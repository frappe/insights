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
	get: () => (valuePropPassed.value ? props.value : props.modelValue),
	set: (option) => {
		// since combobox resets any object to empty object, we need to find the original object
		const column = findByValue(columns.value, option.value)
		emit('update:modelValue', { ...column, ...option })
	},
})

function findByValue(columns, value) {
	return columns.find((c) => value == c.expression?.raw || value == `${c.table}.${c.column}`)
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

const columns = computed(() => {
	if (!dataSourceTables.value?.length) return []
	return dataSourceTables.value
		.map((d) => d.doc?.columns)
		.flat()
		.concat(props.columnOptions)
		.reverse() // to show the passed column options first
		.filter((col, currIndex, self) => {
			if (!col) return false
			const otherIndex = self.findIndex((c) =>
				c.expression
					? c.expression.raw === col.expression?.raw
					: c && c.column === col.column && c.table === col.table
			)
			return otherIndex === currIndex && (!props.columnFilter || props.columnFilter(col))
		})
})
const columnOptions = computed(() => {
	if (!columns.value?.length) return []
	return columns.value.map((c) => {
		return {
			label: c.label,
			description: c.description || c.table,
			value: c.expression?.raw || `${c.table}.${c.column}`,
		}
	})
})
</script>

<template>
	<div>
		<InputWithPopover
			v-model="column"
			:items="columnOptions"
			placeholder="Pick a column"
		></InputWithPopover>
	</div>
</template>
