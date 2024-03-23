<script setup lang="ts">
import { FIELDTYPES } from '@/utils'
import { debounce } from 'frappe-ui'
import { computed, inject, onMounted, ref, watch } from 'vue'
import { FilterCondition } from '../FiltersSelectorDialog.vue'
import { QueryPipeline } from '../useQueryPipeline'
import DatePickerControl from './DatePickerControl.vue'

const filter = defineModel<FilterCondition>({ required: true })

onMounted(() => {
	if (valueSelectorType.value === 'select') fetchColumnValues()
})

function onColumnChange(column_name: string) {
	filter.value.column_name = column_name
	filter.value.operator = operatorOptions.value[0].value
	filter.value.value = undefined
	if (valueSelectorType.value === 'select') {
		filter.value.value = []
		fetchColumnValues()
	}
}

const operatorOptions = computed(() => {
	const type = columnType.value
	const options = [] as { label: string; value: FilterOperator }[]
	if (FIELDTYPES.TEXT.includes(type)) {
		options.push({ label: 'is', value: 'in' }) // value selector
		options.push({ label: 'is not', value: 'not_in' }) // value selector
		options.push({ label: 'contains', value: 'contains' }) // text
		options.push({ label: 'does not contain', value: 'not_contains' }) // text
		options.push({ label: 'starts with', value: 'starts_with' }) // text
		options.push({ label: 'ends with', value: 'ends_with' }) // text
		options.push({ label: 'is empty', value: 'is_set' }) // no value
		options.push({ label: 'is not empty', value: 'is_not_set' }) // no value
	}
	if (FIELDTYPES.NUMBER.includes(type)) {
		options.push({ label: '=', value: '=' }) // number
		options.push({ label: '!=', value: '!=' }) // number
		options.push({ label: '>', value: '>' }) // number
		options.push({ label: '>=', value: '>=' }) // number
		options.push({ label: '<', value: '<' }) // number
		options.push({ label: '<=', value: '<=' }) // number
	}
	if (FIELDTYPES.DATE.includes(type)) {
		options.push({ label: 'is', value: '=' }) // date
		options.push({ label: 'is not', value: '!=' }) // date
		options.push({ label: 'is before', value: '>' }) // date
		options.push({ label: 'is on or before', value: '>=' }) // date
		options.push({ label: 'is after', value: '<' }) // date
		options.push({ label: 'is on or after', value: '<=' }) // date
		options.push({ label: 'is between', value: 'between' }) // date range
	}
	return options
})

function onOperatorChange(operator: FilterOperator) {
	filter.value.operator = operator
	filter.value.value = undefined
}

const columnType = computed(() => {
	const col = queryPipeline.results.columns.find((c) => c.name === filter.value.column_name)
	if (!col) return 'String'
	return col.type
})

const valueSelectorType = computed(() => {
	if (!filter.value.column_name || !filter.value.operator) return 'text' // default to text
	if (['is_set', 'is_not_set'].includes(filter.value.operator)) return

	const type = columnType.value
	if (FIELDTYPES.TEXT.includes(type)) {
		return ['in', 'not_in'].includes(filter.value.operator) ? 'select' : 'text'
	}
	if (FIELDTYPES.NUMBER.includes(type)) return 'number'
	if (FIELDTYPES.DATE.includes(type)) {
		return filter.value.operator === 'between' ? 'date_range' : 'date'
	}
	return 'text'
})

const queryPipeline = inject('queryPipeline') as QueryPipeline
const distinctColumnValues = ref<any[]>([])
const fetchingValues = ref(false)
const fetchColumnValues = debounce((query: string) => {
	fetchingValues.value = true
	queryPipeline
		.getDistinctColumnValues(filter.value.column_name, query)
		.then((values: string[]) => (distinctColumnValues.value = values))
		.finally(() => (fetchingValues.value = false))
}, 300)

watch(
	() => filter.value.value,
	(filter_value: FilterValue) => {
		if (!filter.value.column_name || !filter.value.operator) {
			filter.value.isValid = false
			return
		}

		// if selector type is none, no need to validate
		if (!valueSelectorType.value) {
			filter.value.isValid = true
			return
		}

		if (!filter_value) {
			filter.value.isValid = false
			return
		}

		// for number, validate if it's a number
		if (FIELDTYPES.NUMBER.includes(columnType.value)) {
			filter.value.isValid = !isNaN(filter_value as any)
		}

		// for text,
		// if it's a select, validate if it's an array of strings
		// if it's a text, validate if it's a string
		if (FIELDTYPES.TEXT.includes(columnType.value)) {
			if (valueSelectorType.value === 'select') {
				filter.value.isValid = Boolean(
					Array.isArray(filter_value) &&
						filter_value.length &&
						filter_value.every((v: any) => typeof v === 'string')
				)
			} else {
				filter.value.isValid = typeof filter_value === 'string'
			}
		}

		// for date,
		// if it's a date, validate if it's a date string
		// if it's a date range, validate if it's an array of 2 date strings
		if (FIELDTYPES.DATE.includes(columnType.value)) {
			if (valueSelectorType.value === 'date') {
				filter.value.isValid = typeof filter_value === 'string'
			} else if (valueSelectorType.value === 'date_range') {
				filter.value.isValid = Boolean(
					Array.isArray(filter_value) &&
						filter_value.length === 2 &&
						filter_value.every((v: any) => typeof v === 'string')
				)
			}
		}
	}
)
</script>

<template>
	<div class="flex flex-1 gap-2">
		<div id="column_name" class="!min-w-[140px] flex-1 flex-shrink-0">
			<Autocomplete
				placeholder="Column"
				:modelValue="filter.column_name"
				:options="queryPipeline.results.columnOptions"
				@update:modelValue="onColumnChange($event.value)"
			/>
		</div>
		<div id="operator" class="!min-w-[100px] flex-1">
			<FormControl
				type="select"
				placeholder="Operator"
				:modelValue="filter.operator"
				:options="operatorOptions"
				@update:modelValue="onOperatorChange($event)"
			/>
		</div>
		<div id="value" class="!min-w-[140px] flex-1 flex-shrink-0">
			<FormControl
				v-if="valueSelectorType === 'text'"
				v-model="filter.value"
				placeholder="eg. foo"
			/>
			<FormControl
				v-else-if="valueSelectorType === 'number'"
				type="number"
				:modelValue="filter.value"
				placeholder="eg. 42"
				@update:modelValue="filter.value = Number($event)"
			/>
			<DatePickerControl
				v-else-if="valueSelectorType === 'date'"
				placeholder="Select Date"
				:modelValue="[filter.value as string]"
				@update:modelValue="filter.value = $event[0]"
			/>
			<DatePickerControl
				v-else-if="valueSelectorType === 'date_range'"
				:range="true"
				v-model="(filter.value as string[])"
				placeholder="Select Date"
			/>
			<Autocomplete
				v-else-if="valueSelectorType === 'select'"
				class="max-w-[200px]"
				placeholder="Value"
				:multiple="true"
				:modelValue="filter.value || []"
				:options="distinctColumnValues"
				@update:query="fetchColumnValues"
				@update:modelValue="filter.value = $event.map((v: any) => v.value)"
			/>
		</div>
	</div>
</template>
