<script setup lang="ts">
import { debounce } from 'frappe-ui'
import { computed, onMounted, ref } from 'vue'
import { flattenOptions } from '../../helpers'
import {
	ColumnOption,
	FilterOperator,
	FilterRule,
	GroupedColumnOption,
} from '../../types/query.types'
import { column } from '../helpers'
import useQuery from '../query'
import DatePickerControl from './DatePickerControl.vue'
import { getFilterType, getOperatorOptions, getValueSelectorType } from './filter_utils'
import RelativeDatePickerControl from './RelativeDatePickerControl.vue'

const filter = defineModel<FilterRule>({ required: true })
const props = defineProps<{
	columnOptions: ColumnOption[] | GroupedColumnOption[]
}>()

onMounted(() => {
	if (valueSelectorType.value === 'select') fetchColumnValues()
})

function onColumnChange(column_name: string) {
	filter.value.column = column(column_name)
	filter.value.operator = operatorOptions.value[0]?.value
	filter.value.value = undefined
	if (valueSelectorType.value === 'select') {
		filter.value.value = []
		fetchColumnValues()
	}
}

const columnType = computed(() => {
	if (!props.columnOptions?.length) return
	if (!filter.value.column.column_name) return
	const options = flattenOptions(props.columnOptions) as ColumnOption[]
	const col = options.find((c) => c.value === filter.value.column.column_name)
	if (!col) throw new Error(`Column not found: ${filter.value.column.column_name}`)
	return col.data_type
})

const operatorOptions = computed(() => {
	if (!columnType.value) return []
	return getOperatorOptions(getFilterType(columnType.value))
})

function onOperatorChange(operator: FilterOperator) {
	filter.value.operator = operator
	filter.value.value = undefined
}

const valueSelectorType = computed(() => {
	if (!filter.value.column.column_name || !filter.value.operator || !columnType.value) {
		return
	}
	return getValueSelectorType(filter.value.operator, getFilterType(columnType.value))
})

const distinctColumnValues = ref<any[]>([])
const fetchingValues = ref(false)
const fetchColumnValues = debounce((searchTxt: string) => {
	const options = flattenOptions(props.columnOptions) as ColumnOption[]
	const option = options.find((c) => c.value === filter.value.column.column_name)
	if (!option?.query) {
		fetchingValues.value = false
		console.warn('Query not found for column:', filter.value.column.column_name)
		return
	}
	// only for dashboard filters
	// if column_name is {sep}query{sep}.{sep}column_name{sep} extract column_name
	const sep = '`'
	const pattern = new RegExp(`${sep}([^${sep}]+)${sep}\\.${sep}([^${sep}]+)${sep}`)
	const match = pattern.exec(filter.value.column.column_name)
	const column_name = match ? match[2] : filter.value.column.column_name

	fetchingValues.value = true
	return useQuery(option.query)
		.getDistinctColumnValues(column_name, searchTxt)
		.then((values: string[]) => (distinctColumnValues.value = values))
		.finally(() => (fetchingValues.value = false))
}, 300)
</script>

<template>
	<div class="flex flex-1 gap-2">
		<div id="column_name" class="!min-w-[140px] flex-1 flex-shrink-0">
			<Autocomplete
				placeholder="Column"
				:modelValue="filter.column.column_name"
				:options="props.columnOptions"
				@update:modelValue="onColumnChange($event?.value)"
			/>
		</div>
		<div id="operator" class="!min-w-[100px] flex-1">
			<FormControl
				type="select"
				placeholder="Operator"
				:disabled="!columnType"
				:modelValue="filter.operator"
				:options="operatorOptions"
				@update:modelValue="onOperatorChange($event)"
			/>
		</div>
		<div id="value" class="!min-w-[140px] flex-1 flex-shrink-0">
			<FormControl
				v-if="valueSelectorType === 'text'"
				v-model="filter.value"
				placeholder="Value"
				autocomplete="off"
			/>
			<FormControl
				v-else-if="valueSelectorType === 'number'"
				type="number"
				:modelValue="filter.value"
				placeholder="Value"
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
			<RelativeDatePickerControl
				v-else-if="valueSelectorType === 'relative_date'"
				v-model="(filter.value as string)"
				placeholder="Relative Date"
			/>
			<Autocomplete
				v-else-if="valueSelectorType === 'select'"
				class="max-w-[200px]"
				placeholder="Value"
				:multiple="true"
				:modelValue="filter.value || []"
				:options="distinctColumnValues"
				:loading="fetchingValues"
				@update:query="fetchColumnValues"
				@update:modelValue="filter.value = $event?.map((v: any) => v.value) || []"
			/>
			<FormControl v-else disabled />
		</div>
	</div>
</template>
