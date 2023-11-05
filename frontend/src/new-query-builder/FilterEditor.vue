<script setup>
import { FIELDTYPES, getOperatorOptions } from '@/utils'
import { computed, defineProps, inject, reactive, watch } from 'vue'
import FilterValueSelector from './FilterValueSelector.vue'
import { NEW_FILTER } from './constants'

const emit = defineEmits(['save', 'discard', 'remove'])
const props = defineProps({ filter: Object })

const builder = inject('builder')
const query = inject('query')

const filter = reactive({
	...NEW_FILTER,
	...props.filter,
})

const filterColumnOptions = computed(() =>
	query.columnOptions.map((group) => {
		return {
			...group,
			items: group.items.filter((c) => c.column !== 'count'),
		}
	})
)

const isValidFilter = computed(() => {
	if (!filter.column.column) return false
	if (!filter.operator.value) return false
	if (filter.operator.value.includes('is_')) return true
	if (!filter.value.value) return false
	return true
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
// prettier-ignore
watch(() => filter.operator.value, (newVal, oldVal) => {
	if (newVal !== oldVal) {
		filter.value = {}
	}
})

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
</script>

<template>
	<div class="flex flex-col gap-4 p-4">
		<!-- <div
			class="flex h-8 w-full cursor-pointer select-none items-center rounded bg-gray-100 p-1"
		>
			<div
				v-for="tab in ['Simple', 'Expression']"
				class="flex h-full flex-1 items-center justify-center px-4 text-sm transition-all"
				:class="{
					'rounded bg-white shadow':
						tab.active || (modelValue && modelValue === tab.value),
					'cursor-not-allowed': tab.disabled,
				}"
				@click="handleClick(tab)"
			>
				{{ tab.label }}
			</div>
		</div> -->
		<div class="space-y-1">
			<span class="text-sm font-medium text-gray-700">Column</span>
			<Autocomplete
				:modelValue="{
					...filter.column,
					value: `${filter.column.table}.${filter.column.column}`,
				}"
				placeholder="Column"
				:options="filterColumnOptions"
				@update:modelValue="filter.column = $event"
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
		<div v-if="selectorType !== 'none'" class="space-y-1">
			<span class="text-sm font-medium text-gray-700"> Value </span>
			<FilterValueSelector
				:filter="filter"
				:selector-type="selectorType"
				@update:filter="filter.value = $event.value"
			/>
		</div>
		<div class="flex justify-between">
			<Button variant="outline" @click="emit(isValidFilter ? 'discard' : 'remove')">
				Discard
			</Button>
			<div class="flex gap-2">
				<Button variant="outline" theme="red" @click="emit('remove')">Remove</Button>
				<Button variant="solid" @click="emit('save', filter)">Save</Button>
			</div>
		</div>
	</div>
</template>
