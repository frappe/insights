<script setup lang="ts">
import { ListFilter } from 'lucide-vue-next'
import { computed, reactive } from 'vue'
import { copy } from '../helpers'
import FiltersSelector from '../query/components/FiltersSelector.vue'
import { getCachedQuery } from '../query/query'
import { FilterArgs, FilterGroupArgs } from '../types/query.types'
import { WorkbookChart, WorkbookQuery } from '../types/workbook.types'
import { Dashboard } from './dashboard'

const props = defineProps<{
	dashboard: Dashboard
	charts: WorkbookChart[]
	queries: WorkbookQuery[]
}>()

const columnOptions = computed(() => {
	return props.queries
		.map((q) => {
			const query = getCachedQuery(q.name)
			if (!query) return []
			return query.result.columns.map((c) => ({
				query: q.name,
				label: c.name,
				data_type: c.type,
				description: c.type,
				value: `'${q.name}'.'${c.name}'`,
			}))
		})
		.flat()
})

const initialFilters = reactive<FilterGroupArgs>({
	logical_operator: 'And',
	filters: [],
})
setInitialFilters()

function setInitialFilters() {
	const dashboardFilters = copy(props.dashboard.filters)
	initialFilters.filters = Object.entries(dashboardFilters)
		.map(([queryName, filters]) => {
			return filters.map((filter) => {
				if ('column' in filter) {
					filter.column.column_name = `'${queryName}'.'${filter.column.column_name}'`
				}
				return filter
			})
		})
		.flat()
}

function applyFilters(args: FilterGroupArgs) {
	const filtersByQuery = {} as Record<string, FilterArgs[]>
	args.filters.forEach((filter) => {
		if ('column' in filter) {
			const [queryName, columnName] = filter.column.column_name
				.split("'.'")
				.map((s) => s.replace(/'/g, ''))

			filter.column.column_name = columnName
			filtersByQuery[queryName] = filtersByQuery[queryName] || []
			filtersByQuery[queryName].push(filter)
		}
	})
	props.dashboard.filters = filtersByQuery
	props.dashboard.refresh()
	setInitialFilters()
}
</script>

<template>
	<Popover>
		<template #target="{ togglePopover }">
			<Button label="Filter" variant="outline" @click="togglePopover">
				<template #prefix>
					<ListFilter class="h-4 w-4 text-gray-700" stroke-width="1.5" />
				</template>
				Filter
				<template v-if="initialFilters.filters?.length" #suffix>
					<div
						class="flex h-5 w-5 items-center justify-center rounded bg-gray-900 pt-[1px] text-2xs font-medium text-white"
					>
						{{ initialFilters.filters.length }}
					</div>
				</template>
			</Button>
		</template>

		<template #body-main="{ togglePopover, isOpen }">
			<FiltersSelector
				v-if="isOpen"
				:initialFilters="initialFilters"
				:columnOptions="columnOptions"
				@close="
					() => {
						setInitialFilters()
						togglePopover()
					}
				"
				@select="
					(filters) => {
						applyFilters(filters)
						togglePopover()
					}
				"
			/>
		</template>
	</Popover>
</template>
