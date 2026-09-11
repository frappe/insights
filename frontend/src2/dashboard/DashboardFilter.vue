<script setup lang="ts">
import { Button } from 'frappe-ui'
import { X } from 'lucide-vue-next'
import { computed, inject, reactive, watchEffect, watch } from 'vue'
import FilterPicker from '../components/filter_picker/FilterPicker.vue'
import { columnIcon, summaryParts, type Filter } from '../components/filter_picker/filter_picker'
import { copy, wheneverChanges } from '../helpers'
import { FilterType } from '../helpers/constants'
import {
	ColumnDataType,
	FilterOperator,
	FilterValue,
	QueryResultColumn,
} from '../types/query.types'
import { WorkbookDashboardFilter } from '../types/workbook.types'
import { Dashboard } from './dashboard'
import DashboardFilterEditor from './DashboardFilterEditor.vue'
import { filterIconClass } from './filter_icons'

const dashboard = inject<Dashboard>('dashboard')!
const props = defineProps<{ item: WorkbookDashboardFilter }>()

const filter = reactive(copy(props.item))
watchEffect(() => Object.assign(filter, props.item))
if (!filter.links) {
	filter.links = {}
}

// The picker reads a column; a dashboard filter names itself and states a
// filter type. One column type per filter type, the one the picker reads back
// as that kind.
function columnTypeOf(filter_type: FilterType): ColumnDataType {
	if (filter_type === 'Number') return 'Decimal'
	if (filter_type === 'Date') return 'Date'
	return 'String'
}

const column = computed<QueryResultColumn>(() => ({
	name: filter.filter_name,
	type: columnTypeOf(filter.filter_type),
}))

// The filter names itself. Which column it reads is the server's to look up —
// the link that says so is read there, so there is one lookup rather than one
// per surface.
function stringValuesProvider() {
	return (search: string) => {
		const firstLinkedChart = Object.keys(filter.links)?.[0]
		if (!firstLinkedChart) return Promise.resolve([] as string[])
		return dashboard.getDistinctColumnValues(filter.filter_name, search, firstLinkedChart)
	}
}

// The author's icon is a `lucide-*` class Tailwind baked into the stylesheet. A
// filter authored against the old sprite may name a glyph this build has no CSS
// for, and that one falls back to the type icon.
const iconClass = computed(() => filterIconClass(filter.icon))

const filterState = reactive<{ operator?: FilterOperator; value?: FilterValue }>(
	copy(dashboard.filterStates[filter.filter_name] || {}),
)

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

const filters = computed<Filter[]>({
	get: () =>
		filterState.operator
			? [
					{
						column: column.value,
						operator: filterState.operator,
						value: filterState.value,
					},
			  ]
			: [],
	set: (rules) => {
		filterState.operator = rules[0]?.operator
		filterState.value = rules[0]?.value
	},
})

// the widget has no room for a sign column, so it reads the operator as a word
function summary(applied?: Filter) {
	if (!applied) return
	const { word, value } = summaryParts(applied)
	return [word, value].filter(Boolean).join(' ')
}

const isApplied = computed(() => Boolean(filterState.operator))

function clear() {
	filterState.operator = undefined
	filterState.value = undefined
}
</script>

<template>
	<div class="relative w-full">
		<FilterPicker
			v-model="filters"
			class="w-full"
			:column="column"
			:columns="[column]"
			:values-provider="stringValuesProvider"
		>
			<template #trigger="{ filter: applied }">
				<Button
					variant="outline"
					class="flex w-full !justify-start overflow-hidden text-sm [&>span]:truncate"
					:class="applied ? 'pe-7' : ''"
				>
					<template #prefix>
						<span v-if="iconClass" :class="iconClass" class="h-4 w-4 flex-shrink-0" />
						<component
							v-else
							:is="columnIcon(column)"
							class="h-4 w-4 flex-shrink-0"
							stroke-width="1.5"
						/>
					</template>
					<span class="text-ink-gray-8">
						{{ filter.filter_name }}
						<span v-if="applied" class="font-medium">{{ summary(applied) }}</span>
					</span>
				</Button>
			</template>
		</FilterPicker>

		<!-- beside the trigger, not inside it: a click within reka's trigger opens
		     the popover, and clearing is not choosing -->
		<Button
			v-if="isApplied"
			variant="ghost"
			size="xs"
			:label="__('Clear')"
			class="absolute end-0.5 top-0.5"
			@click.stop="clear"
		>
			<template #icon><X stroke-width="1.5" /></template>
		</Button>
	</div>

	<DashboardFilterEditor v-if="dashboard.isEditingItem(props.item)" :item="props.item" />
</template>
