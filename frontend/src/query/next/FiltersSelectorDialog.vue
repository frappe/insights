<script setup lang="ts">
import { PlusIcon } from 'lucide-vue-next'
import { computed, inject, ref } from 'vue'
import FilterCondition from './components/FilterCondition.vue'
import { column } from './pipeline_utils'
import { QueryPipeline } from './useQueryPipeline'

const emit = defineEmits({ select: (filters: FilterArgs[]) => true })
const showDialog = defineModel()

const queryPipeline = inject('queryPipeline') as QueryPipeline

export interface FilterCondition {
	column_name: string
	operator: FilterOperator
	value: FilterValue
	isValid?: boolean
}
const filters = ref<FilterCondition[]>([
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
		filters.value.map((filter) => {
			return {
				column: column(filter.column_name),
				operator: filter.operator,
				value: filter.value,
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
		<template #body-content>
			<div class="flex max-h-[20rem] min-w-[400px] flex-col overflow-auto p-0.5">
				<div
					v-if="filters.length"
					v-for="(_, i) in filters"
					:key="i"
					id="filter-list"
					class="mb-3 flex items-center justify-between gap-2"
				>
					<div class="flex flex-1 items-center gap-2">
						<div class="w-13 flex-shrink-0 text-base text-gray-600">
							{{ i == 0 ? 'Where' : 'And' }}
						</div>
						<FilterCondition
							:modelValue="filters[i]"
							@update:modelValue="filters[i] = $event"
						/>
					</div>
					<div class="flex-shrink-0">
						<Button variant="ghost" icon="x" @click="filters.splice(i, 1)" />
					</div>
				</div>
				<div v-else class="mb-3 flex h-7 items-center px-0 text-sm text-gray-600">
					Empty - Choose a field to filter by
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
