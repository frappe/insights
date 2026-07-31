<script setup lang="ts">
import { Icon } from 'frappe-ui/icons'
import { computed, inject, reactive, watchEffect, watch } from 'vue'
import { copy, wheneverChanges } from '../helpers'
import { FIELDTYPES } from '../helpers/constants'
import DataTypeIcon from '../query/components/DataTypeIcon.vue'
import { ColumnDataType, FilterOperator } from '../types/query.types'
import { WorkbookDashboardFilter } from '../types/workbook.types'
import { Dashboard } from './dashboard'
import DashboardFilterEditor from './DashboardFilterEditor.vue'
import Filter from './Filter.vue'

const dashboard = inject<Dashboard>('dashboard')!
const props = defineProps<{ item: WorkbookDashboardFilter }>()

const filter = reactive(copy(props.item))
watchEffect(() => Object.assign(filter, props.item))
if (!filter.links) {
	filter.links = {}
}

const FILTER_TYPES = {
	String: FIELDTYPES.TEXT,
	Number: FIELDTYPES.NUMBER,
	Date: FIELDTYPES.DATE,
}

const sourceColumn = computed(() => {
	const firstChart = Object.keys(filter.links)[0]
	if (!firstChart) return
	const linkedColumn = filter.links[firstChart]
	return dashboard.getColumnFromFilterLink(linkedColumn)
})

function stringValuesProvider(search: string) {
	if (!sourceColumn.value) return Promise.resolve([])

	const firstLinkedChart = Object.keys(filter.links)?.[0]
	const adhocFilters = firstLinkedChart
		? dashboard.getAdhocFilters(firstLinkedChart, filter.filter_name)
		: undefined

	return dashboard.getDistinctColumnValues(
		sourceColumn.value.query,
		sourceColumn.value.column,
		search,
		adhocFilters,
	)
}

const filterState = reactive(copy(dashboard.filterStates[filter.filter_name] || {}))

// no `immediate` — on mount, filterState must keep the restored state from dashboard.filterStates
watch(
	() => [filter.default_operator, filter.default_value],
	([op, val]) => {
		if (op != null && val != null) {
			filterState.operator = op as FilterOperator
			filterState.value = val
		}
	},
	{ deep: true },
)

wheneverChanges(
	() => filterState,
	() => {
		dashboard.updateFilterState(filter.filter_name, filterState.operator, filterState.value)
	},
	{ deep: true },
)

const label = computed(() => {
	let _label = filter.filter_name
	if (filterState.operator && filterState.value) {
		const value_str = Array.isArray(filterState.value)
			? filterState.value.join(', ')
			: filterState.value
		_label += ` ${filterState.operator} ${value_str}`
	}
	return _label
})
</script>

<template>
	<div class="h-8 w-full [&>div:first-child]:h-full">
		<Popover class="h-full" match-trigger-width>
			<template #trigger>
				<Button
					variant="outline"
					class="flex h-full w-full !justify-start overflow-hidden text-sm [&>span]:truncate"
				>
					<template #prefix>
						<Icon
							v-if="filter.icon"
							:name="filter.icon"
							class="h-4 w-4 flex-shrink-0"
						/>
						<DataTypeIcon
							v-else-if="filter.filter_type"
							:column-type="FILTER_TYPES[filter.filter_type][0] as ColumnDataType"
							class="h-4 w-4 flex-shrink-0"
							stroke-width="1.5"
						/>
					</template>
					{{ label }}
				</Button>
			</template>
			<template #default="{ toggle: togglePopover, isOpen }">
				<div class="p-2" :style="{ width: 'var(--reka-popover-trigger-width)' }">
					<Filter
						v-if="isOpen"
						:filter-type="filter.filter_type"
						:valuesProvider="stringValuesProvider"
						v-model:operator="filterState.operator"
						v-model:value="filterState.value"
						@close="() => togglePopover()"
					>
					</Filter>
				</div>
			</template>
		</Popover>
	</div>

	<DashboardFilterEditor v-if="dashboard.isEditingItem(props.item)" :item="props.item" />
</template>
