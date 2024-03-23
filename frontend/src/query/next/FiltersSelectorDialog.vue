<script setup lang="ts">
import { PlusIcon } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import FilterExpression from './components/FilterExpression.vue'
import FilterRule from './components/FilterRule.vue'
import { column, expression } from './pipeline_utils'

const emit = defineEmits({ select: (filters: FilterArgs[]) => true })
const showDialog = defineModel()

export interface FilterRule {
	column_name: string
	operator: FilterOperator
	value: FilterValue
	isValid?: boolean
}
export interface FilterExpression {
	expression: string
	isValid?: boolean
}
export type Filter = FilterRule | FilterExpression
const filters = ref<Filter[]>([
	{
		column_name: '',
		operator: '=',
		value: undefined,
		isValid: false,
	},
])

function addFilter() {
	filters.value.push({
		column_name: '',
		operator: '=',
		value: undefined,
		isValid: false,
	})
}

const areAllFiltersValid = computed(
	() => filters.value.length && filters.value.every((filter) => filter.isValid)
)
function confirmSelection() {
	emit(
		'select',
		filters.value.map((filter: Filter) => {
			if (filter.hasOwnProperty('expression')) {
				const _filter = filter as FilterExpression
				return {
					expression: expression(_filter.expression),
				}
			} else {
				const _filter = filter as FilterRule
				return {
					column: column(_filter.column_name),
					operator: _filter.operator,
					value: _filter.value,
				}
			}
		})
	)
	showDialog.value = false
}
</script>

<template>
	<Dialog
		v-if="showDialog"
		:modelValue="showDialog"
		@after-leave="filters = []"
		:options="{
			size: '2xl',
			title: 'Filter Rows',
			actions: [],
		}"
	>
		<template #body>
			<div class="bg-white px-4 pb-6 pt-5 sm:px-6">
				<div class="flex items-center justify-between pb-4">
					<h3 class="text-2xl font-semibold leading-6 text-gray-900">Filter Rows</h3>
					<Button variant="ghost" @click="showDialog = false" icon="x" size="md">
					</Button>
				</div>
				<div
					v-if="filters.length"
					v-for="(_, i) in filters"
					:key="i"
					id="filter-list"
					class="mb-3 flex items-start justify-between gap-2"
				>
					<div class="flex flex-1 items-start gap-2">
						<div
							class="flex h-7 w-13 flex-shrink-0 items-center text-base text-gray-600"
						>
							{{ i == 0 ? 'Where' : 'And' }}
						</div>
						<FilterExpression
							v-if="filters[i].hasOwnProperty('expression')"
							:modelValue="(filters[i] as FilterExpression)"
							@update:modelValue="filters[i] = $event"
						/>
						<FilterRule
							v-if="filters[i].hasOwnProperty('column_name')"
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
										filters[i] = { expression: '' }
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
	</Dialog>
</template>
