<script setup>
import { computed } from 'vue'
import ColumnSelector from './ColumnSelector.vue'

const emit = defineEmits(['update:modelValue'])
const props = defineProps({
	modelValue: Array,
	placeholder: String,
	tables: Array,
	data_source: String,
	columnFilter: Function,
})
const selectedColumns = computed({
	get: () => props.modelValue,
	set: (value) => emit('update:modelValue', value),
})
</script>

<template>
	<Suspense v-for="(column, index) in selectedColumns" :key="index">
		<ColumnSelector
			class="flex rounded-lg border border-gray-300 text-gray-800"
			:data_source="props.data_source"
			:tables="props.tables"
			:columnFilter="props.columnFilter"
			v-model="column.column"
		/>
	</Suspense>
</template>
