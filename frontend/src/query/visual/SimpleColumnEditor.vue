<script setup>
import { AGGREGATIONS, FIELDTYPES, GRANULARITIES } from '@/utils'
import { computed, defineProps, inject, reactive } from 'vue'
import { NEW_COLUMN } from './constants'

const emit = defineEmits(['save', 'discard', 'remove'])
const props = defineProps({ column: Object })

const assistedQuery = inject('assistedQuery')
const query = inject('query')

const column = reactive({
	...NEW_COLUMN,
	...props.column,
})
if (column.table && column.column && !column.value) {
	column.value = `${column.table}.${column.column}`
}
if (!column.aggregation) {
	column.aggregation = 'group by'
}

function onColumnChange(option) {
	const selectedOption = { ...option }
	column.table = selectedOption.table
	column.table_label = selectedOption.table_label
	column.column = selectedOption.column
	column.label = selectedOption.label
	column.alias = selectedOption.label
	column.type = selectedOption.type
	column.value = selectedOption.value
}

const isValidColumn = computed(() => {
	if (!column.label || !column.type) return false
	if (column.table && column.column) return true
	return false
})

function onAggregationChange(aggregation) {
	column.aggregation = aggregation.value
	const number_agg = [
		'count',
		'sum',
		'avg',
		'cumulative sum',
		'cumulative count',
		'distinct',
		'distinct_count',
		'min',
		'max',
	]
	if (number_agg.includes(aggregation.value)) {
		column.type = 'Decimal'
	}
}
</script>

<template>
	<div class="flex flex-col gap-4 p-4">
		<div class="space-y-1">
			<span class="text-sm font-medium text-gray-700">Aggregation</span>
			<Autocomplete
				:modelValue="column.aggregation.toLowerCase()"
				placeholder="Aggregation"
				:options="AGGREGATIONS"
				@update:modelValue="onAggregationChange"
			/>
		</div>
		<div class="space-y-1">
			<span class="text-sm font-medium text-gray-700">Column</span>
			<Autocomplete
				:modelValue="column"
				bodyClasses="w-[18rem]"
				placeholder="Column"
				@update:modelValue="onColumnChange"
				:options="assistedQuery.groupedColumnOptions"
				@update:query="assistedQuery.fetchColumnOptions"
			/>
		</div>
		<div class="space-y-1">
			<span class="text-sm font-medium text-gray-700">Label</span>
			<FormControl
				type="text"
				class="w-full"
				v-model="column.label"
				placeholder="Label"
				@update:modelValue="(val) => (column.alias = val)"
			/>
		</div>
		<div v-if="FIELDTYPES.DATE.includes(column.type)" class="space-y-1">
			<span class="text-sm font-medium text-gray-700">Date Format</span>
			<Autocomplete
				:modelValue="column.granularity"
				placeholder="Date Format"
				:options="GRANULARITIES"
				@update:modelValue="(op) => (column.granularity = op.value)"
			/>
		</div>
		<div class="flex justify-between">
			<Button variant="outline" @click="emit('discard')"> Discard </Button>
			<div class="flex gap-2">
				<Button variant="outline" theme="red" @click="emit('remove')">Remove</Button>
				<Button variant="solid" :disabled="!isValidColumn" @click="emit('save', column)">
					Save
				</Button>
			</div>
		</div>
	</div>
</template>
