<script setup lang="ts">
import { computed } from 'vue'
import DataTable from '../../components/DataTable.vue'
import {
	AdhocFilters,
	FilterArgs,
	QueryResultColumn,
	QueryResultRow,
	SortDirection,
} from '../../types/query.types'

import { column, filter_group, parseFilterString, rawRowOf } from '../helpers'
import { ResultTable } from '../result_table'
import type { ChartSegmentClick } from '../../charts/drill/segment_click'

// `query` is whatever produced the rows — a query store, or a chart read store
// that holds a result and none of the authoring half. What it does not offer is
// not drawn.
//
// The chrome around the grid — the title, find, status, paging and export — is
// `ResultPane`'s. This is the grid and the query's own affordances on it, so a
// host that owns the cursor hands the slice down through `rows`.
const props = defineProps<{
	query: ResultTable
	/** the rows to draw, when the pane owns the slice. Defaults to the whole result. */
	rows?: QueryResultRow[]
	/** which page the slice came from, so the row gutter counts on */
	currentPage?: number
	pageSize?: number
	enableColumnRename?: boolean
	enableSort?: boolean
	enableDrillDown?: boolean
	enableNewColumn?: boolean
	onSortChange?: (column_name: string, sort_order: SortDirection) => void
	// what a cell's value opens, asked of the raw row — the caller reads the
	// value that was queried, not the one that was printed
	getCellLink?: (column: QueryResultColumn, row: QueryResultRow) => string | undefined
}>()

const emit = defineEmits<{ segmentClick: [click: ChartSegmentClick] }>()

const columns = computed(() => props.query.result.columns)
const rows = computed(() => props.rows ?? props.query.result.formattedRows)
const previewRowCount = computed(() => props.query.result.rows.length)

// a source with no paging of its own holds the whole result already
const currentPage = computed(() => props.currentPage ?? props.query.currentPage ?? 1)
const pageSize = computed(() => props.pageSize ?? props.query.pageSize ?? previewRowCount.value + 1)

// When the entire result fits on one page, filter client-side (instant, no round-trip)
const isSinglePage = computed(
	() => currentPage.value === 1 && previewRowCount.value < pageSize.value,
)

function onRename(column_name: string, new_name: string) {
	new_name = new_name.trim()
	if (new_name === column_name) return
	if (!new_name) return
	props.query.renameColumn?.(column_name, new_name)
}

const sortOrder = computed(() => {
	const _sortOrder = {} as Record<string, SortDirection>

	props.query.currentOperations?.forEach((operation) => {
		if (operation.type === 'order_by') {
			const column_name = operation.column.column_name
			const direction = operation.direction
			_sortOrder[column_name] = direction
		}
	})

	return _sortOrder
})

function onSortChange(column_name: string, sort_order: SortDirection) {
	if (props.onSortChange) {
		props.onSortChange(column_name, sort_order)
		return
	}

	if (!sort_order) {
		props.query.removeOrderBy?.(column_name)
		return
	}
	props.query.addOrderBy?.({
		column: column(column_name),
		direction: sort_order,
	})
}

// The table reports the click, it does not act on it: what a cell can be drilled
// against is the caller's to know, and so is the dialog. The table draws the
// formatted rows, so it is the table that crosses back to the raw one — a
// segment is pinned on what was queried, never on what was printed.
function onDrillDown(column: QueryResultColumn, formattedRow: QueryResultRow, event: MouseEvent) {
	const row = rawRowOf(props.query.result, formattedRow)
	if (!row) return
	emit('segmentClick', {
		target: { column: column.name, row },
		point: { x: event.clientX, y: event.clientY },
	})
}

function cellLink(column: QueryResultColumn, formattedRow: QueryResultRow) {
	const row = rawRowOf(props.query.result, formattedRow)
	return row ? props.getCellLink?.(column, row) : undefined
}

function onFilterChange(filters: Record<string, string>) {
	const adhocFilters = {} as AdhocFilters

	// Collect rules for ALL non-empty column filters into a single filter_group
	const allRules = [] as FilterArgs[]
	Object.entries(filters).forEach(([colName, filterStr]) => {
		if (!filterStr) return
		const parsed = parseFilterString(filterStr)
		if (!parsed) return

		if (parsed.kind === 'numeric') {
			allRules.push({
				column: column(colName),
				operator: parsed.operator,
				value: parsed.num,
			})
		} else {
			allRules.push({
				column: column(colName),
				operator: 'contains',
				value: parsed.text,
			})
		}
	})

	if (allRules.length && props.query.name) {
		adhocFilters[props.query.name] = filter_group({
			logical_operator: 'And',
			filters: allRules,
		})
	}

	props.query.adhocFilters = adhocFilters
	props.query.goToPage?.(1)
}
</script>

<template>
	<DataTable
		v-if="props.query.ready"
		:filtering="props.query.executing"
		:columns="columns"
		:rows="rows"
		:page-size="pageSize"
		:current-page="currentPage"
		:on-filter-change="isSinglePage ? undefined : onFilterChange"
		:sort-order="sortOrder"
		:on-sort-change="props.enableSort ? onSortChange : undefined"
		:on-column-rename="props.enableColumnRename ? onRename : undefined"
		:on-drilldown="props.enableDrillDown ? onDrillDown : undefined"
		:cell-link="props.getCellLink ? cellLink : undefined"
		:enable-new-column="props.enableNewColumn"
		v-bind="$attrs"
	>
		<template #header-prefix="{ column }">
			<slot name="header-prefix" :column="column" />
		</template>
		<template #header-suffix="{ column }">
			<slot name="header-suffix" :column="column" />
		</template>

		<template v-if="props.enableNewColumn" #new-column-editor="slotArgs">
			<slot name="new-column-editor" v-bind="slotArgs" />
		</template>
	</DataTable>
</template>
