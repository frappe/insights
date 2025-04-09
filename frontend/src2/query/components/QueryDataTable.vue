<script setup lang="ts">
import { LoadingIndicator } from 'frappe-ui'
import { Bell, RefreshCw } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import DrillDown from '../../charts/components/DrillDown.vue'
import DataTable from '../../components/DataTable.vue'
import { QueryResultColumn, QueryResultRow, SortDirection } from '../../types/query.types'
import { column } from '../helpers'
import { Query } from '../query'
import QueryAlertsDialog from './QueryAlertsDialog.vue'
import AlertSetupDialog from './AlertSetupDialog.vue'

const props = defineProps<{
	query: Query
	enableAlerts?: boolean
	enableColumnRename?: boolean
	enableSort?: boolean
	enableDrillDown?: boolean
	onSortChange?: (column_name: string, sort_order: SortDirection) => void
}>()

const columns = computed(() => props.query.result.columns)
const rows = computed(() => props.query.result.formattedRows)
const previewRowCount = computed(() => props.query.result.rows.length)
const totalRowCount = computed(() => {
	if (!props.query.result.totalRowCount && previewRowCount.value < 100) {
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
function onDrillDown(column: QueryResultColumn, row: QueryResultRow) {
	drillDownQuery.value = props.query.getDrillDownQuery(column, row)
	if (drillDownQuery.value) {
		showDrillDown.value = true
	}
}

const showAlertsDialog = ref(false)
const currentAlertName = ref('')
</script>

<template>
	<DataTable
		:loading="props.query.executing"
		:columns="columns"
		:rows="rows"
		:enable-pagination="true"
		:on-export="props.query.downloadResults"
		:sort-order="sortOrder"
		:on-sort-change="props.enableSort ? onSortChange : undefined"
		:on-column-rename="props.enableColumnRename ? onRename : undefined"
		:on-drilldown="props.enableDrillDown ? onDrillDown : undefined"
		v-bind="$attrs"
	>
		<!-- pagination -->
		<template #header-prefix="{ column }">
			<slot name="header-prefix" :column="column" />
		</template>
		<template #header-suffix="{ column }">
			<slot name="header-suffix" :column="column" />
		</template>
		<template #footer-left>
			<div class="tnum flex items-center gap-1 text-sm text-gray-600">
				<span> Showing {{ previewRowCount.toLocaleString() }} of </span>
				<span v-if="!totalRowCount" class="inline-block">
					<Tooltip text="Load Count">
						<RefreshCw
							v-if="!props.query.fetchingCount"
							class="h-3.5 w-3.5 cursor-pointer transition-all hover:text-gray-800"
							stroke-width="1.5"
							@click="props.query.fetchResultCount"
						/>
						<LoadingIndicator v-else class="h-3.5 w-3.5 text-gray-600" />
					</Tooltip>
				</span>
				<span v-else> {{ totalRowCount.toLocaleString() }} </span>
				rows
			</div>
		</template>

		<template #footer-right-actions>
			<Button v-if="enableAlerts" variant="ghost" @click="showAlertsDialog = true">
				<template #icon>
					<Bell class="h-4 w-4 text-gray-700" stroke-width="1.5" />
				</template>
			</Button>
		</template>
	</DataTable>

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
