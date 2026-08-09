<script setup lang="ts">
import { computed } from 'vue'
import { FIELDTYPES, FilterType } from '../helpers/constants'
import DataTypeIcon from '../query/components/DataTypeIcon.vue'
import { isFilterApplied } from '../query/components/filter_utils'
import { ColumnDataType, FilterOperator, FilterValue } from '../types/query.types'
import Filter from './Filter.vue'
import { filterIconClass } from './filter_icons'

// One filter, as the reader meets it: a grid cell that names itself when it is
// empty and shows what it is holding when it is not. Where the state lives and
// which column it lands on are the caller's business, and that is the whole of
// what the two feeds differ by — the builder keeps both in its store, a read
// surface asks the server by filter name.
const props = defineProps<{
	filterName: string
	filterType: FilterType
	icon?: string
	valuesProvider: (search: string) => Promise<string[]>
}>()

const operator = defineModel<FilterOperator>('operator')
const value = defineModel<FilterValue>('value')

const FILTER_TYPES = {
	String: FIELDTYPES.TEXT,
	Number: FIELDTYPES.NUMBER,
	Date: FIELDTYPES.DATE,
}

const applied = computed(() => isFilterApplied(props.filterType, operator.value, value.value))

// The author's icon is a `lucide-*` class Tailwind baked into the stylesheet,
// so it draws wherever the stylesheet reaches — the SPA and a desk island's
// shadow root alike. A filter authored against the old sprite may name a glyph
// this build has no CSS for, and that one falls back to the type icon.
const iconClass = computed(() => filterIconClass(props.icon))

const label = computed(() => {
	if (!applied.value) return props.filterName
	if (value.value === undefined) return `${props.filterName} ${operator.value}`
	const value_str = Array.isArray(value.value) ? value.value.join(', ') : value.value
	return `${props.filterName} ${operator.value} ${value_str}`
})
</script>

<template>
	<div class="h-8 [&>div:first-child]:h-full">
		<Popover class="h-full" match-trigger-width>
			<template #trigger>
				<Button
					variant="outline"
					class="flex h-full w-full !justify-start overflow-hidden text-sm [&>span]:truncate"
				>
					<template #prefix>
						<span v-if="iconClass" :class="iconClass" class="h-4 w-4 flex-shrink-0" />
						<DataTypeIcon
							v-else-if="props.filterType"
							:column-type="FILTER_TYPES[props.filterType][0] as ColumnDataType"
							class="h-4 w-4 flex-shrink-0"
							stroke-width="1.5"
						/>
					</template>
					{{ label }}
				</Button>
			</template>
			<template #default="{ toggle: togglePopover, open }">
				<div class="p-2" :style="{ width: 'var(--reka-popover-trigger-width)' }">
					<Filter
						v-if="open"
						:filter-type="props.filterType"
						:valuesProvider="props.valuesProvider"
						v-model:operator="operator"
						v-model:value="value"
						@close="() => togglePopover()"
					/>
				</div>
			</template>
		</Popover>
	</div>
</template>
