<script setup lang="ts">
import { Button } from 'frappe-ui'
import { Bell, Download } from 'lucide-vue-next'
import { computed, ref, watch } from 'vue'
import DrillDown from '../../charts/components/DrillDown.vue'
import DataTable from '../../components/DataTable.vue'
import ExportDialog from '../../components/ExportDialog.vue'
import {
	AdhocFilters,
	FilterArgs,
	QueryResultColumn,
	QueryResultRow,
	SortDirection,
} from '../../types/query.types'

import { column, filter_group, parseFilterString } from '../helpers'
import { Query } from '../query'
import AlertSetupDialog from './AlertSetupDialog.vue'
import QueryAlertsDialog from './QueryAlertsDialog.vue'

const props = defineProps<{
	query: Query
	enableAlerts?: boolean
	enableColumnRename?: boolean
	enableSort?: boolean
	enableDrillDown?: boolean
	enableNewColumn?: boolean
	onSortChange?: (column_name: string, sort_order: SortDirection) => void
}>()

const isFiltering = ref(false)
watch(
	() => props.query.executing,
	(executing) => {
		if (!executing) isFiltering.value = false
	},
)

const columns = computed(() => props.query.result.columns)
const rows = computed(() => props.query.result.formattedRows)
const previewRowCount = computed(() => props.query.result.rows.length)
const totalRowCount = computed(() => props.query.result.totalRowCount || undefined)

// When the entire result fits on one page, filter client-side (instant, no round-trip)
const isSinglePage = computed(
	() => props.query.currentPage === 1 && previewRowCount.value < props.query.pageSize,
)

function onRename(column_name: string, new_name: string) {
	new_name = new_name.trim()
	if (new_name === column_name) return
	if (!new_name) return
	props.query.renameColumn(column_name, new_name)
}

const sortOrder = computed(() => {
	const _sortOrder = {} as Record<string, SortDirection>

	props.query.currentOperations.forEach((operation) => {
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
		props.query.removeOrderBy(column_name)
		return
	}
	props.query.addOrderBy({
		column: column(column_name),
		direction: sort_order,
	})
}

const showDrillDown = ref(false)
const drillDownQuery = ref<Query>()
async function onDrillDown(column: QueryResultColumn, row: QueryResultRow) {
	drillDownQuery.value = await props.query.getDrillDownQuery(column, row)
	if (drillDownQuery.value) {
		showDrillDown.value = true
	}
}

const showAlertsDialog = ref(false)
const currentAlertName = ref('')

// Export dialog state
const showExportDialog = ref(false)
const exportDefaultName = computed(() => {
	const now = new Date()
	const ts = `${now.getDate()}_${now.getMonth()}_${now.getFullYear()}`
	return `export_${ts}`
})

function openExport() {
	if (!props.query?.exportResults) return
	showExportDialog.value = true
}

// Auto-close dialog after export completes
watch(
	() => props.query.downloading,
	(downloading, prev) => {
		if (prev && !downloading) {
			showExportDialog.value = false
		}
	},
)

function onExport(format: 'csv' | 'excel', filename: string) {
	props.query.exportResults(format, filename)
}

function onPageChange(page: number) {
	props.query.goToPage(page)
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

	if (allRules.length) {
		adhocFilters[props.query.name] = filter_group({
			logical_operator: 'And',
			filters: allRules,
		})
	}

	props.query.adhocFilters = adhocFilters

	isFiltering.value = true
	props.query.goToPage(1)
}
</script>

<template>
	<DataTable
		:loading="props.query.executing && !isFiltering"
		:filtering="props.query.executing && isFiltering"
		:columns="columns"
		:rows="rows"
		:enable-pagination="true"
		:total-row-count="totalRowCount"
		:current-page="props.query.currentPage"
		:on-page-change="onPageChange"
		:on-fetch-count="props.query.fetchResultCount"
		:on-filter-change="isSinglePage ? undefined : onFilterChange"
		:on-export="props.query.exportResults"
		:downloading="props.query.downloading"
		:sort-order="sortOrder"
		:on-sort-change="props.enableSort ? onSortChange : undefined"
		:on-column-rename="props.enableColumnRename ? onRename : undefined"
		:on-drilldown="props.enableDrillDown ? onDrillDown : undefined"
		:enable-new-column="props.enableNewColumn"
		v-bind="$attrs"
	>
		<template #header-prefix="{ column }">
			<slot name="header-prefix" :column="column" />
		</template>
		<template #header-suffix="{ column }">
			<slot name="header-suffix" :column="column" />
		</template>
		<template #footer-right-actions>
			<Button v-if="enableAlerts" variant="ghost" @click="showAlertsDialog = true">
				<template #icon>
					<Bell class="h-4 w-4 text-gray-700" stroke-width="1.5" />
				</template>
			</Button>
			<Button variant="ghost" @click="openExport">
				<template #icon>
					<Download class="h-4 w-4 text-gray-700" stroke-width="1.5" />
				</template>
			</Button>
		</template>

		<template v-if="props.enableNewColumn" #new-column-editor="slotArgs">
			<slot name="new-column-editor" v-bind="slotArgs" />
		</template>
	</DataTable>
	<ExportDialog
		v-model="showExportDialog"
		:downloading="props.query.downloading"
		:default-filename="exportDefaultName"
		@export="onExport"
		@cancel="props.query.cancelDownload"
	/>

	<DrillDown
		v-if="drillDownQuery"
		v-model="showDrillDown"
		@update:model-value="!$event ? (drillDownQuery = undefined) : undefined"
		:query="drillDownQuery"
	>
	</DrillDown>

	<QueryAlertsDialog
		v-if="showAlertsDialog"
		v-model="showAlertsDialog"
		:query="props.query"
		@set-current-alert-name="currentAlertName = $event"
	>
	</QueryAlertsDialog>

	<AlertSetupDialog
		v-if="currentAlertName"
		:modelValue="Boolean(currentAlertName)"
		@update:model-value="!$event ? (currentAlertName = '') : undefined"
		:query="props.query"
		:alert_name="currentAlertName"
	/>
</template>
