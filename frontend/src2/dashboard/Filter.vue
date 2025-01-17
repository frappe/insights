<script setup lang="ts">
import { computed } from 'vue'
import { FilterType } from '../helpers/constants'
import DatePickerControl from '../query/components/DatePickerControl.vue'
import RelativeDatePicker from '../query/components/RelativeDatePicker.vue'
import { FilterOperator, FilterValue } from '../types/query.types'
import { getOperatorOptions, getValueSelectorType } from '../query/components/filter_utils'

const props = defineProps<{ filterType: FilterType }>()
const filterOperator = defineModel<FilterOperator>('operator')
const filterValue = defineModel<FilterValue>('value')

const valueSelectorType = computed(() => {
	if (!filterOperator.value) return
	return getValueSelectorType(filterOperator.value, props.filterType)
})

const operatorOptions = computed(() => {
	return getOperatorOptions(props.filterType)
})

function onOperatorChange(operator: FilterOperator) {
	filterOperator.value = operator
	filterValue.value = undefined
}
</script>

<template>
	<div class="flex flex-col gap-2">
		<div id="operator" class="!min-w-[100px] flex-1">
			<FormControl
				type="select"
				placeholder="Operator"
				:modelValue="filterOperator"
				:options="operatorOptions"
				@update:modelValue="onOperatorChange($event)"
			/>
		</div>
		<div id="value" class="!min-w-[140px] flex-1 flex-shrink-0">
			<FormControl
				v-if="valueSelectorType === 'text'"
				v-model="filterValue"
				placeholder="Value"
				autocomplete="off"
			/>
			<FormControl
				v-else-if="valueSelectorType === 'number'"
				type="number"
				:modelValue="filterValue"
				placeholder="Value"
				@update:modelValue="filterValue = Number($event)"
			/>
			<DatePickerControl
				v-else-if="valueSelectorType === 'date'"
				placeholder="Select Date"
				:modelValue="[filterValue as string]"
				@update:modelValue="filterValue = $event[0]"
			/>
			<DatePickerControl
				v-else-if="valueSelectorType === 'date_range'"
				:range="true"
				v-model="(filterValue as string[])"
				placeholder="Select Date"
			/>
			<RelativeDatePicker
				v-else-if="valueSelectorType === 'relative_date'"
				v-model="(filterValue as string)"
				placeholder="Relative Date"
			/>
			<!-- <Autocomplete
				v-else-if="valueSelectorType === 'select'"
				class="max-w-[200px]"
				placeholder="Value"
				:multiple="true"
				:modelValue="filter.value || []"
				:options="distinctColumnValues"
				:loading="fetchingValues"
				@update:query="fetchColumnValues"
				@update:modelValue="filter.value = $event?.map((v: any) => v.value) || []"
			/> -->
			<FormControl v-else disabled />
		</div>
	</div>
</template>
