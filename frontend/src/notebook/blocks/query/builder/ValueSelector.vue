<script setup lang="jsx">
import DatePickerFlat from '@/components/Controls/DatePickerFlat.vue'
import DateRangePickerFlat from '@/components/Controls/DateRangePickerFlat.vue'
import TimespanPickerFlat from '@/components/Controls/TimespanPickerFlat.vue'
import { FIELDTYPES, formatDate } from '@/utils'
import { whenever } from '@vueuse/core'
import { call, debounce } from 'frappe-ui'
import { computed, ref } from 'vue'
import Combobox from './Combobox.vue'
import InputWithPopover from './InputWithPopover.vue'
import ResizeableInput from './ResizeableInput.vue'

const emit = defineEmits(['update:modelValue'])
const props = defineProps({
	data_source: String,
	column: Object,
	operator: Object,
	modelValue: Object,
})
const modelValue = computed({
	get: () => props.modelValue,
	set: (value) => emit('update:modelValue', value),
})

const operator = computed(() => props.operator?.value)
const isExpression = computed(() => props.column?.expression?.raw)
const isString = computed(() => props.column?.type === 'String')
const isDate = computed(() => FIELDTYPES.DATE.includes(props.column?.type))
const isEqualityCheck = computed(() => ['=', '!=', 'in', 'not_in'].includes(operator.value))
const isNullCheck = computed(() => ['is_set', 'is_not_set'].includes(operator.value))

const selectorType = computed(() => {
	if (isDate.value && operator.value === 'between') return 'datepickerrange'
	if (isDate.value && operator.value === 'timespan') return 'timespanpicker'
	if (isDate.value) return 'datepicker'

	if (isString.value && isNullCheck.value) return 'none'
	if (!isExpression.value && isString.value && isEqualityCheck.value) return 'combobox'
	return 'text'
})

const TimespanPicker = (props) => (
	<TimespanPickerFlat
		class="p-2"
		v-model={props.value}
		onChange={() => props.togglePopover(false)}
		onUpdate:modelValue={(value) => props.setValue(value)}
	/>
)

const isMultiValue = computed(() => ['in', 'not_in'].includes(props.operator?.value))
const columnValues = ref([])
const fetchingColumnValues = ref(false)
const checkAndFetchColumnValues = debounce(async function (search_text = '') {
	if (!isEqualityCheck.value) return
	if (props.column?.type == 'String' && props.data_source) {
		const URL = 'insights.api.fetch_column_values'
		fetchingColumnValues.value = true
		const values = await call(URL, {
			data_source: props.data_source,
			table: props.column.table,
			column: props.column.column,
			search_text,
		})
		columnValues.value = values.map((value) => ({ label: value, value }))
		// prepend the selected value to the list
		if (Array.isArray(modelValue.value.value)) {
			// modelValue.value = {label: '2 selected', value: [{ label: '', value: ''}, ...]}
			modelValue.value.value.forEach((selectedOption) => {
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
const ColumnValueCombobox = (props) => (
	<Combobox
		v-model={props.value}
		values={columnValues.value}
		allowMultiple={isMultiValue.value}
		loading={fetchingColumnValues.value}
		onUpdate:modelValue={(value) => {
			props.setValue(value)
			!isMultiValue.value && props.togglePopover(false)
		}}
	/>
)

const DateRangePicker = (props) => (
	<div class="p-2">
		<DateRangePickerFlat
			value={props.value.value}
			onChange={(dates) => {
				props.setValue({
					value: dates,
					label: dates
						.split(',')
						.map((date) => formatDate(date))
						.join(' to '),
				})
				props.togglePopover(false)
			}}
		/>
	</div>
)

const DatePicker = (props) => (
	<DatePickerFlat
		class="rounded p-2"
		value={props.value.value}
		onChange={(date) => {
			props.setValue({
				value: date,
				label: formatDate(date),
			})
			props.togglePopover(false)
		}}
	/>
)

const selectorComponentMap = {
	combobox: ColumnValueCombobox,
	datepicker: DatePicker,
	datepickerrange: DateRangePicker,
	timespanpicker: TimespanPicker,
}
</script>

<template>
	<ResizeableInput
		v-if="selectorType === 'text'"
		v-model="modelValue.value"
		placeholder="Type a value"
		@update:modelValue="modelValue = { value: $event, label: $event }"
	></ResizeableInput>

	<InputWithPopover
		v-else
		v-model="modelValue"
		:disableInput="isMultiValue"
		placeholder="Value"
		@input="selectorType === 'combobox' && checkAndFetchColumnValues($event)"
	>
		<template #popover="{ value, togglePopover, setValue }">
			<component
				:is="selectorComponentMap[selectorType]"
				:value="value"
				:togglePopover="togglePopover"
				:setValue="setValue"
			/>
		</template>
	</InputWithPopover>
</template>
