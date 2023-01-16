<script setup>
import { formatDate, isEmptyObj } from '@/utils'
import { getOperatorOptions } from '@/utils/query/columns'
import { debounce } from 'frappe-ui'
import { computed, inject, reactive, ref, watch } from 'vue'

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
const checkAndFetchColumnValues = debounce(function (search_text = '') {
	if (
		isEmptyObj(filter.column) ||
		!['=', '!=', 'in', 'not_in'].includes(filter.operator?.value)
	) {
		return
	}

	if (filter.column?.type == 'String') {
		dashboard.fetch_column_values.submit({
			column: filter.column,
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
	return dashboard.fetch_column_values.data?.message.map((value) => {
		return { label: value, value }
	})
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
	return filter.operator?.value
})

const valueLabel = computed(() =>
	filter.value?.length > 1
		? `${filter.value?.length} values`
		: filter.value[0]?.label || filter.value?.label
)

function resetFilter() {
	filter.column = props.disableColumns ? filter.column : null
	filter.operator = null
	filter.value = null
	emit('reset')
}
</script>

<template>
	<div class="w-full [&:first-child]:w-full">
		<Popover class="w-full">
			<template #target="{ togglePopover, isOpen }">
				<div class="flex">
					<button
						class="flex w-full items-center rounded-md border bg-white px-3 py-1 text-base leading-5 text-gray-900"
						@click="togglePopover"
					>
						<span v-if="!filter.column" class="text-gray-500">
							Select a filter...
						</span>
						<span v-else class="overflow-hidden text-ellipsis whitespace-nowrap">
							{{ filter.label || filter.column.label }}
						</span>
						<span v-if="filter.operator" class="ml-1">
							{{ operatorLabel }}
						</span>
						<span
							v-if="filter.value"
							class="ml-1 flex-shrink-0 overflow-hidden text-ellipsis whitespace-nowrap"
						>
							{{ valueLabel }}
						</span>
						<div class="ml-auto flex items-center pl-2">
							<div
								v-if="isOpen && !applyDisabled"
								class="-my-1 -mr-2 rounded-md p-1 hover:bg-blue-50 hover:text-blue-600"
								@click.prevent.stop="applyFilter() | togglePopover(false)"
							>
								<FeatherIcon name="check" class="h-3.5 w-3.5" />
							</div>
							<div
								v-else-if="!isOpen && !applyDisabled"
								class="-my-1 -mr-2 rounded-md p-1 hover:bg-blue-50 hover:text-blue-600"
								@click.prevent.stop="!isOpen && resetFilter()"
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
			<template #body>
				<!-- Column Selector -->
				<div
					v-if="selecting === 'column'"
					class="mt-2 flex w-fit flex-col rounded-md bg-white p-2 text-base shadow"
				>
					<div class="mb-1 px-1 text-sm text-gray-400">Select a column</div>
					<div
						class="cursor-pointer rounded-md px-2 py-1.5 hover:bg-gray-100"
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
					class="mt-2 flex w-fit flex-col rounded-md bg-white p-2 text-base shadow"
				>
					<div class="mb-1 px-1 text-sm text-gray-400">Select an operator</div>
					<div
						class="cursor-pointer rounded-md px-2 py-1.5 hover:bg-gray-100"
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
					class="mt-2 flex w-fit flex-col rounded-md bg-white p-2 text-base shadow"
				>
					<Combobox
						v-if="showValuePicker"
						v-model="filter.value"
						nullable
						:multiple="['in', 'not in'].includes(filter.operator?.value)"
					>
						<ComboboxInput
							v-if="filter.operator?.value != 'is'"
							autocomplete="off"
							placeholder="Filter..."
							@input="checkAndFetchColumnValues($event.target.value)"
							class="form-input mb-2 block h-7 w-full placeholder-gray-500"
						/>
						<ComboboxOptions static class="flex max-h-[20rem] flex-col overflow-hidden">
							<div class="mb-1 px-1 text-sm text-gray-400">Select an option</div>
							<div class="flex-1 overflow-y-scroll">
								<ComboboxOption
									v-for="value in values"
									:key="value.value"
									:value="value"
									v-slot="{ active, selected }"
								>
									<div
										class="flex cursor-pointer items-center rounded-md px-2 py-1.5 hover:bg-gray-100"
										:class="{ 'bg-gray-100': active }"
									>
										<span>{{ value.label }}</span>
										<FeatherIcon
											v-if="selected"
											name="check"
											class="ml-auto h-3.5 w-3.5"
										/>
									</div>
								</ComboboxOption>
							</div>
						</ComboboxOptions>
					</Combobox>

					<TimespanPickerFlat v-else-if="showTimespanPicker" v-model="filter.value" />

					<DateRangePickerFlat
						v-else-if="showDatePicker && filter.operator?.value == 'between'"
						:value="filter.value?.value"
						@change="
							(dates) =>
								(filter.value = {
									value: dates,
									label: dates
										.split(',')
										.map((date) => formatDate(date))
										.join(' to '),
								})
						"
					/>

					<DatePickerFlat
						v-else-if="showDatePicker"
						:value="filter.value?.value"
						@change="
							(date) =>
								(filter.value = {
									value: date,
									label: formatDate(date),
								})
						"
					/>

					<input
						v-else
						type="text"
						placeholder="Enter a value"
						:value="filter.value?.value"
						@input="
							(event) =>
								(filter.value = {
									value: event.target.value,
									label: event.target.value,
								})
						"
						class="form-input block h-7 w-full select-none rounded-md placeholder-gray-500 placeholder:text-sm"
					/>
				</div>
			</template>
		</Popover>
	</div>
</template>
