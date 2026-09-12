<script setup lang="ts">
// Every stage is this list. reka owns the highlight, the arrow keys and the
// scrolling; this file only renders rows and reports a pick.
import { Button, Checkbox, LoadingIndicator } from 'frappe-ui'
import { X } from 'lucide-vue-next'
import { ComboboxItem, ComboboxViewport, ListboxContent } from 'reka-ui'
import { __ } from '../../translation'
import type { ListItem } from './filter_picker'

defineProps<{
	items: ListItem[]
	stage: string
	loading?: boolean
	empty?: string
}>()
const emit = defineEmits<{ pick: [item: ListItem]; remove: [item: ListItem] }>()

// copied from frappe-ui's src/components/shared/selection/utils.ts — the package
// exports no subpath that reaches it
const itemClasses =
	'select-none rounded-4 border-0 text-base text-ink-gray-9 transition-colors duration-100 ease-out data-[disabled]:text-ink-gray-4 data-[highlighted]:bg-surface-alpha-gray-2 data-[state=checked]:bg-surface-gray-3 data-[highlighted]:data-[state=checked]:bg-surface-gray-4'

// ItemListRow.vue's layout and its `sm` scale
const rowClasses = 'group flex w-full items-center gap-2 rounded-4 min-h-7 px-2 py-1.5 text-base'

/** a reka-owned row's value is reka's, so the tick reads back as `data-state` */
function valueOf(item: ListItem) {
	return item.tick ? item.label : item.key
}

/** reka owns the model on the multi stage's rows only; every other row is ours */
function onSelect(item: ListItem, event: Event) {
	if (!item.tick) event.preventDefault()
}

/**
 * reka's ListboxItem carries our listeners twice: once through the `$attrs` it
 * spreads onto the row itself, once through Vue's own fallthrough. One click
 * would then pick the row twice and walk two stages on one Enter, so only the
 * first run of an event counts.
 */
let picked: MouseEvent | undefined
function onClick(item: ListItem, event: MouseEvent) {
	if (picked === event) return
	picked = event
	emit('pick', item)
}

/**
 * reka's ListboxItem memoises its row on the highlight and the tick alone
 * (ListboxItem.vue, the `v-memo` at line 79), so anything else the row draws
 * has to arrive as a new key. The stage leads, so a stage change re-mounts
 * every row and no memoised row outlives the list it was drawn for. A
 * reka-owned tick is left out — it moves reka's own model and invalidates the
 * memo by itself.
 */
function keyOf(item: ListItem, stage: string) {
	return [
		stage,
		item.key,
		item.label,
		item.operator ?? '',
		item.value ?? '',
		item.note ?? '',
		item.tick ? '' : String(item.checked ?? ''),
	].join('|')
}
</script>

<template>
	<ListboxContent>
		<ComboboxViewport class="flex max-h-80 flex-col overflow-auto p-1">
			<template v-for="item in items" :key="keyOf(item, stage)">
				<div v-if="item.separated" class="-mx-1 my-1 border-t border-outline-gray-1" />
				<ComboboxItem
					:value="valueOf(item)"
					:data-row-key="item.key"
					:class="[itemClasses, rowClasses]"
					@select="onSelect(item, $event)"
					@mousedown.prevent
					@click="onClick(item, $event)"
				>
					<Checkbox
						v-if="item.checked !== undefined"
						:model-value="item.checked"
						size="sm"
						tabindex="-1"
						aria-hidden="true"
						class="pointer-events-none"
					/>
					<component
						:is="item.icon"
						v-if="item.icon"
						class="size-4 shrink-0 text-ink-gray-5"
						stroke-width="1.5"
					/>
					<span
						class="truncate text-start"
						:class="
							item.operator !== undefined ? 'font-medium text-ink-gray-8' : 'flex-1'
						"
						>{{ item.label }}</span
					>
					<template v-if="item.operator !== undefined">
						<span class="shrink-0 text-ink-gray-5">{{ item.operator }}</span>
						<span class="flex-1 truncate text-start text-ink-gray-6">{{
							item.value
						}}</span>
					</template>
					<span v-if="item.note" class="shrink-0 text-sm text-ink-gray-5">{{
						item.note
					}}</span>
					<Button
						v-if="item.removable"
						variant="ghost"
						size="xs"
						:label="__('Remove')"
						class="-me-1.5 -my-1 shrink-0 opacity-0 group-hover:opacity-100 group-data-[highlighted]:opacity-100"
						@mousedown.prevent
						@click.stop="emit('remove', item)"
					>
						<template #icon><X class="size-3" stroke-width="1.5" /></template>
					</Button>
				</ComboboxItem>
			</template>

			<div
				v-if="loading && !items.length"
				class="flex items-center gap-2 px-2 py-1.5 text-base text-ink-gray-5"
			>
				<LoadingIndicator class="size-4" />
				{{ __('Searching...') }}
			</div>
			<div v-else-if="!items.length && empty" class="px-2 py-1.5 text-base text-ink-gray-5">
				{{ empty }}
			</div>
		</ComboboxViewport>
	</ListboxContent>
</template>
