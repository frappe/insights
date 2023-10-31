<script setup>
import DatePicker from '@/components/Controls/DatePicker.vue'
import DateRangePicker from '@/components/Controls/DateRangePicker.vue'
import TimespanPicker from '@/components/Controls/TimespanPicker.vue'
import { FIELDTYPES, formatDate, getOperatorOptions } from '@/utils'
import { whenever } from '@vueuse/core'
import { FormControl, call, debounce } from 'frappe-ui'
import { computed, defineProps, inject, reactive, ref, watch } from 'vue'
import { NEW_FILTER } from './constants'

const emit = defineEmits(['save', 'discard', 'remove'])
const props = defineProps({ filter: Object })

const builder = inject('builder')
const query = inject('query')

const filter = reactive({
	...NEW_FILTER,
	...props.filter,
})

const operatorOptions = computed(() => {
	const options = getOperatorOptions(filter.column.type)
	return options
		.filter((option) => option.value !== 'is')
		.concat([
			{ label: 'is set', value: 'is_set' },
			{ label: 'is not set', value: 'is_not_set' },
		])
})
if (!filter.operator?.value) {
	filter.operator = operatorOptions.value[0]
}
watch(
	() => filter.operator.value,
	(newVal, oldVal) => {
		if (newVal !== oldVal) filter.value = {}
	}
)

function onColumnChange(option) {
	filter.column.table = option.table
	filter.column.table_label = option.table_label
	filter.column.column = option.column
	filter.column.label = option.label
	filter.column.alias = option.alias || option.label
	filter.column.type = option.type
}

const operator = computed(() => filter.operator?.value)
const isExpression = computed(() => filter.column?.expression?.raw)
const isString = computed(() => filter.column?.type === 'String')
const isDate = computed(() => FIELDTYPES.DATE.includes(filter.column?.type))
const isEqualityCheck = computed(() => ['=', '!=', 'in', 'not_in'].includes(operator.value))
const isNullCheck = computed(() => ['is_set', 'is_not_set'].includes(operator.value))

const selectorType = computed(() => {
	if (isNullCheck.value) return 'none'

	if (isDate.value && operator.value === 'between') return 'datepickerrange'
	if (isDate.value && operator.value === 'timespan') return 'timespanpicker'
	if (isDate.value) return 'datepicker'

	if (!isExpression.value && isString.value && isEqualityCheck.value) return 'combobox'
	return 'text'
})

function onDateRangeChange(dates) {
	filter.value = {
		value: dates,
		label: dates
			.split(',')
			.map((date) => formatDate(date))
			.join(' to '),
	}
}

function onDateChange(date) {
	filter.value = {
		value: date,
		label: formatDate(date),
	}
}

const isMultiValue = computed(() => ['in', 'not_in'].includes(filter.operator?.value))
const columnValues = ref([])
const fetchingColumnValues = ref(false)
const checkAndFetchColumnValues = debounce(async function (search_text = '') {
	if (!isEqualityCheck.value) return
	if (filter.column?.type == 'String' && builder.data_source) {
		const URL = 'insights.api.data_sources.fetch_column_values'
		fetchingColumnValues.value = true
		const values = await call(URL, {
			data_source: builder.data_source,
			table: filter.column.table,
			column: filter.column.column,
			search_text,
		})
		columnValues.value = values.map((value) => ({ label: value, value }))
		// prepend the selected value to the list
		if (Array.isArray(filter.value.value)) {
			// filter.value = {label: '2 selected', value: [{ label: '', value: ''}, ...]}
			filter.value.value.forEach((selectedOption) => {
				if (!columnValues.value.find((v) => v.value === selectedOption.value)) {
					columnValues.value.unshift(selectedOption)
				}
			})
		}
		fetchingColumnValues.value = false
	}
}, 300)
whenever(
	() => selectorType.value == 'combobox',
	() => checkAndFetchColumnValues(),
	{ immediate: true }
)
function onColumnValueChange(value) {
	filter.value = !isMultiValue.value
		? value
		: {
				label: `${value.length} values`,
				value: value,
		  }
}
</script>

<template>
	<div class="flex flex-col gap-4 p-4">
		<div class="space-y-1">
			<span class="text-sm font-medium text-gray-700">Column</span>
			<Autocomplete
				:modelValue="{
					...filter.column,
					value: `${filter.column.table}.${filter.column.column}`,
				}"
				placeholder="Column"
				:options="query.columnOptions"
				@update:modelValue="onColumnChange"
			/>
		</div>
		<div class="space-y-1">
			<span class="text-sm font-medium text-gray-700">Operator</span>
			<Autocomplete
				:modelValue="filter.operator"
				placeholder="Operator"
				:options="operatorOptions"
				@update:modelValue="filter.operator = $event"
			/>
		</div>
		<div class="space-y-1">
			<span v-if="selectorType !== 'none'" class="text-sm font-medium text-gray-700">
				Value
			</span>
			<Autocomplete
				v-if="selectorType === 'combobox'"
				placeholder="Value"
				:multiple="isMultiValue"
				:modelValue="filter.value.value"
				:options="columnValues"
				@update:query="checkAndFetchColumnValues"
				@update:modelValue="onColumnValueChange"
			/>
			<TimespanPicker
				v-if="selectorType === 'timespanpicker'"
				v-model="filter.value"
				placeholder="Value"
			/>
			<DateRangePicker
				v-if="selectorType === 'datepickerrange'"
				:value="filter.value.value"
				:formatter="formatDate"
				@change="onDateRangeChange($event)"
			/>
			<DatePicker
				v-if="selectorType === 'datepicker'"
				:value="filter.value.value"
				:formatter="formatDate"
				@change="onDateChange($event)"
			/>
			<FormControl
				v-if="selectorType === 'text'"
				type="text"
				autocomplete="off"
				placeholder="Value"
				:modelValue="filter.value.value"
				@update:modelValue="filter.value.value = $event"
			/>
		</div>
		<div class="flex justify-between">
			<Button variant="outline" @click="emit('discard')">Discard</Button>
			<div class="flex gap-2">
				<Button variant="outline" theme="red" @click="emit('remove')">Remove</Button>
				<Button variant="solid" @click="emit('save', filter)">Save</Button>
			</div>
		</div>
	</div>
</template>
