<template>
	<div class="relative flex flex-col space-y-3">
		<div class="space-y-1 text-sm">
			<div class="text-gray-700">Aggregation Type</div>
			<Autocomplete
				v-model="simpleColumn.aggType"
				:options="aggregations"
				placeholder="Select aggregation type"
				@update:modelValue="onTypeSelect"
			/>
		</div>
		<div v-if="columnNeeded" class="space-y-1 text-sm">
			<div class="text-gray-700">Column</div>
			<Autocomplete
				v-model="simpleColumn.column"
				:options="filteredColumns"
				placeholder="Select a column..."
				:emptyText="requiresNumberColumn ? 'No number columns' : 'No columns'"
				@update:modelValue="onColumnSelect"
			/>
		</div>
		<div class="space-y-1 text-sm">
			<div class="text-gray-700">Label</div>
			<Input
				type="text"
				v-model="simpleColumn.label"
				class="placeholder:text-sm"
				placeholder="Enter a label..."
			/>
		</div>

		<div v-if="showDateFormatOptions" class="space-y-1 text-sm">
			<div class="text-gray-700">Date Format</div>
			<Autocomplete
				v-model="simpleColumn.dateFormat"
				:options="dateFormats.map((f) => ({ ...f, description: f.value }))"
				placeholder="Select a date format..."
				@update:modelValue="selectDateFormat"
			/>
		</div>
		<div class="space-y-1 text-sm">
			<div class="text-gray-700">Sort</div>
			<Input
				type="select"
				v-model="simpleColumn.order_by"
				:options="[
					{
						label: '',
						value: '',
					},
					{
						label: 'Ascending',
						value: 'asc',
					},
					{
						label: 'Descending',
						value: 'desc',
					},
				]"
				class="placeholder:text-sm"
				placeholder="Enter a label..."
			/>
		</div>
		<div class="sticky bottom-0 mt-3 flex justify-end space-x-2 bg-white pt-1">
			<Button
				v-if="props.column.name"
				class="text-red-500"
				variant="outline"
				@click="removeMetric"
			>
				Remove
			</Button>
			<Button @click="addOrEditColumn" variant="solid" :disabled="applyDisabled">
				{{ props.column.name ? 'Update' : 'Add ' }}
			</Button>
		</div>
	</div>
</template>

<script setup>
import { FIELDTYPES, isEmptyObj } from '@/utils'

import { dateFormats } from '@/utils/format'

import { computed, inject, reactive, ref } from 'vue'

const query = inject('query')

const emit = defineEmits(['column-select', 'close'])
const props = defineProps({
	column: {
		type: Object,
		default: {},
	},
})

const aggregations = ref([
	{
		label: 'No Aggregation',
		value: '',
	},
	{
		label: 'Group by',
		value: 'Group By',
	},
	{
		label: 'Count of Records',
		value: 'Count',
	},
	{
		label: 'Sum of',
		value: 'Sum',
	},
	{
		label: 'Avg of',
		value: 'Avg',
	},
	{
		label: 'Min of',
		value: 'Min',
	},
	{
		label: 'Max of',
		value: 'Max',
	},
	{
		label: 'Cumulative Count of Records',
		value: 'Cumulative Count',
	},
	{
		label: 'Cumulative Sum of',
		value: 'Cumulative Sum',
	},
])

const simpleColumn = reactive({
	// since props.column comes from doc.columns, it doesn't have value property
	// value is needed to show the selected column in the autocomplete
	column: { ...props.column, value: props.column.column },
	label: props.column.label,
	order_by: props.column.order_by,
	aggType: aggregations.value.find((t) => {
		return t.value == props.column.aggregation
	}),
	dateFormat:
		dateFormats.find((t) => {
			return t.value == props.column.format_option?.date_format
		}) || {},
})
if (!simpleColumn.aggType) simpleColumn.aggType = { label: 'No Aggregation', value: '' }

const columnNeeded = computed(() => {
	return simpleColumn.aggType.label && !simpleColumn.aggType.label?.includes('Count')
})
const applyDisabled = computed(() => {
	return (
		!simpleColumn.label ||
		(columnNeeded.value && isEmptyObj(simpleColumn.column)) ||
		(showDateFormatOptions.value && isEmptyObj(simpleColumn.dateFormat))
	)
})

const columnOptions = query.columns.options
const requiresNumberColumn = computed(
	() =>
		simpleColumn.aggType.value === 'Sum' ||
		simpleColumn.aggType.value === 'Avg' ||
		simpleColumn.aggType.value === 'Min' ||
		simpleColumn.aggType.value === 'Max' ||
		simpleColumn.aggType.value === 'Cumulative Sum'
)
const filteredColumns = computed(() =>
	requiresNumberColumn.value
		? columnOptions?.filter((c) => FIELDTYPES.NUMBER.includes(c.type))
		: columnOptions
)

const showDateFormatOptions = computed(() =>
	['Date', 'Datetime'].includes(simpleColumn.column.type)
)
function selectDateFormat(option) {
	simpleColumn.column.format_option = {
		date_format: typeof option === 'string' ? option : option.value,
	}
}

function onTypeSelect(option) {
	simpleColumn.aggType = option ? option : {}
	simpleColumn.label = simpleColumn.aggType.label
}
function onColumnSelect(option) {
	simpleColumn.column = option ? option : {}
	simpleColumn.column.name = props.column.name
	if (simpleColumn.aggType.value) {
		simpleColumn.label = simpleColumn.aggType.label + ' ' + simpleColumn.column.label
	} else {
		simpleColumn.label = simpleColumn.column.label
	}
}

function addOrEditColumn() {
	if (applyDisabled.value) return
	const editing = props.column?.name

	const column = {
		...simpleColumn.column,
		aggregation: simpleColumn.aggType.value,
		label: simpleColumn.label,
		order_by: simpleColumn.order_by,
		format_option: showDateFormatOptions.value ? simpleColumn.column.format_option : null,
	}

	if (!columnNeeded.value) {
		column.column = 'count'
		column.type = 'Integer'
		column.table = query.tables.data[0].table
		column.table_label = query.tables.data[0].table_label
	}

	if (editing) {
		query.updateColumn.submit({ column })
	} else {
		query.addColumn.submit({ column })
	}
	emit('close')
}

function removeMetric() {
	query.removeColumn.submit({ column: simpleColumn.column })
	emit('close')
}
</script>
