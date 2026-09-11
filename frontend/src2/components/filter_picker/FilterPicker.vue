<script setup lang="ts">
// The filter picker, in its two mounts. Without `column` it is the whole
// picker: a Filter button, and the stages that let the reader choose a column,
// an operator and a value, with the applied filters on an overview stage
// inside. With `column` the column is already chosen, the trigger names it,
// opening lands on the operator stage, and the model holds at most one filter.
import { Badge, Button, Popover } from 'frappe-ui'
import { ListFilter, X } from 'lucide-vue-next'
import { computed } from 'vue'
import { __ } from '../../translation'
import type { QueryResultColumn } from '../../types/query.types'
import { columnIcon, summaryParts, type Filter } from './filter_picker'
import FilterPickerPanel from './FilterPickerPanel.vue'

// `defineModel` puts `modelValue` in the same props object `defineProps`
// returns, so the panel is handed each prop by name: a `v-bind="props"` would
// pass the filters on as `modelValue` too, and that is a prop of the panel's
// own root.
const props = defineProps<{
	columns: QueryResultColumn[]
	valuesProvider: (column: QueryResultColumn) => (search: string) => Promise<string[]>
	column?: QueryResultColumn
}>()
const model = defineModel<Filter[]>({ default: () => [] })

defineSlots<{
	trigger?: (props: { filter?: Filter; open: boolean; toggle: () => void }) => any
}>()

// a host may bind `v-model:open`, e.g. to keep a hover-revealed toolbar shown while the popover is up
const open = defineModel<boolean>('open', { default: false })

const count = computed(() => model.value.length)
/** the column mount holds at most one filter, and its trigger reads it */
const filter = computed(() => model.value[0])
/** a column mount opens on the filter it already holds */
const initial = computed(() => (props.column ? filter.value : undefined))

function onCommit(committed: Filter, replacing?: Filter) {
	if (props.column) {
		model.value = [committed]
		return
	}
	const index = replacing ? model.value.indexOf(replacing) : -1
	model.value =
		index >= 0
			? model.value.map((f, i) => (i === index ? committed : f))
			: [...model.value, committed]
}

function remove(target: Filter) {
	model.value = model.value.filter((f) => f !== target)
}

function clear() {
	model.value = []
}

/** what the column trigger reads after the `·`: `<sign> value-summary` */
const valueText = computed(() => {
	if (!filter.value) return __('Any')
	const { operator, value } = summaryParts(filter.value)
	return [operator, value].filter(Boolean).join(' ')
})
</script>

<template>
	<div class="inline-flex">
		<Popover
			v-model:open="open"
			bare
			:align="column ? 'start' : 'end'"
			:offset="4"
			:auto-focus="false"
		>
			<template #trigger="{ toggle }">
				<slot name="trigger" :filter="filter" :open="open" :toggle="toggle">
					<Button v-if="column" variant="subtle" :class="count ? '' : 'text-ink-gray-5'">
						<template #prefix>
							<component :is="columnIcon(column)" class="size-4" stroke-width="1.5" />
						</template>
						<span class="text-ink-gray-6">{{ column.name }}</span>
						<span class="text-ink-gray-4">·</span>
						<span :class="count ? 'font-medium text-ink-gray-8' : ''">{{
							valueText
						}}</span>
					</Button>
					<Button
						v-else
						variant="subtle"
						:label="__('Filter')"
						:class="count ? 'rounded-e-none' : ''"
					>
						<template #prefix
							><ListFilter class="size-4" stroke-width="1.5"
						/></template>
						<template v-if="count" #suffix>
							<!-- outline, not subtle: a subtle badge fills with the
							     same gray the subtle button is already painted in,
							     and the count loses its pill -->
							<Badge
								variant="outline"
								theme="gray"
								size="sm"
								:label="String(count)"
							/>
						</template>
					</Button>
				</slot>
			</template>

			<FilterPickerPanel
				:columns="columns"
				:values-provider="valuesProvider"
				:column="column"
				:filters="model"
				:initial="initial"
				@commit="onCommit"
				@remove="remove"
				@close="open = false"
			/>
		</Popover>
		<Button
			v-if="!column && count && !$slots.trigger"
			variant="subtle"
			:label="__('Clear filters')"
			class="rounded-s-none border-s border-outline-gray-3"
			@click="clear"
		>
			<template #icon><X class="size-4" stroke-width="1.5" /></template>
		</Button>
	</div>
</template>
