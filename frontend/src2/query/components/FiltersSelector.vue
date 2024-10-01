<script setup lang="ts">
import { PlusIcon } from 'lucide-vue-next'
import { computed, reactive } from 'vue'
import { copy, flattenOptions } from '../../helpers'
import { Column, ColumnOption, FilterGroupArgs, GroupedColumnOption } from '../../types/query.types'
import { column, expression } from '../helpers'
import FilterRule from './FilterRule.vue'
import InlineExpression from './InlineExpression.vue'
import { isFilterExpressionValid, isFilterValid } from './filter_utils'

const props = defineProps<{
	filterGroup?: FilterGroupArgs
	columnOptions: ColumnOption[] | GroupedColumnOption[]
}>()

const emit = defineEmits({
	select: (args: FilterGroupArgs) => true,
	close: () => true,
})

const filterGroup = reactive<FilterGroupArgs>(
	props.filterGroup
		? copy(props.filterGroup)
		: {
				logical_operator: 'And',
				filters: [],
		  }
)

function addFilter() {
	filterGroup.filters.push({
		column: column(''),
		operator: '=',
		value: undefined,
	})
}

const areAllFiltersValid = computed(() => {
	if (!filterGroup.filters.length) return true
	return filterGroup.filters.every((filter) => {
		if ('expression' in filter) return isFilterExpressionValid(filter)

		const options = flattenOptions(props.columnOptions) as ColumnOption[]

		const column = options.find((c) => c.value === filter.column.column_name)
		if (!column) return false

		return isFilterValid(filter, column.data_type)
	})
})

const areFiltersUpdated = computed(() => {
	if (!props.filterGroup) return true
	return JSON.stringify(filterGroup) !== JSON.stringify(props.filterGroup)
})
</script>

<template>
	<div class="min-w-[36rem] rounded-lg bg-white px-4 pb-6 pt-5 sm:px-6">
		<div class="flex items-center justify-between pb-4">
			<h3 class="text-2xl font-semibold leading-6 text-gray-900">Filter</h3>
			<Button variant="ghost" @click="emit('close')" icon="x" size="md"> </Button>
		</div>
		<div
			v-if="filterGroup.filters.length"
			v-for="(_, i) in filterGroup.filters"
			:key="i"
			id="filter-list"
			class="mb-3 flex items-start justify-between gap-2"
		>
			<div class="flex flex-1 items-start gap-2">
				<div class="flex h-7 w-13 flex-shrink-0 items-center text-base text-gray-600">
					<span v-if="i == 0">Where</span>
					<Button
						v-else
						@click="
							filterGroup.logical_operator =
								filterGroup.logical_operator === 'And' ? 'Or' : 'And'
						"
					>
						{{ filterGroup.logical_operator }}
					</Button>
				</div>
				<InlineExpression
					v-if="'expression' in filterGroup.filters[i]"
					v-model="filterGroup.filters[i].expression"
				/>
				<FilterRule
					v-if="'column' in filterGroup.filters[i]"
					:modelValue="filterGroup.filters[i]"
					:columnOptions="props.columnOptions"
					@update:modelValue="filterGroup.filters[i] = $event"
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
								filterGroup.filters[i] = { expression: expression('') }
							},
						},
						{
							label: 'Duplicate',
							onClick: () => {
								filterGroup.filters.splice(
									i + 1,
									0,
									JSON.parse(JSON.stringify(filterGroup.filters[i]))
								)
							},
						},
						{
							label: 'Remove',
							onClick: () => filterGroup.filters.splice(i, 1),
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
				<Button label="Clear" variant="outline" @click="filterGroup.filters = []" />
				<Button
					label="Apply Filters"
					variant="solid"
					:disabled="!areAllFiltersValid || !areFiltersUpdated"
					@click="emit('select', filterGroup)"
				/>
			</div>
		</div>
	</div>
</template>
