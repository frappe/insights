<script setup lang="ts">
import { computed } from 'vue'
import ColumnFilterValueSelector from './ColumnFilterValueSelector.vue'
import { FilterOperator, FilterValue, QueryResultColumn } from '../../types/query.types'

const props = defineProps<{
	column: QueryResultColumn
	valuesProvider: (search: string) => Promise<string[]>
}>()
const filter = defineModel<{ operator: FilterOperator; value: FilterValue }>({
	type: Object,
	default: () => ({ operator: '=', value: [] }),
})

const operatorOptions = [
	{ label: 'is', value: '=' },
	{ label: 'is not', value: '!=' },
	{ label: 'contains', value: 'contains' },
	{ label: 'not contains', value: 'not_contains' },
	{ label: 'is set', value: 'is_set' },
	{ label: 'is not set', value: 'is_not_set' },
]
const isString = computed(() => props.column.type === 'String')
const isEqualityCheck = computed(() => ['=', '!='].includes(filter.value.operator))
const isNullCheck = computed(() => ['is_set', 'is_not_set'].includes(filter.value.operator))
const isLikeCheck = computed(() => ['contains', 'not_contains'].includes(filter.value.operator))

function onOperatorChange() {
	if (isEqualityCheck.value) filter.value.value = []
	if (isNullCheck.value) filter.value.value = undefined
	if (isLikeCheck.value) filter.value.value = ''
}

const placeholder = computed(() => {
	if (isNullCheck.value) return ''
	if (filter.value.operator.includes('contains')) return 'eg. %foo%'
})
</script>

<template>
	<div class="flex flex-col gap-2">
		<FormControl
			type="select"
			:options="operatorOptions"
			v-model="filter.operator"
			@update:modelValue="onOperatorChange"
		/>
		<ColumnFilterValueSelector
			v-if="isString && isEqualityCheck && Array.isArray(filter.value)"
			v-model="filter.value"
			:column="props.column"
			:valuesProvider="props.valuesProvider"
		/>
		<FormControl v-else-if="!isNullCheck" :placeholder="placeholder" v-model="filter.value" />
	</div>
</template>
