<script setup lang="ts">
import { FIELDTYPES } from '../../helpers/constants'
import { computed, reactive } from 'vue'
import { FilterOperator, FilterValue, QueryResultColumn } from '../../types/query.types'
import ColumnFilterTypeDate from './ColumnFilterTypeDate.vue'
import ColumnFilterTypeNumber from './ColumnFilterTypeNumber.vue'
import ColumnFilterTypeText from './ColumnFilterTypeText.vue'

const emit = defineEmits({
	filter: (operator: FilterOperator, value: FilterValue) => true,
	close: () => true,
})
const props = defineProps<{
	column: QueryResultColumn
	valuesProvider: (search: string) => Promise<string[]>
	placement?: string
}>()

const isText = computed(() => FIELDTYPES.TEXT.includes(props.column.type))
const isNumber = computed(() => FIELDTYPES.NUMBER.includes(props.column.type))
const isDate = computed(() => FIELDTYPES.DATE.includes(props.column.type))

const initialFilter = {
	operator: '=' as FilterOperator,
	value: [] as FilterValue,
}
const newFilter = reactive({ ...initialFilter })

const isValidFilter = computed(() => {
	if (!newFilter.operator) return false
	if (isText.value && newFilter.operator.includes('set')) return true

	if (!newFilter.value) return false
	if (isText.value && newFilter.operator.includes('contains')) return newFilter.value

	const value = newFilter.value as any[] // number & date value is always an array
	if (isNumber.value) return value[0] || value[1]
	if (isDate.value) return value[0] || value[1]
	if (isText.value && newFilter.operator.includes('=')) return value.length

	return false
})

function processFilter(operator: FilterOperator, value: FilterValue) {
	if (isNumber.value && Array.isArray(value)) {
		// convert to string so that 0 is not considered as falsy
		value = value.map((v) => (!isNaN(v) ? String(v) : v))
		if (operator === '=' && value[0] === value[1]) return ['=', Number(value[0])]
		if (operator === '>=' && value[0] && !value[1]) return ['>=', Number(value[0])]
		if (operator === '<=' && !value[0] && value[1]) return ['<=', Number(value[1])]
		if (operator === 'between' && value[0] && value[1]) {
			return ['between', [Number(value[0]), Number(value[1])]]
		}
	}

	if (isText.value) {
		if (operator.includes('set')) return [operator, value]
		if (operator.includes('contains')) return [operator, value]
		if (operator.includes('=')) {
			return [operator === '!=' ? 'not_in' : 'in', value]
		}
	}

	if (isDate.value && Array.isArray(value)) {
		if (operator === '=' && value[0] === value[1]) return ['=', value[0]]
		if (operator === '>=' && value[0] && !value[1]) return ['>=', value[0]]
		if (operator === '<=' && !value[0] && value[1]) return ['<=', value[1]]
		if (operator === 'within') return ['within', value.join(' ')]
		if (operator === 'between' && value[0] && value[1]) return ['between', [value[0], value[1]]]
	}
}

function confirmFilter() {
	const filter = processFilter(newFilter.operator, newFilter.value)
	if (!filter) {
		console.error(newFilter.operator, newFilter.value)
		throw new Error('Invalid filter')
	}
	emit('filter', filter[0], filter[1])
	Object.assign(newFilter, { ...initialFilter })
	emit('close')
}
</script>

<template>
	<div class="flex flex-col gap-2 px-2.5 py-2">
		<ColumnFilterTypeNumber
			v-if="isNumber"
			class="w-[15rem]"
			:column="props.column"
			:model-value="newFilter"
			@update:model-value="Object.assign(newFilter, $event)"
		/>
		<ColumnFilterTypeText
			v-else-if="isText"
			class="w-[15rem]"
			:column="props.column"
			:model-value="newFilter"
			@update:model-value="Object.assign(newFilter, $event)"
			:valuesProvider="props.valuesProvider"
		/>
		<ColumnFilterTypeDate
			v-else-if="isDate"
			:column="props.column"
			:model-value="newFilter"
			@update:model-value="Object.assign(newFilter, $event)"
		/>

		<div class="flex justify-end gap-1">
			<Button @click="emit('close')" icon="x"></Button>
			<Button
				variant="solid"
				icon="check"
				:disabled="!isValidFilter"
				@click="confirmFilter()"
			>
			</Button>
		</div>
	</div>
</template>
