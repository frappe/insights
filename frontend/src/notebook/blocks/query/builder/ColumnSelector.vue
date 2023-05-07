<script setup>
import { useDataSourceTable } from '@/datasource/useDataSource'
import { computed, ref, watch } from 'vue'
import InputWithPopover from './InputWithPopover.vue'
const props = defineProps({
	data_source: String,
	tables: Array,
	modelValue: Object,
	columnFilter: Function,
})
const emit = defineEmits(['update:modelValue'])
const column = computed({
	get: () => props.modelValue,
	set: (value) => emit('update:modelValue', value),
})

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
		.slice(0, 50)
		.filter((column, index, self) => {
			return (
				column &&
				self.findIndex((c) => c && c.column === column.column) === index &&
				(!props.columnFilter || props.columnFilter(column))
			)
		})
		.map((column) => {
			return {
				column: column.column,
				type: column.type,
				table: column.table,
				value: column.column,
				label: column.label,
			}
		})
})
</script>

<template>
	<div>
		<InputWithPopover
			v-model="column"
			:items="columns"
			placeholder="Pick a column"
		></InputWithPopover>
	</div>
</template>
