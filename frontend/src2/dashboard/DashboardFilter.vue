<script setup lang="ts">
import { computed, inject, reactive, watch, watchEffect } from 'vue'
import { copy, wheneverChanges } from '../helpers'
import { FIELDTYPES } from '../helpers/constants'
import DataTypeIcon from '../query/components/DataTypeIcon.vue'
import { ColumnDataType } from '../types/query.types'
import { WorkbookDashboardFilter } from '../types/workbook.types'
import { Dashboard } from './dashboard'
import DashboardFilterEditor from './DashboardFilterEditor.vue'
import Filter from './Filter.vue'

const dashboard = inject<Dashboard>('dashboard')!
const props = defineProps<{ item: WorkbookDashboardFilter }>()

const filter = reactive(copy(props.item))
watchEffect(() => Object.assign(filter, copy(props.item)))
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
	return dashboard.getDistinctColumnValues(
		sourceColumn.value.query,
		sourceColumn.value.column,
		search,
	)
}

const filterState = reactive(copy(dashboard.filterStates[filter.filter_name] || {}))
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
		<Popover class="h-full">
			<template #target="{ togglePopover }">
				<Button
					variant="outline"
					class="flex h-full w-full !justify-start overflow-hidden text-sm shadow-sm [&>span]:truncate"
					@click="togglePopover"
				>
					<template #prefix>
						<DataTypeIcon
							v-if="filter.filter_type"
							:column-type="FILTER_TYPES[filter.filter_type][0] as ColumnDataType"
							class="h-4 w-4 flex-shrink-0"
							stroke-width="1.5"
						/>
					</template>
					{{ label }}
				</Button>
			</template>
			<template #body-main="{ togglePopover, isOpen }">
				<div class="w-full p-2">
					<Filter
						v-if="isOpen"
						:filter-type="filter.filter_type"
						:valuesProvider="stringValuesProvider"
						v-model:operator="filterState.operator"
						v-model:value="filterState.value"
						@update:value="() => togglePopover()"
					>
					</Filter>
				</div>
			</template>
		</Popover>
	</div>

	<DashboardFilterEditor v-if="dashboard.isEditingItem(props.item)" :item="props.item" />
</template>
