<script setup lang="ts">
import { computed, watchEffect } from 'vue'
import { copy } from '../../helpers'
import { FilterOperator } from '../../types/query.types'
import { isValidNumber } from './filter_utils'

const filterOperator = defineModel<FilterOperator>('operator')
const filterValue = defineModel<number | number[]>('value')

// this component has min & max fields only,
// using just min & max values, we figure out the operator & value
// 1. min & max values are present => operator = 'between', value = [min, max]
// 2. only min value is present => operator = '>=', value = min
// 3. only max value is present => operator = '<=', value = max
// 4. min & max values are present and equal => operator = '=', value = min

const state = computed({
	get() {
		const value = copy(filterValue.value)
		if (Array.isArray(value)) {
			return { min: value[0], max: value[1] }
		} else if (isValidNumber(value)) {
			if (filterOperator.value === '=') {
				return { min: value, max: value }
			} else if (filterOperator.value === '>=') {
				return { min: value, max: undefined }
			} else if (filterOperator.value === '<=') {
				return { min: undefined, max: value }
			}
		}
		return { min: undefined, max: undefined }
	},
	set({ min: newMin, max: newMax }) {
		const validMin = isValidNumber(newMin)
		const validMax = isValidNumber(newMax)
		const _min = validMin ? Number(newMin) : undefined
		const _max = validMax ? Number(newMax) : undefined

		if (validMin && validMax && _min === _max) {
			filterValue.value = _min
			filterOperator.value = '='
		} else if (validMin && !validMax) {
			filterValue.value = _min
			filterOperator.value = '>='
		} else if (!validMin && validMax) {
			filterValue.value = _max
			filterOperator.value = '<='
		} else if (validMin && validMax) {
			filterValue.value = [_min, _max] as number[]
			filterOperator.value = 'between'
		} else {
			filterValue.value = undefined
			filterOperator.value = undefined
		}
	},
})
</script>

<template>
	<div class="flex gap-2">
		<FormControl
			type="number"
			autocomplete="off"
			placeholder="Min"
			label="Min"
			:modelValue="state.min"
			@update:modelValue="state = { ...state, min: $event }"
		/>
		<FormControl
			type="number"
			autocomplete="off"
			placeholder="Max"
			label="Max"
			:modelValue="state.max"
			@update:modelValue="state = { ...state, max: $event }"
		/>
	</div>
</template>
