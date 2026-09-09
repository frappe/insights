<script setup lang="ts">
import { FormControl } from 'frappe-ui'
import { CornerDownLeft, Search } from 'lucide-vue-next'
import { computed, nextTick, ref, watch } from 'vue'
import { columnIcon } from '../../query/column_icon'
import { __ } from '../../translation'
import type { QueryResultColumn } from '../../types/query.types'
import { findColumns } from './find'

// One box, two jobs. The row job is live in the grid behind this panel. The
// column job needs a list, so the panel carries both and says which is which.
const props = defineProps<{
	columns: QueryResultColumn[]
	/** how many rows the term keeps, so the panel can say what it costs */
	matchCount: number
}>()

const emit = defineEmits<{ jump: [column_name: string] }>()

const term = defineModel<string>({ default: '' })

const focused = ref(false)
const panelOpen = ref(false)
const activeIndex = ref(0)
const $input = ref<any>(null)

const matched = computed(() => findColumns(props.columns, term.value))

watch(term, () => {
	panelOpen.value = Boolean(term.value)
	activeIndex.value = 0
})

function onFocus() {
	focused.value = true
	if (term.value) panelOpen.value = true
}

function onBlur() {
	focused.value = false
	panelOpen.value = false
}

function clear() {
	term.value = ''
	panelOpen.value = false
}

function onKeydown(event: KeyboardEvent) {
	if (event.key === 'Escape') {
		event.preventDefault()
		clear()
		return
	}
	if (!panelOpen.value || !matched.value.length) return
	if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
		event.preventDefault()
		const delta = event.key === 'ArrowDown' ? 1 : -1
		activeIndex.value =
			(activeIndex.value + delta + matched.value.length) % matched.value.length
	} else if (event.key === 'Enter') {
		event.preventDefault()
		select(activeIndex.value)
	}
}

function select(index: number) {
	const column = matched.value[index]
	if (!column) return
	// A jump is a move, not a filter: the term goes, so every row is back
	// and the column has a grid to land in.
	term.value = ''
	panelOpen.value = false
	emit('jump', column.name)
}

function focus() {
	nextTick(() => $input.value?.$el?.querySelector('input')?.focus())
}

defineExpose({ focus, clear })
</script>

<template>
	<div class="relative">
		<FormControl
			ref="$input"
			v-model="term"
			type="text"
			variant="outline"
			class="w-[120px]"
			:placeholder="__('Find')"
			autocomplete="off"
			@focus="onFocus"
			@blur="onBlur"
			@keydown="onKeydown"
		>
			<template #prefix>
				<Search class="size-3.5 text-ink-gray-6" stroke-width="1.5" />
			</template>
		</FormControl>

		<!-- A hand-built box wearing PopoverPanel's look and Combobox's rows:
		     frappe-ui's Popover takes focus on open, which a panel driven by
		     typing cannot afford. Same layer as a popover, so the grid's sticky
		     header cannot paint over it. See
		     docs/projects/table-experience/issues/07-frappe-ui-gaps.md -->
		<div
			v-if="panelOpen"
			class="absolute start-0 top-full z-[100] mt-1 w-64 overflow-hidden rounded-6 bg-surface-elevation-2 shadow-2xl ring-1 ring-black ring-opacity-5"
		>
			<div v-if="matched.length" class="flex flex-col p-1">
				<div class="flex h-7 items-center px-2 text-sm-medium text-ink-gray-4">
					{{ __('Jump to column') }}
				</div>
				<div
					v-for="(column, index) in matched"
					:key="column.name"
					class="flex min-h-7 cursor-pointer select-none items-center gap-2 rounded-4 px-2 text-base text-ink-gray-9 transition-colors duration-100 ease-out"
					:class="index === activeIndex ? 'bg-surface-alpha-gray-2' : ''"
					@mousemove="activeIndex = index"
					@mousedown.prevent="select(index)"
				>
					<component
						:is="columnIcon(column.type)"
						class="size-4 shrink-0 text-ink-gray-5"
						stroke-width="1.5"
					/>
					<span :title="column.name" class="flex-1 truncate text-start">
						{{ column.name }}
					</span>
					<CornerDownLeft
						v-if="index === activeIndex"
						class="size-3.5 shrink-0 text-ink-gray-4"
						stroke-width="1.5"
					/>
				</div>
			</div>
			<div
				class="px-3 py-1.5 text-sm text-ink-gray-5"
				:class="matched.length ? 'border-t border-outline-gray-1' : ''"
			>
				<template v-if="props.matchCount === 1">{{ __('1 row matches') }}</template>
				<template v-else-if="props.matchCount">
					{{ __('{0} rows match', String(props.matchCount)) }}
				</template>
				<template v-else>{{ __('No rows match') }}</template>
			</div>
		</div>
	</div>
</template>
