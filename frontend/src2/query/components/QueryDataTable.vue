<script setup lang="ts">
import { Button, LoadingIndicator } from 'frappe-ui'
import { Bell, ChevronLeft, ChevronRight, Download, RefreshCw } from 'lucide-vue-next'
import { computed, ref, watch } from 'vue'
import DrillDown from '../../charts/components/DrillDown.vue'
import DataTable from '../../components/DataTable.vue'
import ExportDialog from '../../components/ExportDialog.vue'
import { QueryResultColumn, QueryResultRow, SortDirection } from '../../types/query.types'

import { column } from '../helpers'
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

const columns = computed(() => props.query.result.columns)
const rows = computed(() => props.query.result.formattedRows)
const previewRowCount = computed(() => props.query.result.rows.length)
const totalRowCount = computed(() => {
	if (!props.query.result.totalRowCount && previewRowCount.value < props.query.pageSize) {
		return previewRowCount.value
	}
	return props.query.result.totalRowCount
})

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

const isFirstPage = computed(() => props.query.currentPage <= 1)
const isLastPage = computed(() => {
	if (totalRowCount.value) {
		return props.query.currentPage >= Math.ceil(totalRowCount.value / props.query.pageSize)
	}
	return previewRowCount.value < props.query.pageSize
})
const isSinglePage = computed(() => isFirstPage.value && isLastPage.value)
const from = computed(() => (props.query.currentPage - 1) * props.query.pageSize + 1)
const to = computed(() => from.value + previewRowCount.value - 1)
</script>

<template>
	<DataTable
		:loading="props.query.executing"
		:columns="columns"
		:rows="rows"
		:enable-pagination="true"
		:total-row-count="totalRowCount"
		:current-page="props.query.currentPage"
		:on-page-change="onPageChange"
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
		<template #footer-left>
			<div v-if="!isSinglePage" class="flex w-full items-center justify-between">
				<div class="flex items-center gap-1 tnum text-sm text-gray-500">
					Showing {{ from }}–{{ to }} of
					<template v-if="totalRowCount">
						{{ totalRowCount.toLocaleString() }}
					</template>
					<template v-else>
						<template v-if="props.query.fetchingCount">
							<LoadingIndicator class="inline h-3.5 w-3.5 text-gray-500" />
						</template>
						<Tooltip v-else text="Load Count">
							<RefreshCw
								v-if="!props.query.fetchingCount"
								class="h-3.5 w-3.5 inline-flex cursor-pointer transition-all hover:text-gray-800"
								stroke-width="1.5"
								@click="props.query.fetchResultCount"
							/>
						</Tooltip>
					</template>
					rows
				</div>

				<div class="flex items-center gap-0.5">
					<Button
						variant="ghost"
						:disabled="isFirstPage"
						@click="onPageChange(props.query.currentPage - 1)"
					>
						<template #icon>
							<ChevronLeft class="h-4 w-4 text-gray-700" stroke-width="1.5" />
						</template>
					</Button>
					<span class="tnum min-w-[3rem] text-center text-sm text-gray-600">
						Page {{ props.query.currentPage }}
					</span>
					<Button
						variant="ghost"
						:disabled="isLastPage"
						@click="onPageChange(props.query.currentPage + 1)"
					>
						<template #icon>
							<ChevronRight class="h-4 w-4 text-gray-700" stroke-width="1.5" />
						</template>
					</Button>
				</div>
			</div>
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
