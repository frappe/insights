<template>
	<div class="flex flex-col space-y-3">
		<div class="space-y-1 text-sm text-gray-600">
			<div class="font-light">Column</div>
			<Autocomplete
				v-model="filter.column"
				:options="columnOptions"
				placeholder="Select a column..."
			/>
		</div>
		<div class="space-y-1 text-sm text-gray-600">
			<div class="font-light">Operator</div>
			<Autocomplete
				v-model="filter.operator"
				:options="operatorList"
				placeholder="Select operator..."
			/>
		</div>
		<div class="space-y-1 text-sm text-gray-600">
			<div class="font-light">Value</div>
			<Autocomplete
				v-if="showValueOptions"
				v-model="filter.value"
				:options="valueList"
				:placeholder="valuePlaceholder"
				@inputChange="checkAndFetchColumnValues"
			/>
			<TimespanPicker
				v-else-if="showTimespanPicker"
				id="value"
				v-model="filter.value"
				:placeholder="valuePlaceholder"
			/>
			<ListPicker
				v-else-if="showListPicker"
				:options="valueList"
				:placeholder="valuePlaceholder"
				@inputChange="checkAndFetchColumnValues"
				@selectOption="
					(options) => {
						filter.value = {
							value: options.map((option) => option.label),
							label:
								options.length > 1 ? `${options.length} values` : options[0].label,
						}
					}
				"
			/>
			<DatePicker
				v-else-if="showDatePicker"
				id="value"
				:value="filter.value.value"
				:placeholder="valuePlaceholder"
				:formatValue="formatDate"
				@change="
					(date) => {
						filter.value = {
							value: date,
							label: formatDate(date),
						}
					}
				"
			/>
			<input
				v-else
				type="text"
				v-model="filter.value.value"
				:placeholder="valuePlaceholder"
				class="form-input block h-8 w-full select-none rounded-md placeholder-gray-500 placeholder:text-sm"
			/>
		</div>
		<div class="flex justify-end">
			<Button @click="apply" appearance="primary" :disabled="applyDisabled"> Apply </Button>
		</div>
	</div>
</template>

<script setup>
import Autocomplete from '@/components/Autocomplete.vue'
import TimespanPicker from '@/components/TimespanPicker.vue'
import ListPicker from '@/components/ListPicker.vue'
import DatePicker from '@/components/DatePicker.vue'

import { debounce } from 'frappe-ui'
import { isEmptyObj } from '@/utils/utils.js'
import { computed, inject, nextTick, onMounted, reactive, watch } from 'vue'

const query = inject('query')

const props = defineProps({
	filter: {
		type: Object,
		default: {
			left: {},
			operator: {},
			right: {},
		},
	},
})
const emit = defineEmits(['filter-select'])

const filter = reactive({
	column: props.filter.left,
	operator: props.filter.operator,
	value: props.filter.right,
})

onMounted(() => {
	query.fetchColumns()
	if (!isEmptyObj(filter.column)) {
		query.fetchOperatorList({
			fieldtype: filter.column?.type,
		})
	}
})

const columnOptions = computed(() => {
	return query.fetchColumnsData.value?.map((c) => {
		return {
			...c,
			value: c.column,
			description: c.table_label,
		}
	})
})
const operatorList = query.fetchOperatorListData

const showDatePicker = computed(() => {
	return (
		['Date', 'Datetime'].includes(filter.column?.type) &&
		['=', '!=', '>', '>=', '<', '<=', 'between'].includes(filter.operator?.value)
	)
})
const showTimespanPicker = computed(
	() =>
		['Date', 'Datetime'].includes(filter.column?.type) && filter.operator?.value === 'timespan'
)

const showListPicker = computed(
	() =>
		['in', 'not in'].includes(filter.operator?.value) &&
		['Varchar', 'Char', 'Enum'].includes(filter.column?.type)
)

const showValueOptions = computed(
	() =>
		['=', '!=', 'is'].includes(filter.operator?.value) &&
		['Varchar', 'Char', 'Enum'].includes(filter.column?.type)
)

const valueList = computed(() => {
	if (filter.operator?.value == 'is') {
		return [
			{ label: 'Set', value: 'set' },
			{ label: 'Not Set', value: 'not set' },
		]
	}
	return query.fetchColumnValuesData.value
})

const valuePlaceholder = computed(() => {
	if (showDatePicker.value) {
		return 'Select a date...'
	}
	if (isEmptyObj(filter.operator)) {
		return 'Type a value...'
	}
	if (filter.operator?.value == 'between') {
		return 'Type two comma separated values...'
	}
	if (filter.operator?.value == 'in' || filter.operator?.value == 'not in') {
		return 'Type comma separated values...'
	}
	return 'Type a value...'
})

const applyDisabled = computed(
	() => isEmptyObj(filter.column) || isEmptyObj(filter.operator) || isEmptyObj(filter.value)
)

watch(
	() => filter.column,
	(newColumn) => {
		filter.column = newColumn
		filter.operator = {}
		filter.value = {}
		query.fetchOperatorList({
			fieldtype: filter.column?.type,
		})
	}
)
watch(
	() => filter.operator,
	(newOperator) => {
		filter.operator = newOperator
		filter.value = {}
	}
)
watch(
	() => filter.value,
	(newValue) => {
		if (newValue.value == filter.value.value) {
			return
		}
		if (
			newValue &&
			!showListPicker.value &&
			!showDatePicker.value &&
			!showValueOptions.value &&
			!showTimespanPicker.value
		) {
			filter.value = {
				label: newValue.value,
				value: newValue.value,
			}
		} else {
			filter.value = newValue
		}
	}
)

function apply() {
	if (isEmptyObj(filter.column) || isEmptyObj(filter.operator) || isEmptyObj(filter.value)) {
		return
	}
	if (!filter.value.label && filter.value.value) {
		filter.value.label = filter.value.value
	}
	emit('filter-select', {
		filter: {
			left: filter.column,
			operator: filter.operator,
			right: filter.value,
		},
	})
}

const checkAndFetchColumnValues = debounce(function (search_text) {
	if (
		!search_text ||
		isEmptyObj(filter.column) ||
		!['=', '!=', 'in', 'not in'].includes(filter.operator?.value)
	) {
		return
	}

	if (['Varchar', 'Char', 'Enum'].includes(filter.column?.type)) {
		query.fetchColumnValues({
			column: filter.column,
			search_text,
		})
	}
}, 300)

function formatDate(value) {
	if (!value) {
		return ''
	}
	return new Date(value).toLocaleString('en-US', {
		month: 'short',
		year: 'numeric',
		day: 'numeric',
	})
}
</script>
