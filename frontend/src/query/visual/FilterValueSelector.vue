<script setup>
import DatePicker from '@/components/Controls/DatePicker.vue'
import DateRangePicker from '@/components/Controls/DateRangePicker.vue'
import TimespanPicker from '@/components/Controls/TimespanPicker.vue'
import { FIELDTYPES, formatDate } from '@/utils'
import { FormControl, call, debounce } from 'frappe-ui'
import { computed, defineProps, ref, watch } from 'vue'

const props = defineProps({
	label: { type: String, required: false, default: 'Value' },
	column: { type: Object, required: true },
	operator: { type: Object, required: true },
	dataSource: { type: String, required: true },
})
const filterValue = defineModel()

const operator = computed(() => props.operator?.value)
const isExpression = computed(() => props.column?.expression?.raw)
const isString = computed(() => props.column?.type === 'String')
const isDate = computed(() => FIELDTYPES.DATE.includes(props.column?.type))
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
	filterValue.value = {
		value: dates,
		label: dates
			.split(',')
			.map((date) => formatDate(date))
			.join(' to '),
	}
}

function onDateChange(date) {
	filterValue.value = {
		value: date,
		label: formatDate(date),
	}
}
const isMultiValue = computed(() => ['in', 'not_in'].includes(operator.value))
const columnValues = ref([])
const fetchingColumnValues = ref(false)
const checkAndFetchColumnValues = debounce(async function (search_text = '') {
	if (!props.column || !operator.value) return
	if (!['=', '!=', 'in', 'not_in'].includes(operator.value)) return
	if (!props.column.table || !props.column.column || !props.dataSource) return
	if (props.column?.type == 'String' && props.dataSource) {
		const URL = 'insights.api.data_sources.fetch_column_values'
		fetchingColumnValues.value = true
		const values = await call(URL, {
			data_source: props.dataSource,
			table: props.column.table,
			column: props.column.column,
			search_text,
		})
		columnValues.value = values.map((value) => ({ label: value, value }))
		// prepend the selected value to the list
		if (Array.isArray(filterValue.value?.value)) {
			// filterValue.value = {label: '2 selected', value: [{ label: '', value: ''}, ...]}
			filterValue.value.forEach((selectedOption) => {
				if (!columnValues.value.find((v) => v.value === selectedOption.value)) {
					columnValues.value.unshift(selectedOption)
				}
			})
		}
		fetchingColumnValues.value = false
	}
}, 300)

watch(
	() => {
		return {
			column: `${props.column.table}.${props.column.column}`,
			operator: operator.value,
		}
	},
	(newVal, oldVal) => {
		if (!newVal.column || !newVal.operator) return
		if (newVal.column === oldVal?.column && newVal.operator === oldVal?.operator) return
		if (selectorType.value !== 'combobox') return
		checkAndFetchColumnValues()
	},
	{ deep: true, immediate: true }
)

function onOptionSelect(value) {
	filterValue.value = !isMultiValue.value
		? value
		: {
				label: `${value.length} values`,
				value: value,
		  }
}
</script>

<template>
	<div v-if="selectorType != 'none'" class="space-y-1">
		<span class="mb-2 block text-sm leading-4 text-gray-700"> {{ props.label }} </span>
		<Autocomplete
			v-if="selectorType === 'combobox'"
			:key="isMultiValue"
			placeholder="Value"
			:multiple="isMultiValue"
			:modelValue="filterValue?.value"
			:options="columnValues"
			@update:query="checkAndFetchColumnValues"
			@update:modelValue="onOptionSelect"
		/>
		<TimespanPicker
			v-if="selectorType === 'timespanpicker'"
			v-model="filterValue"
			placeholder="Value"
		/>
		<DateRangePicker
			v-if="selectorType === 'datepickerrange'"
			:value="filterValue?.value"
			:formatter="formatDate"
			@change="onDateRangeChange($event)"
		/>
		<DatePicker
			v-if="selectorType === 'datepicker'"
			:value="filterValue?.value"
			:formatter="formatDate"
			@change="onDateChange($event)"
		/>
		<FormControl
			v-if="selectorType === 'text'"
			type="text"
			autocomplete="off"
			placeholder="Value"
			:modelValue="filterValue?.value"
			@update:modelValue="
				filterValue = {
					value: $event,
					label: $event,
				}
			"
		/>
	</div>
</template>
