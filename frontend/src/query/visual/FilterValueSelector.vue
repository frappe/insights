<script setup>
import DatePicker from '@/components/Controls/DatePicker.vue'
import DateRangePicker from '@/components/Controls/DateRangePicker.vue'
import TimespanPicker from '@/components/Controls/TimespanPicker.vue'
import { formatDate } from '@/utils'
import { whenever } from '@vueuse/core'
import { FormControl, call, debounce } from 'frappe-ui'
import { computed, defineProps, inject, ref, watch } from 'vue'

const emit = defineEmits(['update:filter'])
const props = defineProps({
	selectorType: { type: String, required: true },
	filter: { type: Object, required: true },
})

const assistedQuery = inject('assistedQuery')
const filter = computed({
	get: () => props.filter,
	set: (val) => emit('update:filter', val),
})

function onDateRangeChange(dates) {
	filter.value.value = {
		value: dates,
		label: dates
			.split(',')
			.map((date) => formatDate(date))
			.join(' to '),
	}
}

function onDateChange(date) {
	filter.value.value = {
		value: date,
		label: formatDate(date),
	}
}
const isMultiValue = computed(() => ['in', 'not_in'].includes(filter.value.operator?.value))
const columnValues = ref([])
const fetchingColumnValues = ref(false)
const checkAndFetchColumnValues = debounce(async function (search_text = '') {
	const _filter = filter.value
	if (!_filter.column || !_filter.operator) return
	if (!['=', '!=', 'in', 'not_in'].includes(_filter.operator.value)) return
	if (!_filter.column.table || !_filter.column.column || !assistedQuery.data_source) return
	if (_filter.column?.type == 'String' && assistedQuery.data_source) {
		const URL = 'insights.api.data_sources.fetch_column_values'
		fetchingColumnValues.value = true
		const values = await call(URL, {
			data_source: assistedQuery.data_source,
			table: _filter.column.table,
			column: _filter.column.column,
			search_text,
		})
		columnValues.value = values.map((value) => ({ label: value, value }))
		// prepend the selected value to the list
		if (Array.isArray(_filter.value.value)) {
			// _filter.value = {label: '2 selected', value: [{ label: '', value: ''}, ...]}
			_filter.value.value.forEach((selectedOption) => {
				if (!columnValues.value.find((v) => v.value === selectedOption.value)) {
					columnValues.value.unshift(selectedOption)
				}
			})
		}
		fetchingColumnValues.value = false
	}
}, 300)
watch(
	() => filter.value.column,
	() => checkAndFetchColumnValues(),
	{ deep: true }
)
whenever(
	() => props.selectorType == 'combobox',
	() => checkAndFetchColumnValues(),
	{ immediate: true }
)

function onOptionSelect(value) {
	filter.value.value = !isMultiValue.value
		? value
		: {
				label: `${value.length} values`,
				value: value,
		  }
}
</script>

<template>
	<Autocomplete
		v-if="selectorType === 'combobox'"
		placeholder="Value"
		:multiple="isMultiValue"
		:modelValue="filter.value.value"
		:options="columnValues"
		@update:query="checkAndFetchColumnValues"
		@update:modelValue="onOptionSelect"
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
</template>
