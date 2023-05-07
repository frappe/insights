<script setup>
import { useDataSource } from '@/datasource/useDataSource'
import { computed, ref } from 'vue'
import InputWithPopover from './InputWithPopover.vue'

const emit = defineEmits(['update:modelValue'])
const props = defineProps({
	data_source: String,
	modelValue: Object,
	tableOptions: Array,
})
const table = computed({
	get: () => props.modelValue,
	set: (value) => emit('update:modelValue', value),
})
let tables = ref(props.tableOptions || [])
if (!props.tableOptions) {
	const dataSource = useDataSource(props.data_source)
	dataSource.fetch_tables()
	tables = computed(() => {
		return dataSource.tables
			.slice(0, 50)
			.filter((t) => !t.hidden)
			.map((table) => {
				return {
					table: table.table,
					value: table.table,
					label: table.label,
				}
			})
	})
}
</script>

<template>
	<div>
		<InputWithPopover
			v-model="table"
			:items="tables"
			placeholder="Pick a table"
		></InputWithPopover>
	</div>
</template>
