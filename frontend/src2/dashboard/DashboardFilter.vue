<script setup lang="ts">
import { Button } from 'frappe-ui'
import { X } from 'lucide-vue-next'
import { computed } from 'vue'
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
import { filterIconClass } from './filter_icons'
import { watchFilterDefault, type DashboardView, type DashboardViewItem } from './view'

// A filter cell, on every dashboard page. The page owns the filter's state and
// its column. The builder keeps both in its store. A view page asks the server
// by filter name.
const props = defineProps<{ item: DashboardViewItem; dashboard: DashboardView }>()

// Derived, not copied: a key the editor removes has to leave the local view too,
// and an assign onto a held object can only add.
const filter = computed(() => ({
	...props.item,
	filter_name: props.item.filter_name || '',
	filter_type: props.item.filter_type || 'String',
}))

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
	return (search: string) => props.dashboard.filterValues(filter.value.filter_name, search)
}

// The numbers a number filter offers, cut from the column the link names. The
// server finds that column, the same way it does for the value list.
function rangeProvider() {
	return props.dashboard.filterRange(filter.value.filter_name)
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
	() => props.dashboard.filters[filter.value.filter_name] || {},
)

function setFilter(operator?: FilterOperator, value?: FilterValue) {
	props.dashboard.setFilter(filter.value.filter_name, operator ? { operator, value } : undefined)
}

// not on mount, so the restored state is kept
watchFilterDefault(() => filter.value, setFilter)

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
			<template #icon><X class="size-3.5" stroke-width="1.5" /></template>
		</Button>
	</div>
</template>
