<script setup>
import DatePickerFlat from '@/components/Controls/DatePickerFlat.vue'
import DateRangePickerFlat from '@/components/Controls/DateRangePickerFlat.vue'
import TimespanPickerFlat from '@/components/Controls/TimespanPickerFlat.vue'
import { fieldtypesToIcon, formatDate, isEmptyObj } from '@/utils'
import { getOperatorOptions } from '@/utils/'
import { Combobox, ComboboxInput, ComboboxOption, ComboboxOptions } from '@headlessui/vue'
import { call, debounce } from 'frappe-ui'
import { computed, inject, reactive, ref, watch } from 'vue'

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

const dashboard = inject('dashboard')
const item_id = inject('item_id')
const columnValues = ref([])
const checkAndFetchColumnValues = debounce(async function (search_text = '') {
	if (
		isEmptyObj(filter.column) ||
		!['=', '!=', 'in', 'not_in'].includes(filter.operator?.value)
	) {
		return
	}

	if (filter.column?.type == 'String') {
		let method = 'insights.api.data_sources.fetch_column_values'
		let params = {
			data_source: filter.column.data_source,
			table: filter.column.table,
			column: filter.column.column,
			search_text,
		}
		if (dashboard.isPublic) {
			method = 'insights.api.public.fetch_column_values_public'
			params = {
				public_key: dashboard.doc.public_key,
				item_id: item_id,
			}
		}
		columnValues.value = await call(method, params)
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
	// if (['between', 'timespan'].includes(filter.operator?.value)) {
	// 	return ':'
	// }
	// if (['in', 'not_in'].includes(filter.operator?.value)) {
	// 	return filter.operator?.label
	// }
	return filter.operator?.label
})

function resetFilter() {
	filter.column = props.disableColumns ? filter.column : null
	filter.operator = null
	filter.value = null
	emit('reset')
}

const valueLabel = computed(() => filter.value?.label || filter.value?.value)
const isMultiple = computed(() => ['in', 'not_in'].includes(filter.operator?.value))
if (isMultiple.value && Array.isArray(filter.value)) {
	// for backward compatibility
	const values = filter.value[0]?.value ? filter.value.map((v) => v.value) : filter.value
	filter.value = {
		label: `${filter.value?.length} values`,
		value: values,
	}
}
const comboboxModelValue = computed({
	get: () => {
		return !isMultiple.value
			? filter.value
			: filter.value?.value?.map((value) => {
					return { label: value, value }
			  })
	},
	set: (value) => {
		if (!isMultiple.value) {
			filter.value = value
			return
		}

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
		const multipleValueLabel = values?.length > 1 ? `${values.length} values` : values?.[0]
		filter.value = { label: multipleValueLabel, value: values }
	},
})
function onComboboxValueChange(value, togglePopover) {}
function isValueSelected(value) {
	if (isMultiple.value) {
		return filter.value?.value?.includes(value)
	}
	return filter.value?.value === value
}
</script>

<template>
	<div class="w-full [&:first-child]:w-full">
		<Popover class="w-full" @close="applyFilter">
			<template #target="{ togglePopover, isOpen }">
				<div class="flex h-8 w-full rounded bg-white shadow">
					<button
						class="flex flex-1 flex-shrink-0 items-center gap-1.5 overflow-hidden rounded bg-white p-1 pl-3 text-base font-medium leading-5 text-gray-900"
						@click="togglePopover"
					>
						<span v-if="!filter.column" class="font-normal text-gray-600">
							Select a filter...
						</span>
						<div class="flex flex-shrink-0 items-center gap-1">
							<component
								:is="fieldtypesToIcon[filter.column?.type || 'String']"
								class="h-4 w-4 flex-shrink-0 text-gray-600"
							/>
							<span class="truncate">{{ props.label || filter.column?.label }}</span>
						</div>
						<span v-if="filter.operator" class="flex-shrink-0 text-green-700">
							{{ operatorLabel }}
						</span>
						<span v-if="filter.value" class="flex-shrink-0 truncate">
							{{ valueLabel }}
						</span>
					</button>
					<div class="flex h-8 items-center rounded">
						<Button
							v-if="isOpen || !applyDisabled"
							icon="x"
							variant="ghost"
							@click.prevent.stop="resetFilter()"
						/>
						<FeatherIcon v-else name="chevron-down" class="mr-2 h-4 w-4" />
					</div>
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
						v-model="comboboxModelValue"
						@update:model-value="!isMultiple && togglePopover(false)"
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
							<div class="flex-1 overflow-y-auto">
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
					<div v-else class="flex items-center gap-2">
						<Input
							:model-value="filter.value?.value"
							@update:model-value="filter.value = { value: $event, label: $event }"
							placeholder="Enter a value"
						/>
						<Button variant="solid" icon="check" @click="togglePopover(false)" />
					</div>
				</div>
			</template>
		</Popover>
	</div>
</template>
