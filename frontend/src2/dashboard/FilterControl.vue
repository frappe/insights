<script setup lang="ts">
import { Icon } from 'frappe-ui/icons'
import { computed } from 'vue'
import { FIELDTYPES, FilterType } from '../helpers/constants'
import DataTypeIcon from '../query/components/DataTypeIcon.vue'
import { isFilterApplied } from '../query/components/filter_utils'
import { ColumnDataType, FilterOperator, FilterValue } from '../types/query.types'
import Filter from './Filter.vue'

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

// frappe-ui's `Icon` is a reference into a sprite an SPA plugin puts in
// `document.body`, which no desk page has and no shadow root could reach. So in
// an island the author's icon paints an empty box and the type icon is drawn
// instead. Shipping the sprite was the alternative: 457 kB for a few glyphs.
const iconAvailable = computed(
	() => Boolean(props.icon) && Boolean(document.getElementById('lucide-sprite')),
)

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
						<Icon
							v-if="iconAvailable"
							:name="props.icon!"
							class="h-4 w-4 flex-shrink-0"
						/>
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
			<template #default="{ toggle: togglePopover, isOpen }">
				<div class="p-2" :style="{ width: 'var(--reka-popover-trigger-width)' }">
					<Filter
						v-if="isOpen"
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
