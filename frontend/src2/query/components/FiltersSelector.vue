<script setup lang="ts">
import { PlusIcon } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import { copy } from '../../helpers'
import { column, expression } from '../helpers'
import FilterExpression from './FilterExpression.vue'
import FilterRule from './FilterRule.vue'
import { isFilterExpressionValid, isFilterValid } from './filter_utils'

const props = defineProps<{
	filters?: FilterArgs[]
	columnOptions: {
		label: string
		value: string
		query: string
		data_type: ColumnDataType
	}[]
}>()
const emit = defineEmits({
	select: (args: FilterGroupArgs) => true,
	close: () => true,
})
const logicalOperator = ref<LogicalOperator>('And')
const filters = ref<FilterArgs[]>(
	props.filters || [
		{
			column: column(''),
			operator: '=',
			value: undefined,
		},
	]
)

function addFilter() {
	filters.value.push({
		column: column(''),
		operator: '=',
		value: undefined,
	})
}

const areAllFiltersValid = computed(() => {
	if (!filters.value.length) return false
	return filters.value.every((filter) => {
		if ('expression' in filter) return isFilterExpressionValid(filter)

		const column = props.columnOptions.find((c) => c.value === filter.column.column_name)
		if (!column) return false

		return isFilterValid(filter, column.data_type)
	})
})

function confirmSelection() {
	emit('select', {
		logical_operator: logicalOperator.value,
		filters: filters.value,
	})
	close()
}
function close() {
	filters.value = []
	emit('close')
}
</script>

<template>
	<div class="min-w-[36rem] rounded-lg bg-white px-4 pb-6 pt-5 sm:px-6">
		<div class="flex items-center justify-between pb-4">
			<h3 class="text-2xl font-semibold leading-6 text-gray-900">Filter</h3>
			<Button variant="ghost" @click="close" icon="x" size="md"> </Button>
		</div>
		<div
			v-if="filters.length"
			v-for="(_, i) in filters"
			:key="i"
			id="filter-list"
			class="mb-3 flex items-start justify-between gap-2"
		>
			<div class="flex flex-1 items-start gap-2">
				<div class="flex h-7 w-13 flex-shrink-0 items-center text-base text-gray-600">
					<span v-if="i == 0">Where</span>
					<Button
						v-else
						@click="logicalOperator = logicalOperator === 'And' ? 'Or' : 'And'"
					>
						{{ logicalOperator }}
					</Button>
				</div>
				<FilterExpression
					v-if="filters[i].hasOwnProperty('expression')"
					:modelValue="(filters[i] as FilterExpression)"
					@update:modelValue="filters[i] = $event"
				/>
				<FilterRule
					v-if="filters[i].hasOwnProperty('column')"
					:columnOptions="props.columnOptions"
					:modelValue="(filters[i] as FilterRule)"
					@update:modelValue="filters[i] = $event"
				/>
			</div>
			<div class="flex h-full flex-shrink-0 items-start">
				<Dropdown
					placement="right"
					:button="{
						icon: 'more-horizontal',
						variant: 'ghost',
					}"
					:options="[
						{
							label: 'Convert to Expression',
							onClick: () => {
								filters[i] = { expression: expression('') }
							},
						},
						{
							label: 'Duplicate',
							onClick: () => {
								filters.splice(i + 1, 0, JSON.parse(JSON.stringify(filters[i])))
							},
						},
						{
							label: 'Remove',
							onClick: () => filters.splice(i, 1),
						},
					]"
				/>
			</div>
		</div>
		<div v-else class="mb-3 flex h-7 items-center px-0 text-sm text-gray-600">
			Empty - Click 'Add Filter' to add a filter
		</div>
		<div class="mt-2 flex items-center justify-between gap-2">
			<Button @click="addFilter" label="Add Filter">
				<template #prefix>
					<PlusIcon class="h-4 w-4 text-gray-700" stroke-width="1.5" />
				</template>
			</Button>
			<div class="flex items-center gap-2">
				<Button
					label="Apply Filters"
					variant="solid"
					:disabled="!areAllFiltersValid"
					@click="confirmSelection"
				/>
			</div>
		</div>
	</div>
</template>
