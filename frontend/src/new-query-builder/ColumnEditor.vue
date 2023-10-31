<script setup>
import { AGGREGATIONS, GRANULARITIES, FIELDTYPES } from '@/utils'
import { defineProps, inject, reactive } from 'vue'
import { NEW_COLUMN } from './constants'

const emit = defineEmits(['save', 'discard', 'remove'])
const props = defineProps({ column: Object })

const builder = inject('builder')
const query = inject('query')

const activeColumn = reactive({
	...NEW_COLUMN,
	...props.column,
})

if (!activeColumn.aggregation) {
	activeColumn.aggregation = 'group by'
}

function onColumnChange(option) {
	activeColumn.table = option.table
	activeColumn.table_label = option.table_label
	activeColumn.column = option.column
	activeColumn.label = option.label
	activeColumn.alias = option.alias || option.label
	activeColumn.type = option.type
}
</script>

<template>
	<div class="flex flex-col gap-4 p-4">
		<div class="space-y-1">
			<span class="text-sm font-medium text-gray-700">Aggregation</span>
			<Autocomplete
				:modelValue="activeColumn.aggregation"
				placeholder="Aggregation"
				:options="AGGREGATIONS"
				@update:modelValue="(op) => (activeColumn.aggregation = op.val)"
			/>
		</div>
		<div class="space-y-1">
			<span class="text-sm font-medium text-gray-700">Column</span>
			<Autocomplete
				:modelValue="{
					...activeColumn,
					value: `${activeColumn.table}.${activeColumn.column}`,
				}"
				placeholder="Column"
				:options="query.columnOptions"
				@update:modelValue="onColumnChange"
			/>
		</div>
		<div v-if="FIELDTYPES.DATE.includes(activeColumn.type)" class="space-y-1">
			<span class="text-sm font-medium text-gray-700">Format</span>
			<Autocomplete
				:modelValue="activeColumn.granularity"
				placeholder="Date Format"
				:options="GRANULARITIES"
				@update:modelValue="(op) => (activeColumn.granularity = op.val)"
			/>
		</div>
		<div class="flex justify-between">
			<Button variant="outline" @click="emit('discard')">Discard</Button>
			<div class="flex gap-2">
				<Button variant="outline" theme="red" @click="emit('remove')">Remove</Button>
				<Button variant="solid" @click="emit('save', activeColumn)">Save</Button>
			</div>
		</div>
	</div>
</template>
