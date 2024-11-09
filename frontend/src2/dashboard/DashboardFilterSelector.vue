<script setup lang="ts">
import { ListFilter } from 'lucide-vue-next'
import { computed, inject, reactive, ref } from 'vue'
import { copy } from '../helpers'
import FiltersSelectorDialog from '../query/components/FiltersSelectorDialog.vue'
import { getCachedQuery } from '../query/query'
import { FilterArgs, FilterGroupArgs, GroupedColumnOption } from '../types/query.types'
import { WorkbookChart, WorkbookQuery } from '../types/workbook.types'
import { workbookKey } from '../workbook/workbook'
import { Dashboard } from './dashboard'

const props = defineProps<{
	dashboard: Dashboard
	charts: WorkbookChart[]
	queries: WorkbookQuery[]
}>()

const showDialog = ref(false)

const workbook = inject(workbookKey)!

const chartQueries = computed(() => {
	if (!workbook)
		return props.charts
			.map((c) => c.query)
			.map((q) => props.queries.find((query) => query.name === q)!)

	return props.charts
		.map((c) => [c.query, ...workbook.getLinkedQueries(c.query)])
		.flat()
		.filter((q, i, arr) => arr.indexOf(q) === i)
		.map((q) => props.queries.find((query) => query.name === q)!)
})

if (chartQueries.value.length) {
	// execute query to load result columns
	chartQueries.value.forEach((q) => {
		const query = getCachedQuery(q.name)
		if (query && !query.result.executedSQL) {
			query.execute()
		}
	})
}

const sep = '`'
const columnOptions = computed(() => {
	return chartQueries.value
		.map((q) => {
			const query = getCachedQuery(q.name)
			if (!query) return {}
			const columns = query.result.columns.map((c) => ({
				query: q.name,
				label: c.name,
				data_type: c.type,
				description: c.type,
				value: `${sep}${q.name}${sep}.${sep}${c.name}${sep}`,
			}))
			return {
				group: query.doc.title || q.name,
				items: columns,
			}
		})
		.filter((group) => group.items?.length) as GroupedColumnOption[]
})

const filterGroup = reactive<FilterGroupArgs>({
	logical_operator: 'And',
	filters: [],
})
setInitialFilters()

function setInitialFilters() {
	const dashboardFilters = copy(props.dashboard.filters)
	filterGroup.filters = Object.entries(dashboardFilters)
		.map(([queryName, filters]) => {
			return filters.map((filter) => {
				if ('column' in filter) {
					const col_name = filter.column.column_name
					filter.column.column_name = `${sep}${queryName}${sep}.${sep}${col_name}${sep}`
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
				.split(`${sep}.${sep}`)
				.map((s) => s.replace(new RegExp(sep, 'g'), ''))

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
	<Button label="Filter" variant="outline" @click="showDialog = true">
		<template #prefix>
			<ListFilter class="h-4 w-4 text-gray-700" stroke-width="1.5" />
		</template>
		Filter
		<template v-if="filterGroup.filters?.length" #suffix>
			<div
				class="flex h-5 w-5 items-center justify-center rounded bg-gray-900 pt-[1px] text-2xs font-medium text-white"
			>
				{{ filterGroup.filters.length }}
			</div>
		</template>
	</Button>

	<FiltersSelectorDialog
		v-if="showDialog"
		v-model="showDialog"
		:filter-group="filterGroup"
		:column-options="columnOptions"
		:disable-logical-operator="true"
		:disable-expressions="true"
		@select="applyFilters($event)"
	/>
</template>
