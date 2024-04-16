<script setup>
import { FIELDTYPES, getOperatorOptions } from '@/utils'
import { computed, defineProps, inject, reactive, ref, watch } from 'vue'
import ExpressionBuilder from './ExpressionBuilder.vue'
import FilterValueSelector from './FilterValueSelector.vue'
import { NEW_FILTER } from './constants'
import { getSelectedTables } from './useAssistedQuery'

const emit = defineEmits(['save', 'discard', 'remove'])
const props = defineProps({ filter: Object })

const assistedQuery = inject('assistedQuery')
const query = inject('query')

const activeTab = ref('Simple')
const filter = reactive({
	...NEW_FILTER,
	...props.filter,
})
if (filter.expression?.raw) {
	activeTab.value = 'Expression'
}
if (filter.column && filter.column.column && filter.column.table && !filter.column.value) {
	filter.column.value = `${filter.column.table}.${filter.column.column}`
}
if (filter.operator?.value == 'is' && filter.value?.value?.toLowerCase().includes('set')) {
	filter.operator.value = filter.value.value === 'Set' ? 'is_set' : 'is_not_set'
}

const filterColumnOptions = computed(() =>
	assistedQuery.groupedColumnOptions.map((group) => {
		return {
			group: group.group,
			items: group.items.filter((c) => c.column !== 'count'),
		}
	})
)

const isValidFilter = computed(() => {
	if (filter.expression?.raw && filter.expression?.ast) return true
	if (filter.column?.value && filter.operator?.value && filter.value?.value) return true
	if (filter.operator?.value?.includes('is_') && filter.column?.column) return true
	return false
})

const operatorOptions = computed(() => {
	const options = getOperatorOptions(filter.column?.type)
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

function isValidExpression(c) {
	if (!c) return false
	return c.expression?.raw && c.expression?.ast
}

const expressionColumnOptions = computed(() => {
	const selectedTables = getSelectedTables(assistedQuery)
	return assistedQuery.columnOptions.filter((c) => selectedTables.includes(c.table)) || []
})
</script>

<template>
	<div class="flex flex-col gap-4 p-4">
		<div
			class="flex h-8 w-full cursor-pointer select-none items-center rounded bg-gray-100 p-1"
		>
			<div
				v-for="(tab, idx) in ['Simple', 'Expression']"
				class="flex h-full flex-1 items-center justify-center px-4 text-sm transition-all"
				:class="activeTab === tab ? 'rounded bg-white shadow' : ''"
				@click.prevent.stop="activeTab = tab"
			>
				{{ tab }}
			</div>
		</div>
		<template v-if="activeTab == 'Expression'">
			<ExpressionBuilder
				v-model="filter.expression"
				:columnOptions="expressionColumnOptions"
			/>
		</template>
		<template v-if="activeTab == 'Simple'">
			<div class="space-y-1">
				<span class="text-sm font-medium text-gray-700">Column</span>
				<Autocomplete
					v-if="!isValidExpression(filter.column)"
					:modelValue="filter.column"
					placeholder="Column"
					:options="filterColumnOptions"
					@update:modelValue="filter.column = $event || {}"
					@update:query="assistedQuery.fetchColumnOptions"
				/>
				<FormControl
					v-else
					type="textarea"
					class="w-full"
					:modelValue="filter.column?.expression.raw"
					disabled
				/>
				<span v-if="isValidExpression(filter.column)" class="text-xs text-orange-500">
					Editing a filter with a <i>column expression</i> is not supported yet. Remove
					this filter and add an expression filter instead.
				</span>
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
			<div>
				<FilterValueSelector
					:column="filter.column"
					:operator="filter.operator"
					:modelValue="filter.value"
					:data-source="assistedQuery.data_source"
					@update:modelValue="filter.value = $event"
				/>
			</div>
		</template>
		<div class="flex justify-between">
			<Button variant="outline" @click="emit(isValidFilter ? 'discard' : 'remove')">
				Discard
			</Button>
			<div class="flex gap-2">
				<Button variant="outline" theme="red" @click="emit('remove')">Remove</Button>
				<Button variant="solid" :disabled="!isValidFilter" @click="emit('save', filter)">
					Save
				</Button>
			</div>
		</div>
	</div>
</template>
