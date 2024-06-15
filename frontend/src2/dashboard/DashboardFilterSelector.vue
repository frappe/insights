<script setup lang="ts">
import { ListFilter } from 'lucide-vue-next'
import { computed, inject } from 'vue'
import { copy } from '../helpers'
import FiltersSelector from '../query/components/FiltersSelector.vue'
import { getCachedQuery } from '../query/query'
import { WorkbookChart, WorkbookQuery } from '../workbook/workbook'
import { Dashboard } from './dashboard'

const props = defineProps<{
	charts: WorkbookChart[]
	queries: WorkbookQuery[]
}>()

const columnOptions = computed(() => {
	return props.queries
		.map((q) => {
			const query = getCachedQuery(q.name)
			const resultColumns = query?.result.columns || []
			return resultColumns.map((c) => ({
				query: q.name,
				label: c.name,
				data_type: c.type,
				description: c.type,
				value: `'${q.name}'.'${c.name}'`,
			}))
		})
		.flat()
})

const dashboard = inject('dashboard') as Dashboard
const filters = computed(() => {
	const _filters = copy(dashboard.filters)
	return Object.entries(_filters)
		.map(([queryName, filters]) => {
			return filters.map((filter) => {
				if ('column' in filter) {
					filter.column.column_name = `'${queryName}'.'${filter.column.column_name}'`
				}
				return filter
			})
		})
		.flat()
})

function applyFilters(args: FilterGroupArgs, togglePopover: Function) {
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
	dashboard.filters = filtersByQuery
	dashboard.refresh()
	togglePopover()
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
				<template v-if="filters?.length" #suffix>
					<div
						class="flex h-5 w-5 items-center justify-center rounded bg-gray-900 pt-[1px] text-2xs font-medium text-white"
					>
						{{ filters.length }}
					</div>
				</template>
			</Button>
		</template>

		<template #body-main="{ togglePopover, isOpen }">
			<FiltersSelector
				v-if="isOpen"
				:filters="filters"
				:columnOptions="columnOptions"
				@select="applyFilters($event, togglePopover)"
			/>
		</template>
	</Popover>
</template>
