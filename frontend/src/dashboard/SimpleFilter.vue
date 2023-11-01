<script setup>
import { formatDate, isEmptyObj } from '@/utils'
import { getOperatorOptions } from '@/utils/query/columns'
import { call, debounce } from 'frappe-ui'
import { computed, reactive, ref, watch } from 'vue'

import DatePickerFlat from '@/components/Controls/DatePickerFlat.vue'
import DateRangePickerFlat from '@/components/Controls/DateRangePickerFlat.vue'
import TimespanPickerFlat from '@/components/Controls/TimespanPickerFlat.vue'
import { Combobox, ComboboxInput, ComboboxOption, ComboboxOptions } from '@headlessui/vue'

const emit = defineEmits(['apply', 'reset'])
const props = defineProps({
	label: String,
	column: Object,
	operator: Object,
	value: Object,
	disableColumns: Boolean,
})

const columns = ref([])
const operators = computed(() => getOperatorOptions(props.column?.type))

const filter = reactive({
	type: 'simple',
	label: props.label,
	column: props.column,
	operator: props.operator,
	value: props.value,
})

watch(
	() => props,
	() => {
		filter.label = props.label
		filter.column = props.column
		filter.operator = props.operator
		filter.value = props.value
	},
	{ immediate: true, deep: true }
)

watch(
	() => filter.operator,
	(operator) => {
		if (operator && ['in', 'not_in'].includes(operator.value) && !filter.value) {
			filter.value = []
		}
	},
	{ immediate: true }
)

const isOpen = ref(false)
const applyDisabled = computed(() => {
	return isEmptyObj(filter.column) || isEmptyObj(filter.operator) || isEmptyObj(filter.value)
})
function applyFilter() {
	if (!isOpen.value) return
	if (applyDisabled.value) return
	emit('apply', filter)
}

const selecting = computed(() => {
	if (!filter.column) return 'column'
	if (!filter.operator) return 'operator'
	return 'value'
})

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

const showValuePicker = computed(
	() =>
		['=', '!=', 'is', 'in', 'not_in'].includes(filter.operator?.value) &&
		filter.column?.type == 'String'
)

const columnValues = ref([])
const checkAndFetchColumnValues = debounce(async function (search_text = '') {
	if (
		isEmptyObj(filter.column) ||
		!['=', '!=', 'in', 'not_in'].includes(filter.operator?.value)
	) {
		return
	}

	if (filter.column?.type == 'String') {
		// prettier-ignore
		columnValues.value = await call('insights.api.data_sources.fetch_column_values', {
			data_source: filter.column.data_source,
			table: filter.column.table,
			column: filter.column.column,
			search_text,
		})
	}
}, 300)

const values = computed(() => {
	if (filter.operator?.value == 'is') {
		return [
			{ label: 'Set', value: 'set' },
			{ label: 'Not Set', value: 'not set' },
		]
	}
	return columnValues.value.map((value) => ({ label: value, value }))
})

watch(
	() => showValuePicker.value,
	(show) => show && checkAndFetchColumnValues(),
	{ immediate: true }
)

const operatorLabel = computed(() => {
	if (['between', 'timespan'].includes(filter.operator?.value)) {
		return ':'
	}
	if (['in', 'not_in'].includes(filter.operator?.value)) {
		return filter.operator?.label
	}
	return filter.operator?.value
})

function resetFilter() {
	filter.column = props.disableColumns ? filter.column : null
	filter.operator = null
	filter.value = null
	emit('reset')
}

const valueLabel = computed(() => filter.value?.label)
const isMultiple = computed(() => ['in', 'not_in'].includes(filter.operator?.value))
if (isMultiple.value && Array.isArray(filter.value)) {
	// for backward compatibility
	const values = filter.value[0]?.value ? filter.value.map((v) => v.value) : filter.value
	filter.value = {
		label: `${filter.value?.length} values`,
		value: values,
	}
}
const comboboxModelValue = computed(() => {
	if (isMultiple.value) {
		return (
			filter.value?.value?.map((value) => {
				return { label: value, value }
			}) || []
		)
	}
	return filter.value
})
function onComboboxValueChange(value) {
	!isMultiple.value && togglePopover(false)
	if (isMultiple.value) {
		const values = value
			?.map((v) => v.value)
			.reduce((acc, value) => {
				// remove the ones which appear more than once
				// since clicking on same value adds it twice
				if (acc.includes(value)) {
					return acc.filter((v) => v !== value)
				}
				return [...acc, value]
			}, [])
		filter.value = {
			label: values?.length > 1 ? `${values.length} values` : values?.[0],
			value: values,
		}
	}
}
function isValueSelected(value) {
	if (isMultiple.value) {
		return filter.value?.value?.includes(value)
	}
	return filter.value?.value === value
}
</script>

<template>
	<div class="w-full [&:first-child]:w-full">
		<Popover class="w-full" @close="applyFilter" @update:show="isOpen = $event">
			<template #target="{ togglePopover, isOpen }">
				<div class="flex w-full">
					<button
						class="flex w-full items-center rounded border border-gray-100 bg-white px-3 py-1 text-base leading-5 text-gray-900 shadow"
						@click="togglePopover"
					>
						<span v-if="!filter.column" class="text-gray-600">Select a filter...</span>
						<span
							v-else
							class="overflow-hidden text-ellipsis whitespace-nowrap"
							:class="{ 'text-gray-600': !filter.operator }"
						>
							{{ filter.label || filter.column.label }}
						</span>
						<span v-if="filter.operator" class="ml-1">{{ operatorLabel }}</span>
						<span
							v-if="filter.value"
							class="ml-1 flex-shrink-0 overflow-hidden text-ellipsis whitespace-nowrap"
						>
							{{ valueLabel }}
						</span>
						<div class="ml-auto flex items-center pl-2">
							<div
								v-if="isOpen || !applyDisabled"
								class="-my-1 -mr-2 rounded p-1 hover:bg-blue-50 hover:text-blue-600"
								@click.prevent.stop="resetFilter()"
							>
								<FeatherIcon name="x" class="h-3.5 w-3.5" />
							</div>
							<FeatherIcon
								v-else
								name="chevron-down"
								class="h-3.5 w-3.5"
								@click.prevent.stop="togglePopover(true)"
							/>
						</div>
					</button>
				</div>
			</template>
			<template #body="{ togglePopover }">
				<!-- Column Selector -->
				<div
					v-if="selecting === 'column'"
					class="mt-2 flex w-fit flex-col rounded bg-white p-2 text-base shadow"
				>
					<div class="mb-1 px-1 text-sm text-gray-500">Select a column</div>
					<div
						class="cursor-pointer rounded px-2 py-1.5 hover:bg-gray-100"
						v-for="column in columns"
						:key="column.value"
						@click.prevent.stop="filter.column = column"
					>
						{{ column.label }}
					</div>
				</div>
				<!-- Operator Selector -->
				<div
					v-if="selecting === 'operator'"
					class="mt-2 flex w-fit flex-col rounded bg-white p-2 text-base shadow"
				>
					<div class="mb-1 px-1 text-sm text-gray-500">Select an operator</div>
					<div
						class="cursor-pointer rounded px-2 py-1.5 hover:bg-gray-100"
						v-for="operator in operators"
						:key="operator.value"
						@click.prevent.stop="filter.operator = operator"
					>
						{{ operator.label }}
					</div>
				</div>
				<!-- Value Selector -->
				<div
					v-if="selecting === 'value'"
					class="mt-2 flex w-fit flex-col rounded bg-white p-2 text-base shadow"
				>
					<Combobox
						v-if="showValuePicker"
						as="div"
						nullable
						:multiple="isMultiple"
						:modelValue="comboboxModelValue"
						@update:model-value="onComboboxValueChange"
					>
						<ComboboxInput
							v-if="filter.operator?.value != 'is'"
							autocomplete="off"
							placeholder="Filter..."
							@input="checkAndFetchColumnValues($event.target.value)"
							class="form-input mb-2 block h-7 w-full border-gray-400 placeholder-gray-500"
						/>
						<ComboboxOptions static class="flex max-h-[20rem] flex-col overflow-hidden">
							<div class="mb-1 px-1 text-sm text-gray-500">Select an option</div>
							<div class="flex-1 overflow-y-scroll">
								<ComboboxOption
									v-for="value in values"
									:key="value.value"
									:value="value"
									v-slot="{ active }"
								>
									<div
										class="flex cursor-pointer items-center rounded px-2 py-1.5 hover:bg-gray-100"
										:class="{ 'bg-gray-100': active }"
									>
										<span>{{ value.label }}</span>
										<FeatherIcon
											v-if="isValueSelected(value.value)"
											name="check"
											class="ml-auto h-3.5 w-3.5"
										/>
									</div>
								</ComboboxOption>
							</div>
						</ComboboxOptions>
					</Combobox>

					<TimespanPickerFlat
						v-else-if="showTimespanPicker"
						v-model="filter.value"
						@change="togglePopover(false)"
					/>

					<DateRangePickerFlat
						v-else-if="showDatePicker && filter.operator?.value == 'between'"
						:value="filter.value?.value"
						@change="
							(dates) => {
								filter.value = {
									value: dates,
									label: dates
										.split(',')
										.map((date) => formatDate(date))
										.join(' to '),
								}
								togglePopover(false)
							}
						"
					/>

					<DatePickerFlat
						v-else-if="showDatePicker"
						:value="filter.value?.value"
						@change="
							(date) => {
								filter.value = {
									value: date,
									label: formatDate(date),
								}
								togglePopover(false)
							}
						"
					/>

					<input
						v-else
						type="text"
						placeholder="Enter a value"
						:value="filter.value?.value"
						@input="
							(event) => {
								filter.value = {
									value: event.target.value,
									label: event.target.value,
								}
							}
						"
						class="form-input block h-7 w-full select-none rounded border-gray-400 placeholder-gray-500"
					/>
				</div>
			</template>
		</Popover>
	</div>
</template>
