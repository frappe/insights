<script setup lang="ts">
// PROTOTYPE — throwaway. One complete picker per type, and no operator control.
//
// Live apply, no Apply button: a pick or a typed value applies where it stands
// (typing is debounced 500ms). An emptied value removes the condition. The
// operator is a consequence of the picker — which values are checked, which of
// the two number inputs is filled, which calendar gesture was made.

import { useDebounceFn, useEventListener, watchDebounced } from '@vueuse/core'
import { Button, Checkbox, Dropdown, FormControl, TabButtons, TextInput } from 'frappe-ui'
import { ChevronLeft, LoaderCircle, MoreHorizontal, Search } from 'lucide-vue-next'
import { computed, nextTick, ref, watch } from 'vue'
import type { FilterOperator, FilterValue, QueryResultColumn, Timespan } from '../types/query.types'
import ProtoDateRange from './ProtoDateRange.vue'
import { columnIcon, isDaySpan, kindOf, resolveSpan } from './proto_filter'

const props = withDefaults(
	defineProps<{
		column: QueryResultColumn
		filter?: { operator: FilterOperator; value: FilterValue } | null
		valuesProvider: (search: string) => Promise<string[]>
	}>(),
	{ filter: null },
)
const emit = defineEmits<{
	apply: [operator: FilterOperator, value: FilterValue]
	clear: []
	back: []
	done: []
}>()

const kind = computed(() => kindOf(props.column.type))

// --- text ------------------------------------------------------------------

// The list is the picker. "contains" is the one alternative body the rare
// operators can reach, and the two set checks never open a body at all.
const textMode = ref<'list' | 'contains'>(
	props.filter?.operator === 'contains' ? 'contains' : 'list',
)
const exclude = ref(props.filter?.operator === 'not_in')
const selected = ref<string[]>(
	props.filter?.operator === 'in' || props.filter?.operator === 'not_in'
		? [...((props.filter.value as string[]) || [])]
		: [],
)
const containsText = ref(
	props.filter?.operator === 'contains' ? String(props.filter.value ?? '') : '',
)

const includeOptions = [
	{ label: 'Include', value: 'include' },
	{ label: 'Exclude', value: 'exclude' },
]
const includeMode = computed({
	get: () => (exclude.value ? 'exclude' : 'include'),
	set: (mode: any) => {
		exclude.value = mode === 'exclude'
		if (selected.value.length) emit('apply', listOperator.value, [...selected.value])
	},
})
const listOperator = computed<FilterOperator>(() => (exclude.value ? 'not_in' : 'in'))

const moreOptions = computed(() => [
	{
		label: textMode.value === 'contains' ? 'Choose values…' : 'Contains…',
		onClick: () => (textMode.value = textMode.value === 'contains' ? 'list' : 'contains'),
	},
	{ label: 'Is set', onClick: () => commit('is_set', null as any) },
	{ label: 'Is not set', onClick: () => commit('is_not_set', null as any) },
])

const search = ref('')
const distinctValues = ref<string[]>([])
const fetching = ref(false)
const activeIndex = ref(0)
const searchInput = ref<any>(null)
const listEl = ref<HTMLElement | null>(null)

watchDebounced(
	[search, () => props.column.name],
	() => {
		if (kind.value !== 'text' || textMode.value !== 'list') return
		fetching.value = true
		props
			.valuesProvider(search.value)
			.then((values) => (distinctValues.value = values.map(String)))
			.catch(() => (distinctValues.value = []))
			.finally(() => (fetching.value = false))
	},
	{ debounce: 300, immediate: true },
)

function isChecked(option: string): boolean {
	return selected.value.includes(option)
}

function toggle(option: string) {
	const index = selected.value.indexOf(option)
	index === -1 ? selected.value.push(option) : selected.value.splice(index, 1)
	if (!selected.value.length) {
		emit('clear')
		return
	}
	emit('apply', listOperator.value, [...selected.value])
}

const debouncedContains = useDebounceFn(() => {
	if (containsText.value) emit('apply', 'contains', containsText.value)
}, 500)

function onContainsInput() {
	if (!containsText.value) {
		emit('clear')
		return
	}
	debouncedContains()
}

// --- number ----------------------------------------------------------------

const numberFrom = ref('')
const numberTo = ref('')
if (kind.value === 'number' && props.filter) {
	const { operator, value } = props.filter
	if (operator === 'between') {
		const [a, b] = (value as any[]) || []
		numberFrom.value = a == null ? '' : String(a)
		numberTo.value = b == null ? '' : String(b)
	} else if (operator === '<=') {
		numberTo.value = String(value ?? '')
	} else {
		numberFrom.value = String(value ?? '')
	}
}

// Inference, borrowed from the builder's ColumnFilterTypeNumber: which of the
// two inputs is filled is the operator.
const debouncedNumber = useDebounceFn(() => {
	const from = numberFrom.value.trim()
	const to = numberTo.value.trim()
	if (!from && !to) {
		emit('clear')
		return
	}
	if (from && !to) emit('apply', '>=', Number(from))
	else if (!from && to) emit('apply', '<=', Number(to))
	else emit('apply', 'between', [Number(from), Number(to)])
}, 500)

// --- date ------------------------------------------------------------------

const dateSpan = computed(() => {
	if (props.filter?.operator !== 'within') return ''
	const span = props.filter.value as Timespan
	return isDaySpan(span) ? '' : span?.span || ''
})

const dateRange = computed<[string, string]>(() => {
	if (props.filter?.operator === 'between') {
		const [from, to] = (props.filter.value as string[]) || []
		return [from || '', to || '']
	}
	if (props.filter?.operator === 'within') {
		const span = props.filter.value as Timespan
		if (isDaySpan(span)) return [span.anchor!, '']
		if (span?.span) return resolveSpan(span.span, span.anchor)
	}
	return ['', '']
})

// --- shared ----------------------------------------------------------------

function commit(operator: FilterOperator, value: FilterValue) {
	emit('apply', operator, value)
	emit('done')
}

function moveActive(delta: number) {
	const total = distinctValues.value.length
	if (total) activeIndex.value = (activeIndex.value + delta + total) % total
}

function onKeydown(event: KeyboardEvent) {
	if (event.isComposing) return
	if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
		event.preventDefault()
		event.stopPropagation()
		moveActive(event.key === 'ArrowDown' ? 1 : -1)
	} else if (event.key === 'Enter') {
		event.preventDefault()
		event.stopPropagation()
		if (event.repeat) return
		const option = distinctValues.value[activeIndex.value]
		if (option) toggle(option)
	} else if (event.key === 'Backspace' && !search.value) {
		event.stopPropagation()
		emit('back')
	}
}

function onTextKeydown(event: KeyboardEvent) {
	if (event.key === 'Backspace' && !containsText.value) {
		event.stopPropagation()
		emit('back')
	}
}

// Backspace steps back, unless a field is focused and has its own use for it.
useEventListener(document, 'keydown', (event: KeyboardEvent) => {
	if (event.key !== 'Backspace') return
	const el = document.activeElement
	if (el instanceof HTMLInputElement || el instanceof HTMLTextAreaElement) return
	event.preventDefault()
	emit('back')
})

watch(search, () => (activeIndex.value = 0))

watch(activeIndex, (index) => {
	nextTick(() => {
		listEl.value?.querySelector(`[data-index="${index}"]`)?.scrollIntoView({ block: 'nearest' })
	})
})

// preventScroll: the panel mounts mid-swipe, still translated. A default focus
// would scroll it into view and visually cancel the slide
watch(textMode, () => nextTick(() => searchInput.value?.focus({ preventScroll: true })), {
	immediate: true,
})
</script>

<template>
	<div class="flex flex-col">
		<div class="flex h-9 items-center gap-1 border-b border-outline-gray-1 pe-1 ps-1">
			<Button variant="ghost" label="Back" @click="emit('back')">
				<template #icon><ChevronLeft class="size-4" stroke-width="1.5" /></template>
			</Button>
			<component
				:is="columnIcon(column)"
				class="size-4 shrink-0 text-ink-gray-5"
				stroke-width="1.5"
			/>
			<span
				:title="column.name"
				class="min-w-0 flex-1 truncate text-base font-medium text-ink-gray-8"
			>
				{{ column.name }}
			</span>

			<template v-if="kind === 'text'">
				<TabButtons
					v-if="textMode === 'list'"
					v-model="includeMode"
					size="sm"
					:options="includeOptions"
				/>
				<Dropdown :options="moreOptions" side="bottom" align="end">
					<Button variant="ghost" label="More operators">
						<template #icon
							><MoreHorizontal class="size-4" stroke-width="1.5"
						/></template>
					</Button>
				</Dropdown>
			</template>
		</div>

		<!-- Dimension: the distinct values, checked -->
		<template v-if="kind === 'text' && textMode === 'list'">
			<div class="px-2 pt-2">
				<TextInput
					ref="searchInput"
					v-model="search"
					type="text"
					variant="outline"
					placeholder="Search values..."
					autocomplete="off"
					@keydown="onKeydown"
				>
					<template #prefix>
						<Search class="size-4 text-ink-gray-5" stroke-width="1.5" />
					</template>
					<template #suffix>
						<LoaderCircle
							v-if="fetching"
							class="size-4 animate-spin text-ink-gray-5"
							stroke-width="1.5"
						/>
					</template>
				</TextInput>
			</div>
			<div
				ref="listEl"
				role="listbox"
				:aria-label="column.name"
				class="mt-1 max-h-52 overflow-y-auto p-1.5 py-1"
			>
				<button
					v-for="(option, index) in distinctValues"
					:key="option"
					:data-index="index"
					role="option"
					:aria-selected="isChecked(option)"
					:class="[
						'flex h-8 w-full items-center gap-2 rounded px-1.5 text-base text-ink-gray-8',
						index === activeIndex ? 'bg-surface-gray-2' : '',
					]"
					@mousemove="activeIndex = index"
					@click="toggle(option)"
				>
					<Checkbox
						:modelValue="isChecked(option)"
						tabindex="-1"
						class="pointer-events-none shrink-0"
					/>
					<span :title="option" class="flex-1 truncate text-start">{{ option }}</span>
				</button>
				<div
					v-if="fetching && !distinctValues.length"
					class="flex h-8 items-center gap-2 px-2 text-base text-ink-gray-5"
				>
					<LoaderCircle class="size-4 animate-spin" stroke-width="1.5" />
					Searching...
				</div>
				<div
					v-else-if="!distinctValues.length"
					class="flex h-8 items-center px-2 text-base text-ink-gray-5"
				>
					No results
				</div>
			</div>
		</template>

		<!-- Dimension, the rare one: a substring -->
		<div v-else-if="kind === 'text'" class="p-2">
			<TextInput
				ref="searchInput"
				v-model="containsText"
				type="text"
				variant="outline"
				placeholder="Contains..."
				autocomplete="off"
				@update:modelValue="onContainsInput"
				@keydown="onTextKeydown"
			/>
		</div>

		<!-- Measure: a range, open at either end -->
		<div v-else-if="kind === 'number'" class="flex items-center gap-2 p-2">
			<FormControl
				type="number"
				placeholder="From"
				class="min-w-0 flex-1"
				v-model="numberFrom"
				@update:modelValue="debouncedNumber"
			/>
			<FormControl
				type="number"
				placeholder="To"
				class="min-w-0 flex-1"
				v-model="numberTo"
				@update:modelValue="debouncedNumber"
			/>
		</div>

		<!-- Date: presets and the calendar, side by side -->
		<ProtoDateRange
			v-else
			:from="dateRange[0]"
			:to="dateRange[1]"
			:span="dateSpan"
			@pick="(operator, value) => emit('apply', operator, value)"
			@done="emit('done')"
		/>
	</div>
</template>
