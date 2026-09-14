<script setup lang="ts">
import { Button } from 'frappe-ui'
import { X } from 'lucide-vue-next'
import { computed, inject, watch } from 'vue'
import FilterPicker from '../components/filter_picker/FilterPicker.vue'
import { summaryParts, type Filter } from '../components/filter_picker/filter_picker'
import { columnIcon } from '../query/column_icon'
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

// Derived, not copied: a key the editor removes has to leave the local view too,
// and an assign onto a held object can only add.
const filter = computed(() => ({ ...props.item, links: props.item.links || {} }))

// The picker reads a column; a dashboard filter names itself and states a
// filter type. One column type per filter type, the one the picker reads back
// as that kind.
function columnTypeOf(filter_type: FilterType): ColumnDataType {
	if (filter_type === 'Number') return 'Decimal'
	if (filter_type === 'Date') return 'Date'
	return 'String'
}

const column = computed<QueryResultColumn>(() => ({
	name: filter.value.filter_name,
	type: columnTypeOf(filter.value.filter_type),
}))

// The filter names itself. Which column it reads is the server's to look up —
// the link that says so is read there, so there is one lookup rather than one
// per surface.
function stringValuesProvider() {
	return (search: string) => {
		const firstLinkedChart = Object.keys(filter.value.links)?.[0]
		if (!firstLinkedChart) return Promise.resolve([] as string[])
		return dashboard.getDistinctColumnValues(filter.value.filter_name, search, firstLinkedChart)
	}
}

// The numbers a number filter offers, cut from the column the link names. The
// server finds that column, the same way it does for the value list.
function rangeProvider() {
	return dashboard.getFilterColumnRange(filter.value.filter_name)
}

// The author's icon is a `lucide-*` class Tailwind baked into the stylesheet. A
// filter authored against the old sprite may name a glyph this build has no CSS
// for, and that one falls back to the type icon.
const iconClass = computed(() => filterIconClass(filter.value.icon))

// The store is where this filter is set, and the control reads it rather than a
// copy of it: the same filter is unset elsewhere (a card's "Reset filters"),
// and a control answering a copy would still read as set and push the value it
// kept back on the next keystroke.
const filterState = computed<{ operator?: FilterOperator; value?: FilterValue }>(
	() => dashboard.filterStates[filter.value.filter_name] || {},
)

function setFilter(operator?: FilterOperator, value?: FilterValue) {
	dashboard.updateFilterState(filter.value.filter_name, operator, value)
}

// no `immediate` — on mount, the state the store restored is what stands
watch(
	() => [filter.value.default_operator, filter.value.default_value],
	([op, val]) => {
		if (op != null && val != null) setFilter(op as FilterOperator, val)
	},
	{ deep: true },
)

const filters = computed<Filter[]>({
	get: () =>
		filterState.value.operator
			? [
					{
						column: column.value,
						operator: filterState.value.operator,
						value: filterState.value.value,
					},
			  ]
			: [],
	set: (rules) => setFilter(rules[0]?.operator, rules[0]?.value),
})

// the trigger has no room for a sign column, so it reads the operator as a word
function summary(applied?: Filter) {
	if (!applied) return
	const { word, value } = summaryParts(applied)
	return [word, value].filter(Boolean).join(' ')
}

const isApplied = computed(() => Boolean(filterState.value.operator))

function clear() {
	setFilter()
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
			:range-provider="rangeProvider"
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
							:is="columnIcon(column.type)"
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
