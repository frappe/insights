<script setup lang="ts">
// PROTOTYPE — throwaway. Helpdesk's FilterFieldList, over result columns.
import { TextInput } from 'frappe-ui'
import { ChevronRight, Search } from 'lucide-vue-next'
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import type { QueryResultColumn } from '../types/query.types'
import { columnIcon } from './proto_filter'

const props = withDefaults(
	defineProps<{
		columns: QueryResultColumn[]
		placeholder?: string
		showShortcutHint?: boolean
	}>(),
	{ placeholder: 'Search columns...', showShortcutHint: false },
)
const emit = defineEmits<{ select: [column: QueryResultColumn]; back: [] }>()

const query = ref('')
const activeIndex = ref(0)
const searchInput = ref<any>(null)
const listEl = ref<HTMLElement | null>(null)

const filteredColumns = computed(() => {
	if (!query.value) return props.columns
	return props.columns.filter((c) => c.name.toLowerCase().includes(query.value.toLowerCase()))
})

function onKeydown(event: KeyboardEvent) {
	if (event.isComposing) return
	if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
		event.preventDefault()
		event.stopPropagation()
		const delta = event.key === 'ArrowDown' ? 1 : -1
		const total = filteredColumns.value.length
		if (total) activeIndex.value = (activeIndex.value + delta + total) % total
	} else if (event.key === 'Enter') {
		event.preventDefault()
		event.stopPropagation()
		if (event.repeat) return
		const column = filteredColumns.value[activeIndex.value]
		if (column) emit('select', column)
	} else if (event.key === 'Backspace' && !query.value) {
		event.stopPropagation()
		emit('back')
	}
}

watch(query, () => (activeIndex.value = 0))

watch(activeIndex, (index) => {
	nextTick(() => {
		listEl.value?.querySelector(`[data-index="${index}"]`)?.scrollIntoView({ block: 'nearest' })
	})
})

onMounted(() => {
	// preventScroll: the panel mounts mid-swipe, still translated. A default
	// focus would scroll it into view and visually cancel the slide
	nextTick(() => searchInput.value?.focus({ preventScroll: true }))
})
</script>

<template>
	<div class="flex flex-col">
		<div class="px-2 pt-2">
			<TextInput
				ref="searchInput"
				v-model="query"
				type="text"
				variant="outline"
				:placeholder="placeholder"
				autocomplete="off"
				@keydown="onKeydown"
			>
				<template #prefix>
					<Search class="size-4 text-ink-gray-5" stroke-width="1.5" />
				</template>
				<template #suffix>
					<kbd
						v-if="showShortcutHint && !query"
						class="flex h-5 min-w-5 items-center justify-center rounded-[5px] border border-outline-gray-2 bg-surface-base px-1 pt-px text-xs text-ink-gray-5"
					>
						F
					</kbd>
				</template>
			</TextInput>
		</div>
		<div
			ref="listEl"
			role="listbox"
			aria-label="Columns"
			class="mt-1 max-h-64 overflow-y-auto p-1"
		>
			<button
				v-for="(column, index) in filteredColumns"
				:key="column.name"
				:data-index="index"
				role="option"
				:aria-selected="index === activeIndex"
				:class="[
					'flex h-8 w-full items-center gap-2 rounded px-2 text-base text-ink-gray-8',
					index === activeIndex ? 'bg-surface-gray-2' : '',
				]"
				@mousemove="activeIndex = index"
				@click="emit('select', column)"
			>
				<component
					:is="columnIcon(column)"
					class="size-4 text-ink-gray-5"
					stroke-width="1.5"
				/>
				<span :title="column.name" class="flex-1 truncate text-start">{{
					column.name
				}}</span>
				<ChevronRight class="size-4 text-ink-gray-4" stroke-width="1.5" />
			</button>
			<div
				v-if="!filteredColumns.length"
				class="flex h-8 items-center px-2 text-base text-ink-gray-5"
			>
				No columns found
			</div>
		</div>
	</div>
</template>
