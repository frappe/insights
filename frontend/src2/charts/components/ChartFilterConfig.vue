<script setup lang="ts">
import { Plus, X } from 'lucide-vue-next'
import { ref } from 'vue'
import DataTypeIcon from '../../query/components/DataTypeIcon.vue'
import FiltersSelectorDialog from '../../query/components/FiltersSelectorDialog.vue'
import { ColumnOption, FilterArgs, FilterGroupArgs } from '../../types/query.types'

const props = defineProps<{ columnOptions: ColumnOption[] }>()
const filterGroup = defineModel<FilterGroupArgs>({
	default: () => {
		return {
			logical_operator: 'And',
			filters: [],
		}
	},
})

const showFiltersSelectorDialog = ref(false)
function getColumnType(column_name: string) {
	const column = props.columnOptions.find((column) => column.value === column_name)
	if (!column) {
		return 'String'
	}
	return column.data_type
}
function getFilterLabel(filter: FilterArgs) {
	if ('column' in filter) {
		return `${filter.column.column_name} ${filter.operator} ${filter.value}`
	}
	return filter.expression
}
</script>

<template>
	<div class="flex flex-col gap-2">
		<div v-if="filterGroup.filters.length" class="flex flex-col gap-1">
			<div v-for="(filter, idx) in filterGroup.filters" :key="idx" class="flex rounded">
				<div class="flex-1 overflow-hidden">
					<Button
						class="w-full !justify-start rounded-r-none [&>span]:truncate"
						@click="showFiltersSelectorDialog = true"
					>
						<template #prefix>
							<DataTypeIcon
								v-if="'column' in filter"
								:column-type="getColumnType(filter.column.column_name)"
							/>
						</template>
						{{ getFilterLabel(filter) }}
					</Button>
				</div>
				<Button
					class="flex-shrink-0 rounded-l-none border-l"
					@click="filterGroup.filters.splice(idx, 1)"
				>
					<template #icon>
						<X class="h-4 w-4 text-gray-700" stroke-width="1.5" />
					</template>
				</Button>
			</div>
		</div>

		<!-- add filter button -->
		<Button class="w-full" @click="showFiltersSelectorDialog = true">
			<template #prefix>
				<Plus class="h-4 w-4 text-gray-700" stroke-width="1.5" />
			</template>
			Add Filter
		</Button>
	</div>

	<FiltersSelectorDialog
		v-if="showFiltersSelectorDialog"
		v-model="showFiltersSelectorDialog"
		:filter-group="filterGroup"
		:column-options="props.columnOptions"
		@select="filterGroup = $event"
	/>
</template>
