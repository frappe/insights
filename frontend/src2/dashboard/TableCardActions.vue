<script setup lang="ts">
// The title row of a table card: the reader's two acts on the rows in front of
// them. Filter is the host's and reaches the server as a card filter; find is
// the table's and never leaves the browser. Both are icons here, the size of
// the edit and expand icons they stand beside, because a card's title row is
// the card's title.
//
// The find text is the card's state, so it is a model rather than something
// held here: the card is what hands it to the grid.
import { Button, TextInput, Tooltip } from 'frappe-ui'
import { ListFilter, Search } from 'lucide-vue-next'
import { computed, nextTick, ref, watchEffect } from 'vue'
import FilterPicker from '../components/filter_picker/FilterPicker.vue'
import type { Filter } from '../components/filter_picker/filter_picker'
import { __ } from '../translation'
import type { QueryResultColumn } from '../types/query.types'

const props = defineProps<{
	columns: QueryResultColumn[]
	valuesProvider: (column: QueryResultColumn) => (search: string) => Promise<string[]>
	/** Whether the acts wait for the card to be pointed at. A public link has no
	 *  hover affordances to keep company with, so there they stand. */
	reveal?: boolean
}>()

const filters = defineModel<Filter[]>('filters', { default: () => [] })
const findText = defineModel<string>('findText', { default: '' })
const findOpen = defineModel<boolean>('findOpen', { default: false })

const findInput = ref<any>()
function openFind() {
	findOpen.value = true
	nextTick(() => findInput.value?.focus())
}
function closeFind() {
	findOpen.value = false
	findText.value = ''
}

// the popover is portaled out of the card, so a pointer over it has left the
// hover group; the row stays revealed while the popover or the find is open
const pickerOpen = ref(false)
const active = defineModel<boolean>('active', { default: false })
watchEffect(() => (active.value = pickerOpen.value || findOpen.value))
const revealClass = computed(() =>
	props.reveal && !active.value ? 'opacity-0 transition-opacity group-hover:opacity-100' : '',
)
const filterTooltip = computed(() =>
	filters.value.length ? __('Filters ({0})', String(filters.value.length)) : __('Filter'),
)
</script>

<template>
	<div class="flex items-center gap-1">
		<!-- the find takes the row while it is open: a card title row holds one
		     act's worth of width, and the input is that act -->
		<TextInput
			v-if="findOpen"
			ref="findInput"
			v-model="findText"
			size="sm"
			class="w-36"
			:placeholder="__('Find in rows')"
			@keydown.escape="closeFind()"
			@blur="!findText && closeFind()"
		>
			<template #prefix>
				<Search class="size-4 text-ink-gray-5" stroke-width="1.5" />
			</template>
		</TextInput>
		<Tooltip v-else :text="__('Find')">
			<Button variant="ghost" :class="revealClass" @click="openFind()">
				<Search class="h-3.5 w-3.5 text-ink-gray-6" stroke-width="1.5" />
			</Button>
		</Tooltip>

		<FilterPicker
			v-model="filters"
			v-model:open="pickerOpen"
			:columns="props.columns"
			:values-provider="props.valuesProvider"
		>
			<!-- The picker's own button carries a label, which beside a card
				     title reads as a second title. Here it is one of the card's
				     icons, and the dot is what says the rows are narrowed.
				     The click is wired here rather than left to the popover: the
				     tooltip around the button drops the props the trigger would
				     otherwise hand it. -->
			<template #trigger="{ toggle }">
				<Tooltip :text="filterTooltip">
					<Button
						:variant="filters.length || pickerOpen ? 'subtle' : 'ghost'"
						:class="revealClass"
						:label="filters.length ? String(filters.length) : undefined"
						@click="toggle()"
					>
						<template v-if="filters.length" #prefix>
							<ListFilter class="h-3.5 w-3.5 text-ink-gray-6" stroke-width="1.5" />
						</template>
						<template v-else #icon>
							<ListFilter class="h-3.5 w-3.5 text-ink-gray-6" stroke-width="1.5" />
						</template>
					</Button>
				</Tooltip>
			</template>
		</FilterPicker>
	</div>
</template>
