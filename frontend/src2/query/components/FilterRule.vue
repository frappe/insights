<script setup lang="ts">
import { FIELDTYPES } from '../../helpers/constants'
import { debounce } from 'frappe-ui'
import { computed, onMounted, ref } from 'vue'
import { column } from '../helpers'
import { getCachedQuery } from '../query'
import DatePickerControl from './DatePickerControl.vue'
import { getValueSelectorType } from './filter_utils'
import { ColumnDataType, FilterOperator, FilterRule } from '../../types/query.types'

const filter = defineModel<FilterRule>({ required: true })
const props = defineProps<{
	columnOptions: {
		label: string
		value: string
		query: string
		data_type: ColumnDataType
	}[]
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
	const col = props.columnOptions.find((c) => c.value === filter.value.column.column_name)
	if (!col) throw new Error(`Column not found: ${filter.value.column.column_name}`)
	return col.data_type
})

const operatorOptions = computed(() => {
	const type = columnType.value
	if (!type) return []

	const options = [] as { label: string; value: FilterOperator }[]
	if (FIELDTYPES.TEXT.includes(type)) {
		options.push({ label: 'is', value: 'in' }) // value selector
		options.push({ label: 'is not', value: 'not_in' }) // value selector
		options.push({ label: 'contains', value: 'contains' }) // text
		options.push({ label: 'does not contain', value: 'not_contains' }) // text
		options.push({ label: 'starts with', value: 'starts_with' }) // text
		options.push({ label: 'ends with', value: 'ends_with' }) // text
		options.push({ label: 'is set', value: 'is_set' }) // no value
		options.push({ label: 'is not set', value: 'is_not_set' }) // no value
	}
	if (FIELDTYPES.NUMBER.includes(type)) {
		options.push({ label: 'equals', value: '=' })
		options.push({ label: 'not equals', value: '!=' })
		options.push({ label: 'greater than', value: '>' })
		options.push({ label: 'greater than or equals', value: '>=' })
		options.push({ label: 'less than', value: '<' })
		options.push({ label: 'less than or equals', value: '<=' })
	}
	if (FIELDTYPES.DATE.includes(type)) {
		options.push({ label: 'equals', value: '=' })
		options.push({ label: 'not equals', value: '!=' })
		options.push({ label: 'greater than', value: '>' })
		options.push({ label: 'greater than or equals', value: '>=' })
		options.push({ label: 'less than', value: '<' })
		options.push({ label: 'less than or equals', value: '<=' })
		options.push({ label: 'between', value: 'between' })
	}
	return options
})

function onOperatorChange(operator: FilterOperator) {
	filter.value.operator = operator
	filter.value.value = undefined
}

const valueSelectorType = computed(
	() => columnType.value && getValueSelectorType(filter.value, columnType.value)
)

const distinctColumnValues = ref<any[]>([])
const fetchingValues = ref(false)
const fetchColumnValues = debounce((searchTxt: string) => {
	const option = props.columnOptions.find((c) => c.value === filter.value.column.column_name)
	if (!option?.query) {
		fetchingValues.value = false
		console.warn('Query not found for column:', filter.value.column.column_name)
		return
	}
	// if column_name is 'query'.'column_name' extract column_name
	const pattern = /'([^']+)'\.'([^']+)'/g
	const match = pattern.exec(filter.value.column.column_name)
	const column_name = match ? match[2] : filter.value.column.column_name

	fetchingValues.value = true
	return getCachedQuery(option.query)
		?.getDistinctColumnValues(column_name, searchTxt)
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
			<Autocomplete
				v-else-if="valueSelectorType === 'select'"
				class="max-w-[200px]"
				placeholder="Value"
				:multiple="true"
				:modelValue="filter.value || []"
				:options="distinctColumnValues"
				:loading="fetchingValues"
				@update:query="fetchColumnValues"
				@update:modelValue="filter.value = $event.map((v: any) => v.value)"
			/>
			<FormControl v-else disabled />
		</div>
	</div>
</template>
